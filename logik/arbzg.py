"""Prüfungen nach dem Arbeitszeitgesetz und Feiertage in Baden-Württemberg."""
from datetime import date, timedelta

from logik.modelle import Zeiteintrag, Abwesenheit, pausen_von
from logik.speicher import finde_abwesenheit
from logik.zeit import (berechne_arbeitsminuten, minuten_als_text, liegt_ausserhalb_betriebszeit,
                        zeit_in_minuten, ende_in_minuten, ist_nachtschicht, laengste_zeit_ohne_pause)


# Feiertage 

def ostersonntag(jahr: int) -> date:
    """Berechnet den Ostersonntag eines Jahres mit der Gaussschen Osterformel."""
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
    return berechne_arbeitsminuten(eintrag.beginn, eintrag.ende, eintrag.pause_minuten)


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


def werktage_im_zeitraum(von: date, bis: date, abwesenheiten: list[Abwesenheit]) -> int:
    """Werktage im Sinne des ArbZG (Montag bis Samstag), ohne Feiertage und ohne Abwesenheiten."""
    anzahl = 0
    datum = von
    while datum <= bis:
        if datum.weekday() != 6 and feiertag_name(datum) == "" and finde_abwesenheit(abwesenheiten, datum) is None:
            anzahl = anzahl + 1
        datum = datum + timedelta(days=1)
    return anzahl


def pruefe_sechs_monate_durchschnitt(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                                     erfassung_ab, heute: date) -> list[dict]:
    """§ 3 ArbZG: im Durchschnitt von 6 Monaten höchstens 8 h je Werktag (Montag bis Samstag).
    Solange noch keine 6 Monate erfasst sind, ist ein Ausgleich möglich: dann nur eine Warnung."""
    if erfassung_ab is None:
        return []
    sechs_monate_zurueck = heute - timedelta(days=182)
    start = max(sechs_monate_zurueck, erfassung_ab)

    # Gearbeitete Minuten durch die Werktage
    ende = heute - timedelta(days=1)
    summe = 0
    for eintrag in eintraege:
        if eintrag.datum == heute:
            ende = heute
        if start <= eintrag.datum <= heute:
            summe = summe + arbeitsminuten(eintrag)
    werktage = werktage_im_zeitraum(start, ende, abwesenheiten)
    if werktage == 0 or summe // werktage <= 480:
        return []

    text = "Durchschnitt " + minuten_als_text(summe // werktage) + " je Werktag, erlaubt sind 8:00 h."
    if start > sechs_monate_zurueck:
        return [melde("Warnung", "§ 3 ArbZG", text + " Bis 6 Monate erfasst sind, muss er sinken.")]
    return [melde("Verletzung", "§ 3 ArbZG", text)]


# § 4 Ruhepausen 

def pruefe_pause(eintrag: Zeiteintrag) -> list[dict]:
    """§ 4 ArbZG: über 6 h Arbeit 30 min Pause, über 9 h 45 min. Warnung schon ab 5,5 h bzw. 8,5 h."""
    arbeit = arbeitsminuten(eintrag)
    pause = eintrag.pause_minuten

    # Pflichtpause je nach Arbeitsdauer bestimmen
    pflicht_pause = 0
    if arbeit > 9 * 60:
        pflicht_pause = 45
    elif arbeit > 6 * 60:
        pflicht_pause = 30
    if pause < pflicht_pause:
        text = "Pause zu kurz: " + str(pause) + " min statt " + str(pflicht_pause) + " min."
        return [melde("Verletzung", "§ 4 ArbZG", text)]

    # Kurz vor der Grenze nur warnen
    bald_pflicht = 0
    if arbeit > 510:
        bald_pflicht = 45
    elif arbeit > 330:
        bald_pflicht = 30
    if pause < bald_pflicht:
        text = "Bald sind " + str(bald_pflicht) + " min Pause nötig, bisher nur " + str(pause) + " min."
        return [melde("Warnung", "§ 4 ArbZG", text)]
    return []


def pruefe_pause_am_stueck(eintrag: Zeiteintrag) -> list[dict]:
    """§ 4 Satz 3 ArbZG: nicht länger als 6 Stunden hintereinander ohne Pause. """
    # Ohne Pause meldet das schon pruefe_pause, sonst käme § 4 doppelt
    if eintrag.pause_minuten == 0:
        return []
    am_stueck = laengste_zeit_ohne_pause(eintrag.beginn, eintrag.ende, pausen_von(eintrag))
    if am_stueck > 6 * 60:
        return [melde("Verletzung", "§ 4 ArbZG",
                      minuten_als_text(am_stueck) + " am Stück ohne Pause, erlaubt sind 6 Stunden.")]
    return []


# § 5 Ruhezeit 

def pruefe_ruhezeit(eintrag: Zeiteintrag, eintrag_vortag, vortag_fehlt: bool = False) -> list[dict]:
    """§ 5 ArbZG: zwischen Ende der Arbeit am Vortag und Beginn heute müssen 11 h Ruhe liegen."""
    if eintrag_vortag is None:
        if vortag_fehlt:
            return [melde("Warnung", "§ 5 ArbZG", "Ruhezeit nicht prüfbar: Für den Vortag fehlt ein Eintrag.")]
        return []

    # Ende des Vortags in Minuten, auch wenn die Schicht erst nach Mitternacht endete
    tage = (eintrag.datum - eintrag_vortag.datum).days
    ende_vortag = ende_in_minuten(eintrag_vortag.beginn, eintrag_vortag.ende)
    ruhe = tage * 24 * 60 + zeit_in_minuten(eintrag.beginn) - ende_vortag
    if ruhe < 0:
        return [melde("Verletzung", "§ 5 ArbZG", "Die Arbeit überschneidet sich mit der Schicht vom Vortag.")]
    if ruhe < 11 * 60:
        return [melde("Verletzung", "§ 5 ArbZG",
                      "Ruhezeit zum Vortag nur " + minuten_als_text(ruhe) + " statt 11 Stunden.")]
    return []


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
