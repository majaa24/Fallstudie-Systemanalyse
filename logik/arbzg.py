"""Prüfungen nach dem Arbeitszeitgesetz und Feiertage in Baden-Württemberg."""
from datetime import date, datetime, time, timedelta

from logik.modelle import Zeiteintrag, Abwesenheit, pausen_von
from logik.speicher import finde_abwesenheit, finde_eintrag
from logik.zeit import (PAUSE_ABSCHNITT_MIN, zaehlende_pausen, pausen_summe, berechne_arbeitsminuten, minuten_als_text,
                        liegt_ausserhalb_betriebszeit, zeit_in_minuten, ende_in_minuten, ist_nachtschicht, laengste_zeit_ohne_pause,
                        berechne_nachtminuten)


# Feiertage 

def ostersonntag(jahr: int) -> date:
    """Berechnet den Ostersonntag eines Jahres mit der Gaußschen Osterformel."""
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = (h + l - 7 * m + 114) % 31 + 1
    return date(jahr, monat, tag)


def feiertage_bw(jahr: int) -> dict:
    """Gesetzliche Feiertage in Baden-Württemberg."""
    feiertage = {
        date(jahr, 1, 1): "Neujahr",
        date(jahr, 1, 6): "Heilige Drei Könige",
        date(jahr, 5, 1): "Tag der Arbeit",
        date(jahr, 10, 3): "Tag der Deutschen Einheit",
        date(jahr, 11, 1): "Allerheiligen",
        date(jahr, 12, 25): "1. Weihnachtstag",
        date(jahr, 12, 26): "2. Weihnachtstag",
    }

    # Bewegliche Feiertage hängen an Ostern
    ostern = ostersonntag(jahr)
    feiertage[ostern - timedelta(days=2)] = "Karfreitag"
    feiertage[ostern + timedelta(days=1)] = "Ostermontag"
    feiertage[ostern + timedelta(days=39)] = "Christi Himmelfahrt"
    feiertage[ostern + timedelta(days=50)] = "Pfingstmontag"
    feiertage[ostern + timedelta(days=60)] = "Fronleichnam"
    return feiertage


def feiertag_name(datum: date) -> str:
    """Name des Feiertags oder "" wenn kein Feiertag."""
    feiertage = feiertage_bw(datum.year)
    if datum in feiertage:
        return feiertage[datum]
    return ""


# Meldungen 

def melde(art: str, paragraph: str, text: str) -> dict:
    """Baut eine Meldung."""
    return {"art": art, "paragraph": paragraph, "text": text}


def arbeitsminuten(eintrag: Zeiteintrag) -> int:
    """Arbeitszeit des Eintrags in Minuten (ohne Pause, auch außerhalb 6 bis 22 Uhr)."""
    return berechne_arbeitsminuten(eintrag.beginn, eintrag.ende, pausen_von(eintrag))


# § 3 Arbeitszeit 

def pruefe_hoechstarbeitszeit(eintrag: Zeiteintrag) -> list[dict]:
    """§ 3 ArbZG: mehr als 8 h ist eine Warnung, mehr als 10 h eine Verletzung."""
    arbeit = arbeitsminuten(eintrag)
    text_arbeit = minuten_als_text(arbeit)
    if arbeit > 600:
        return [melde("Verletzung", "§ 3 ArbZG",
                      "Arbeitszeit " + text_arbeit + " überschreitet die Höchstgrenze von 10 Stunden.")]
    if arbeit > 480:
        return [melde("Warnung", "§ 3 ArbZG",
                      "Arbeitszeit " + text_arbeit + " liegt über 8 Stunden. Ausgleich innerhalb von 6 Monaten nötig.")]
    return []


def ist_werktag(datum: date, abwesenheiten: list[Abwesenheit]) -> bool:
    """Werktag im Sinne des ArbZG (Montag bis Samstag), kein Feiertag und keine Abwesenheit."""
    return datum.weekday() != 6 and feiertag_name(datum) == "" and finde_abwesenheit(abwesenheiten, datum) is None


def werktage_im_zeitraum(von: date, bis: date, abwesenheiten: list[Abwesenheit]) -> int:
    """Werktage im Sinne des ArbZG (Montag bis Samstag), ohne Feiertage und ohne Abwesenheiten."""
    anzahl = 0
    datum = von
    while datum <= bis:
        if ist_werktag(datum, abwesenheiten):
            anzahl = anzahl + 1
        datum = datum + timedelta(days=1)
    return anzahl


def minuten_und_tage(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit], von: date, bis: date):
    """Gearbeitete Minuten und Zahl der Tage von "von" bis "bis" für einen Durchschnitt.
    Gezählt werden die Werktage und dazu jeder andere Tag mit Arbeit (Sonntag, Feiertag, Abwesenheit).
    Sonst stünde dessen Arbeit im Zähler, der Tag aber nicht im Nenner."""
    summe = 0
    tage = werktage_im_zeitraum(von, bis, abwesenheiten)
    for eintrag in eintraege:
        if von <= eintrag.datum <= bis:
            summe = summe + arbeitsminuten(eintrag)
            if not ist_werktag(eintrag.datum, abwesenheiten):
                tage = tage + 1
    return summe, tage


def pruefe_sechs_monate_durchschnitt(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                                     erfassung_ab, heute: date) -> list[dict]:
    """§ 3 ArbZG: im Durchschnitt von 6 Monaten höchstens 8 h je Werktag (Montag bis Samstag).
    Solange noch keine 6 Monate erfasst sind, ist ein Ausgleich möglich: dann nur eine Warnung."""
    if erfassung_ab is None:
        return []
    sechs_monate_zurueck = heute - timedelta(days=182)
    start = max(sechs_monate_zurueck, erfassung_ab)

    # Gearbeitete Minuten durch die Werktage. Heute zählt erst mit, wenn es schon einen Eintrag gibt
    ende = heute - timedelta(days=1)
    for eintrag in eintraege:
        if eintrag.datum == heute:
            ende = heute
    summe, werktage = minuten_und_tage(eintraege, abwesenheiten, start, ende)
    if werktage == 0 or summe // werktage <= 480:
        return []

    text = "Durchschnitt " + minuten_als_text(summe // werktage) + " je Werktag, erlaubt sind 8:00 h."
    if start > sechs_monate_zurueck:
        return [melde("Warnung", "§ 3 ArbZG", text + " Bis 6 Monate erfasst sind, muss er sinken.")]
    return [melde("Verletzung", "§ 3 ArbZG", text)]


# § 4 Ruhepausen 

def hinweis_kurze_pause(pausen: list) -> str:
    """Zusatz zur Meldung, wenn eine Pause nur wegen der 15 Minuten nicht zählt."""
    for pause in pausen:
        if 0 < pause.minuten < PAUSE_ABSCHNITT_MIN:
            return " Pausen unter " + str(PAUSE_ABSCHNITT_MIN) + " min zählen nicht."
    return ""


def pruefe_pause(eintrag: Zeiteintrag) -> list[dict]:
    """§ 4 ArbZG: über 6 h Arbeit 30 min Pause, über 9 h 45 min. Warnung schon ab 5,5 h bzw. 8,5 h.
    Jede Pause unter 15 min zählt nicht als Ruhepause."""
    arbeit = arbeitsminuten(eintrag)
    pausen = pausen_von(eintrag)
    zaehlt = pausen_summe(zaehlende_pausen(pausen))

    # Pflichtpause je nach Arbeitsdauer bestimmen
    pflicht_pause = 0
    if arbeit > 9 * 60:
        pflicht_pause = 45
    elif arbeit > 6 * 60:
        pflicht_pause = 30
    if zaehlt < pflicht_pause:
        text = "Pause zu kurz: " + str(zaehlt) + " min statt " + str(pflicht_pause) + " min." + hinweis_kurze_pause(pausen)
        return [melde("Verletzung", "§ 4 ArbZG", text)]

    # Kurz vor der Grenze nur warnen
    bald_pflicht = 0
    if arbeit > 510:
        bald_pflicht = 45
    elif arbeit > 330:
        bald_pflicht = 30
    if zaehlt < bald_pflicht:
        text = ("Bald sind " + str(bald_pflicht) + " min Pause nötig, bisher nur " + str(zaehlt) + " min."
                + hinweis_kurze_pause(pausen))
        return [melde("Warnung", "§ 4 ArbZG", text)]
    return []


def pruefe_pause_am_stueck(eintrag: Zeiteintrag) -> list[dict]:
    """§ 4 Satz 3 ArbZG: nicht länger als 6 Stunden hintereinander ohne Pause. """
    # Ohne zählende Pause meldet das schon pruefe_pause, sonst käme § 4 doppelt
    if len(zaehlende_pausen(pausen_von(eintrag))) == 0:
        return []
    am_stueck = laengste_zeit_ohne_pause(eintrag.beginn, eintrag.ende, pausen_von(eintrag))
    if am_stueck > 6 * 60:
        return [melde("Verletzung", "§ 4 ArbZG",
                      minuten_als_text(am_stueck) + " am Stück ohne Pause, erlaubt sind 6 Stunden.")]
    return []


# § 5 Ruhezeit 

def ruhezeit_minuten(datum: date, beginn: time, eintrag_vortag: Zeiteintrag) -> int:
    """Minuten vom Ende der Arbeit am Vortag bis zum Beginn, auch wenn der Vortag erst nach Mitternacht endete."""
    tage = (datum - eintrag_vortag.datum).days
    ende_vortag = ende_in_minuten(eintrag_vortag.beginn, eintrag_vortag.ende)
    return tage * 24 * 60 + zeit_in_minuten(beginn) - ende_vortag


def pruefe_ruhezeit(eintrag: Zeiteintrag, eintrag_vortag, vortag_fehlt: bool = False) -> list[dict]:
    """§ 5 ArbZG: zwischen Ende der Arbeit am Vortag und Beginn heute müssen 11 h Ruhe liegen."""
    if eintrag_vortag is None:
        if vortag_fehlt:
            return [melde("Warnung", "§ 5 ArbZG", "Ruhezeit nicht prüfbar: Für den Vortag fehlt ein Eintrag.")]
        return []

    ruhe = ruhezeit_minuten(eintrag.datum, eintrag.beginn, eintrag_vortag)
    if ruhe < 0:
        return [melde("Verletzung", "§ 5 ArbZG", "Die Arbeit überschneidet sich mit der Schicht vom Vortag.")]
    if ruhe < 11 * 60:
        return [melde("Verletzung", "§ 5 ArbZG",
                      "Ruhezeit zum Vortag nur " + minuten_als_text(ruhe) + " statt 11 Stunden.")]
    return []


# § 6 Nachtarbeit

def ist_nachtarbeit(eintrag: Zeiteintrag) -> bool:
    """§ 2 Abs. 4 ArbZG: Nachtarbeit ist Arbeit, die mehr als 2 Stunden der Nachtzeit (23 bis 6 Uhr) umfasst."""
    return berechne_nachtminuten(eintrag.beginn, eintrag.ende, pausen_von(eintrag)) > 120


def pruefe_nachtarbeit(eintrag: Zeiteintrag, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                       erfassung_ab) -> list[dict]:
    """§ 6 Abs. 2 ArbZG: Bei Nachtarbeit sind über 8 h nur erlaubt, wenn im Durchschnitt von 4 Wochen
    8 h je Werktag nicht überschritten werden (bei § 3 sind es 6 Monate). Geprüft werden die 4 Wochen
    bis zu diesem Tag. Ob jemand Nachtarbeitnehmer ist (Wechselschicht oder 48 Tage im Jahr), weiß das
    Programm nicht, es prüft deshalb jeden Tag mit Nachtarbeit."""
    if not ist_nachtarbeit(eintrag) or arbeitsminuten(eintrag) <= 480:
        return []
    vier_wochen_zurueck = eintrag.datum - timedelta(days=27)
    start = vier_wochen_zurueck
    if erfassung_ab is not None and erfassung_ab > start:
        start = erfassung_ab
    summe, tage = minuten_und_tage(eintraege, abwesenheiten, start, eintrag.datum)
    if tage == 0 or summe // tage <= 480:
        return [melde("Warnung", "§ 6 ArbZG", "Nachtarbeit über 8 Stunden. Ausgleich innerhalb von 4 Wochen nötig.")]

    text = "Nachtarbeit: Durchschnitt " + minuten_als_text(summe // tage) + " je Werktag in 4 Wochen, erlaubt sind 8:00 h."
    if start > vier_wochen_zurueck:
        return [melde("Warnung", "§ 6 ArbZG", text + " Bis 4 Wochen erfasst sind, muss er sinken.")]
    return [melde("Verletzung", "§ 6 ArbZG", text)]


# § 9 Sonn- und Feiertagsruhe 

def ruhetag_meldungen(datum: date, zusatz: str) -> list[dict]:
    """Verletzungen, wenn an diesem Datum ein Sonntag oder Feiertag ist."""
    meldungen = []
    if datum.weekday() == 6:
        meldungen.append(melde("Verletzung", "§ 9 ArbZG",
                               "Arbeit an einem Sonntag" + zusatz + " ist nicht zulässig."))
    name = feiertag_name(datum)
    if name != "":
        meldungen.append(melde("Verletzung", "§ 9 ArbZG",
                               "Arbeit an einem gesetzlichen Feiertag (" + name + ")" + zusatz + " ist nicht zulässig."))
    return meldungen


def pruefe_sonntag_feiertag(eintrag: Zeiteintrag) -> list[dict]:
    """§ 9 ArbZG: an Sonntagen und Feiertagen darf nicht gearbeitet werden, auch nicht nach Mitternacht."""
    meldungen = ruhetag_meldungen(eintrag.datum, "")

    # Bei einer Nachtschicht liegt der Teil nach Mitternacht am Folgetag
    if ist_nachtschicht(eintrag.beginn, eintrag.ende) and zeit_in_minuten(eintrag.ende) > 0:
        meldungen.extend(ruhetag_meldungen(eintrag.datum + timedelta(days=1), " (nach Mitternacht)"))
    return meldungen


# § 11 Ausgleich für Sonn- und Feiertagsbeschäftigung

def tage_mit_arbeit(eintrag: Zeiteintrag) -> list[date]:
    """Tage, an denen der Eintrag Arbeit enthält: der Starttag und bei einer Nachtschicht auch der Folgetag."""
    tage = [eintrag.datum]
    if ist_nachtschicht(eintrag.beginn, eintrag.ende) and zeit_in_minuten(eintrag.ende) > 0:
        tage.append(eintrag.datum + timedelta(days=1))
    return tage


def gearbeitete_tage(eintraege: list[Zeiteintrag]) -> set:
    """Alle Tage, an denen gearbeitet wurde, auch nur nach Mitternacht in einer Nachtschicht."""
    tage = set()
    for eintrag in eintraege:
        for tag in tage_mit_arbeit(eintrag):
            tage.add(tag)
    return tage


def ist_ruhetag(datum: date) -> bool:
    """Sonntag oder gesetzlicher Feiertag."""
    return datum.weekday() == 6 or feiertag_name(datum) != ""


def frist_ersatzruhetag(ruhetag: date) -> int:
    """§ 11 Abs. 3 ArbZG: 2 Wochen nach Arbeit am Sonntag, 8 Wochen nach Arbeit an einem Feiertag unter der Woche."""
    if ruhetag.weekday() == 6:
        return 14
    return 56


def ist_freier_werktag(datum: date, gearbeitet: set, erfassung_ab: date, heute: date) -> bool:
    """Vergangener Werktag (Montag bis Samstag, kein Feiertag) seit Beginn der Erfassung, an dem gar nicht
    gearbeitet wurde, auch nicht nach Mitternacht. Tage vor der Erfassung sind unbekannt, Tage ab heute noch offen."""
    if datum < erfassung_ab or datum >= heute or ist_ruhetag(datum):
        return False
    return datum not in gearbeitet


def ersatzruhetage_zuordnen(eintraege: list[Zeiteintrag], erfassung_ab: date, heute: date) -> dict:
    """§ 11 Abs. 3 ArbZG: Jeder gearbeitete Sonn- oder Feiertag braucht einen eigenen freien Werktag, ein freier
    Tag zählt also nur einmal. Der Zeitraum schließt den Ruhetag ein, der freie Tag darf davor oder danach liegen.
    Der Ruhetag mit der frühesten Frist bekommt zuerst den frühesten noch freien Tag.
    Gibt {Ruhetag: freier Tag} zurück, None, wenn es (noch) keinen gibt."""
    gearbeitet = gearbeitete_tage(eintraege)
    nach_frist = []
    for tag in gearbeitet:
        if ist_ruhetag(tag):
            nach_frist.append((tag + timedelta(days=frist_ersatzruhetag(tag) - 1), tag))
    nach_frist.sort()

    benutzt = set()
    zuordnung = {}
    for letzter, ruhetag in nach_frist:
        zuordnung[ruhetag] = None
        datum = ruhetag - timedelta(days=frist_ersatzruhetag(ruhetag) - 1)
        while datum <= letzter:
            if datum not in benutzt and ist_freier_werktag(datum, gearbeitet, erfassung_ab, heute):
                zuordnung[ruhetag] = datum
                benutzt.add(datum)
                break
            datum = datum + timedelta(days=1)
    return zuordnung


def pruefe_ersatzruhetag(eintrag: Zeiteintrag, eintraege: list[Zeiteintrag], erfassung_ab: date,
                         heute: date) -> list[dict]:
    """§ 11 ArbZG für einen Eintrag: Ersatzruhetag für jeden Sonn- oder Feiertag, an dem er Arbeit enthält
    (auch nach Mitternacht), und 15 freie Sonntage im Jahr."""
    meldungen = []
    zuordnung = None
    for ruhetag in tage_mit_arbeit(eintrag):
        if not ist_ruhetag(ruhetag):
            continue
        if zuordnung is None:
            zuordnung = ersatzruhetage_zuordnen(eintraege, erfassung_ab, heute)
        if zuordnung[ruhetag] is not None:
            continue
        frist = frist_ersatzruhetag(ruhetag)
        anlass = "Feiertag"
        if ruhetag.weekday() == 6:
            anlass = "Sonntag"
        letzter = ruhetag + timedelta(days=frist - 1)
        # Liegt das Ende der Frist noch vor uns, kann der freie Tag noch kommen
        if letzter >= heute:
            meldungen.append(melde("Warnung", "§ 11 ArbZG", "Für die Arbeit am " + anlass + " ist ein Ersatzruhetag nötig. Bis "
                                   + letzter.strftime("%d.%m.%Y") + " einen Werktag frei nehmen."))
        else:
            meldungen.append(melde("Verletzung", "§ 11 ArbZG", "Für die Arbeit am " + anlass + " gab es innerhalb von "
                                   + str(frist // 7) + " Wochen keinen Ersatzruhetag."))
    meldungen.extend(pruefe_freie_sonntage(eintrag, eintraege))
    return meldungen


def sonntage_im_jahr(jahr: int) -> int:
    """Wie viele Sonntage ein Jahr hat (52 oder 53)."""
    anzahl = 0
    datum = date(jahr, 1, 1)
    while datum.year == jahr:
        if datum.weekday() == 6:
            anzahl = anzahl + 1
        datum = datum + timedelta(days=1)
    return anzahl


def pruefe_freie_sonntage(eintrag: Zeiteintrag, eintraege: list[Zeiteintrag]) -> list[dict]:
    """§ 11 Abs. 1 ArbZG: Mindestens 15 Sonntage im Jahr müssen frei bleiben. Ein Sonntag zählt als gearbeitet,
    auch wenn nur der Teil einer Nachtschicht nach Mitternacht darauf fällt (wie bei § 9)."""
    sonntag = None
    for tag in tage_mit_arbeit(eintrag):
        if tag.weekday() == 6:
            sonntag = tag
    if sonntag is None:
        return []
    jahr = sonntag.year
    gearbeitet = 0
    for tag in gearbeitete_tage(eintraege):
        if tag.year == jahr and tag.weekday() == 6:
            gearbeitet = gearbeitet + 1
    frei = sonntage_im_jahr(jahr) - gearbeitet
    if frei < 15:
        return [melde("Verletzung", "§ 11 ArbZG", "Im Jahr " + str(jahr) + " bleiben nur " + str(frei)
                      + " Sonntage frei, mindestens 15 müssen es sein.")]
    return []


# Betriebliche Arbeitszeit 

def pruefe_betriebszeit(eintrag: Zeiteintrag) -> list[dict]:
    """Warnung, wenn Zeit vor 6:00 oder nach 22:00 Uhr liegt (zählt nicht für die Gleitzeit)."""
    if liegt_ausserhalb_betriebszeit(eintrag.beginn, eintrag.ende):
        return [melde("Warnung", "Betrieb",
                      "Zeit vor 6:00 oder nach 22:00 Uhr zählt nicht als betriebliche Arbeitszeit.")]
    return []


# Alles zusammen 

def pruefe_tag(eintrag: Zeiteintrag, eintrag_vortag, vortag_fehlt: bool = False) -> list[dict]:
    """Prüft einen Tag nach allen Regeln und gibt alle Meldungen als Liste zurück."""
    meldungen = []
    meldungen.extend(pruefe_hoechstarbeitszeit(eintrag))
    meldungen.extend(pruefe_pause(eintrag))
    meldungen.extend(pruefe_pause_am_stueck(eintrag))
    meldungen.extend(pruefe_sonntag_feiertag(eintrag))
    meldungen.extend(pruefe_ruhezeit(eintrag, eintrag_vortag, vortag_fehlt))
    meldungen.extend(pruefe_betriebszeit(eintrag))
    return meldungen


def mit_eintrag(eintraege: list[Zeiteintrag], eintrag: Zeiteintrag) -> list[Zeiteintrag]:
    """Alle Einträge, wobei "eintrag" den gespeicherten Eintrag vom selben Tag ersetzt (wichtig für die Vorschau)."""
    alle = []
    for anderer in eintraege:
        if anderer.datum != eintrag.datum:
            alle.append(anderer)
    alle.append(eintrag)
    return alle


def pruefe_mit_anderen_tagen(eintrag: Zeiteintrag, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                             erfassung_ab, heute: date) -> list[dict]:
    """Prüfungen, die mehr als den Vortag brauchen: § 6 (4 Wochen) und § 11 (Ersatzruhetag, freie Sonntage)."""
    alle = mit_eintrag(eintraege, eintrag)
    # Die Erfassung beginnt spätestens mit dem ersten Eintrag, auch wenn der erst in der Vorschau steht
    beginn = erfassung_ab
    for anderer in alle:
        if beginn is None or anderer.datum < beginn:
            beginn = anderer.datum
    meldungen = []
    meldungen.extend(pruefe_nachtarbeit(eintrag, alle, abwesenheiten, beginn))
    meldungen.extend(pruefe_ersatzruhetag(eintrag, alle, beginn, heute))
    return meldungen


def warnungen_beim_einstempeln(jetzt: datetime, eintrag_vortag) -> list[dict]:
    """Warnt schon beim Einstempeln, wenn die Ruhezeit nach § 5 noch nicht um ist oder heute ein Sonntag
    oder Feiertag ist (§ 9), ab 14 Uhr auch, wenn morgen einer ist. Sonst käme die Verletzung erst beim Ausstempeln."""
    warnungen = []
    if eintrag_vortag is not None:
        ruhe = ruhezeit_minuten(jetzt.date(), jetzt.time(), eintrag_vortag)
        if ruhe < 11 * 60:
            warnungen.append(melde("Warnung", "§ 5 ArbZG", "Seit dem Ende am Vortag sind erst "
                                   + minuten_als_text(max(ruhe, 0)) + " vergangen, nötig sind 11 Stunden Ruhezeit."))
    for meldung in ruhetag_meldungen(jetzt.date(), ""):
        warnungen.append(melde("Warnung", meldung["paragraph"], meldung["text"]))

    # Ab 14 Uhr kann eine Schicht mit bis zu 10 Stunden über Mitternacht gehen
    if jetzt.hour >= 14:
        for meldung in ruhetag_meldungen(jetzt.date() + timedelta(days=1), " (nach Mitternacht)"):
            warnungen.append(melde("Warnung", meldung["paragraph"], meldung["text"]))
    return warnungen


def status_aus_meldungen(meldungen: list[dict]) -> str:
    """Fasst Meldungen zusammen: "rot" (Verletzung), "orange" (Warnung) oder "grün"."""
    for meldung in meldungen:
        if meldung["art"] == "Verletzung":
            return "rot"
    if len(meldungen) > 0:
        return "orange"
    return "gruen"


def nur_verletzungen(meldungen: list[dict]) -> list[dict]:
    """Filtert aus allen Meldungen nur die Verletzungen heraus."""
    verletzungen = []
    for meldung in meldungen:
        if meldung["art"] == "Verletzung":
            verletzungen.append(meldung)
    return verletzungen
