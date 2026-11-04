"""Gleitzeit-Saldo, Ampel, Eingabeprüfungen und die Tagesliste (so wie die Oberfläche sie braucht)."""
import calendar
from datetime import date, timedelta

from logik.modelle import Zeiteintrag, Abwesenheit, Einstellungen, pausen_von
from logik import arbzg
from logik.speicher import finde_eintrag, finde_abwesenheit, datum_zu_text, zeit_zu_text, zeit_oder_leer
from logik.zeit import berechne_betriebsminuten, sollminuten_je_tag, ist_wochenende, wochentag_name

ARTEN_ABWESENHEIT = ["Urlaub", "Krankheit", "Sonderurlaub", "Sonstige Abwesenheit"]


# Soll und Ist 

def soll_fuer_tag(datum: date, abwesenheiten: list[Abwesenheit], einstellungen: Einstellungen) -> int:
    """Sollzeit eines Tages. Wochenende, Feiertag und Abwesenheit haben kein Soll."""
    if ist_wochenende(datum) or arbzg.feiertag_name(datum) != "":
        return 0
    if finde_abwesenheit(abwesenheiten, datum) is not None:
        return 0
    return sollminuten_je_tag(einstellungen.wochenstunden)


def ist_fuer_eintrag(eintrag: Zeiteintrag) -> int:
    """Betriebliche Arbeitsminuten eines Eintrags (nur 6 bis 22 Uhr)."""
    return berechne_betriebsminuten(eintrag.beginn, eintrag.ende, pausen_von(eintrag))


def saldo_fuer_eintrag(eintrag: Zeiteintrag, abwesenheiten: list[Abwesenheit], einstellungen: Einstellungen) -> int:
    """Gleitzeit eines erfassten Tages: Ist minus Soll. An Sonn-, Feier- und Abwesenheitstagen ist das Soll 0,
    die betriebliche Arbeitszeit zählt dann ganz als Plus."""
    return ist_fuer_eintrag(eintrag) - soll_fuer_tag(eintrag.datum, abwesenheiten, einstellungen)


# Vergessene Arbeitstage 

def erfassung_beginn(eintraege: list[Zeiteintrag], einstellungen: Einstellungen):
    """Ab wann fehlende Arbeitstage zählen: Einstellung oder erster Eintrag. None, wenn es nichts gibt."""
    if einstellungen.erfassung_ab is not None:
        return einstellungen.erfassung_ab
    erster = None
    for eintrag in eintraege:
        if erster is None or eintrag.datum < erster:
            erster = eintrag.datum
    return erster


def ist_fehltag(datum: date, heute: date, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                einstellungen: Einstellungen) -> bool:
    """Vergangener Arbeitstag ohne Eintrag und ohne Abwesenheit, ab Beginn der Zeiterfassung."""
    beginn = erfassung_beginn(eintraege, einstellungen)
    if beginn is None or datum < beginn or datum >= heute:
        return False
    if finde_eintrag(eintraege, datum) is not None:
        return False
    return soll_fuer_tag(datum, abwesenheiten, einstellungen) > 0


#  Saldo

def summe_fehltage(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit], von: date, bis: date,
                   einstellungen: Einstellungen, heute: date) -> int:
    """Minusstunden für vergessene Arbeitstage zwischen "von" und "bis"."""
    beginn = erfassung_beginn(eintraege, einstellungen)
    if beginn is None:
        return 0
    datum = max(von, beginn)
    letzter = min(bis, heute - timedelta(days=1))
    summe = 0
    while datum <= letzter:
        if finde_eintrag(eintraege, datum) is None:
            summe = summe - soll_fuer_tag(datum, abwesenheiten, einstellungen)
        datum = datum + timedelta(days=1)
    return summe


def saldo_zeitraum(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit], von: date, bis: date,
                   einstellungen: Einstellungen, heute: date) -> int:
    """Gleitzeit von "von" bis "bis": erfasste Tage plus Minus für vergessene Arbeitstage."""
    summe = 0
    for eintrag in eintraege:
        if von <= eintrag.datum <= bis:
            summe = summe + saldo_fuer_eintrag(eintrag, abwesenheiten, einstellungen)
    return summe + summe_fehltage(eintraege, abwesenheiten, von, bis, einstellungen, heute)


def saldo_gesamt(eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit], einstellungen: Einstellungen,
                 heute: date) -> int:
    """Gleitzeit über die ganze Zeit."""
    return saldo_zeitraum(eintraege, abwesenheiten, date(1900, 1, 1), date(2999, 12, 31), einstellungen, heute)


def letzter_tag_im_monat(jahr: int, monat: int) -> date:
    """Letzter Tag eines Monats, z.B. 30.09. oder 31.12."""
    return date(jahr, monat, calendar.monthrange(jahr, monat)[1])


# Eingaben prüfen 

def pruefe_abwesenheit(neu: Abwesenheit, abwesenheiten: list[Abwesenheit]) -> str:
    """Prüft eine neue Abwesenheit. Gibt den Fehlertext zurück oder ""."""
    if neu.bis < neu.von:
        return "Das Ende der Abwesenheit liegt vor dem Beginn."
    if neu.art not in ARTEN_ABWESENHEIT:
        return "Unbekannte Art der Abwesenheit."
    for vorhanden in abwesenheiten:
        if neu.von <= vorhanden.bis and neu.bis >= vorhanden.von:
            return ("Überschneidet sich mit " + vorhanden.art + " vom " + vorhanden.von.strftime("%d.%m.%Y")
                    + " bis " + vorhanden.bis.strftime("%d.%m.%Y") + ".")
    return ""


def pruefe_einstellungen(einstellungen: Einstellungen) -> str:
    """Prüft Wochenstunden und Ampelgrenzen (Plus und Minus). Gibt den Fehlertext zurück oder ""."""
    e = einstellungen
    if e.wochenstunden not in [30, 35, 40]:
        return "Die Wochenarbeitszeit muss 30, 35 oder 40 Stunden betragen."
    grenzen = [e.ampel_orange_stunden, e.ampel_rot_stunden, e.ampel_minus_orange_stunden, e.ampel_minus_rot_stunden]
    for grenze in grenzen:
        if grenze < 0:
            return "Die Ampelgrenzen dürfen nicht negativ sein."
    if e.ampel_rot_stunden <= e.ampel_orange_stunden:
        return "Die Rot-Grenze muss über der Orange-Grenze liegen."
    if e.ampel_minus_rot_stunden <= e.ampel_minus_orange_stunden:
        return "Bei den Minusstunden muss die Rot-Grenze über der Orange-Grenze liegen."
    if len(e.name) > 40:
        return "Der Name darf höchstens 40 Zeichen lang sein."
    return ""


# Ampel

def stunden_mit_komma(stunden: float) -> str:
    """Macht aus 37.14 den Text "37,1"."""
    text = str(round(stunden, 1))
    return text.replace(".", ",")


def grenze_als_text(grenze: float) -> str:
    """Macht aus 40.0 den Text "40" und aus 37.5 den Text "37.5"."""
    if grenze == int(grenze):
        return str(int(grenze))
    return str(grenze)


def ampel_plus(stunden: float, einstellungen: Einstellungen) -> dict:
    """Ampel bei Plusstunden: orange ab der Orange-Grenze, rot ab der Rot-Grenze."""
    orange = einstellungen.ampel_orange_stunden
    rot = einstellungen.ampel_rot_stunden
    if stunden >= rot:
        return {"farbe": "rot", "text": "Rot",
                "hinweis": "Ihr Stundenkonto ist ausgeufert. Bitte Abbau mit dem Vorgesetzten abstimmen.",
                "rest": "Grenze von +" + grenze_als_text(rot) + " h überschritten",
                "prozent": 100.0}
    if stunden >= orange:
        return {"farbe": "orange", "text": "Orange",
                "hinweis": "Ihr Stundenkonto wächst. Planen Sie Ausgleichstage ein.",
                "rest": "noch " + stunden_mit_komma(rot - stunden) + " h bis Rot (+" + grenze_als_text(rot) + " h)",
                "prozent": (stunden - orange) / max(1.0, rot - orange) * 100}
    return {"farbe": "gruen", "text": "Grün",
            "hinweis": "Ihr Stundenkonto liegt im normalen Bereich.",
            "rest": "noch " + stunden_mit_komma(orange - stunden) + " h bis Orange (+" + grenze_als_text(orange) + " h)",
            "prozent": stunden / max(1.0, orange) * 100}


def ampel_minus(stunden: float, einstellungen: Einstellungen) -> dict:
    """Ampel bei Minusstunden: orange ab der Minus-Orange-Grenze, rot ab der Minus-Rot-Grenze."""
    minus = -stunden
    orange = einstellungen.ampel_minus_orange_stunden
    rot = einstellungen.ampel_minus_rot_stunden
    if minus >= rot:
        return {"farbe": "rot", "text": "Rot",
                "hinweis": "Ihr Stundenkonto ist stark im Minus. Bitte Abbau mit dem Vorgesetzten abstimmen.",
                "rest": "Grenze von −" + grenze_als_text(rot) + " h unterschritten",
                "prozent": 100.0}
    if minus >= orange:
        return {"farbe": "orange", "text": "Orange",
                "hinweis": "Ihr Stundenkonto ist im Minus. Planen Sie zusätzliche Arbeitszeit ein.",
                "rest": "noch " + stunden_mit_komma(rot - minus) + " h bis Rot (−" + grenze_als_text(rot) + " h)",
                "prozent": (minus - orange) / max(1.0, rot - orange) * 100}
    return {"farbe": "gruen", "text": "Grün",
            "hinweis": "Ihr Stundenkonto liegt im normalen Bereich.",
            "rest": "noch " + stunden_mit_komma(orange - minus) + " h bis Orange (−" + grenze_als_text(orange) + " h)",
            "prozent": minus / max(1.0, orange) * 100}


def ampel(saldo_minuten: int, einstellungen: Einstellungen) -> dict:
    """Ampel für das Stundenkonto: gilt für Plus- und für Minusstunden, jeweils grün, orange, rot."""
    stunden = saldo_minuten / 60
    if stunden < 0:
        return ampel_minus(stunden, einstellungen)
    return ampel_plus(stunden, einstellungen)


# Tagesliste für die Oberfläche

def eintrag_fuer_api(eintrag: Zeiteintrag) -> dict:
    """Zeiteintrag so, wie die Oberfläche ihn erwartet."""
    pausen = []
    for pause in pausen_von(eintrag):
        pausen.append({"ab": zeit_oder_leer(pause.beginn), "minuten": pause.minuten})
    return {"beginn": zeit_zu_text(eintrag.beginn), "ende": zeit_zu_text(eintrag.ende),
            "pause": eintrag.pause_minuten, "pausen": pausen}


def abwesenheit_fuer_api(abwesenheit: Abwesenheit) -> dict:
    """Abwesenheit so, wie die Oberfläche sie erwartet."""
    return {"von": datum_zu_text(abwesenheit.von), "bis": datum_zu_text(abwesenheit.bis),
            "art": abwesenheit.art, "grund": abwesenheit.grund}


def bewerte_eintrag(eintrag: Zeiteintrag, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                    einstellungen: Einstellungen, heute: date) -> dict:
    """Rechnet Ist, Soll, Saldo, Status und Meldungen für einen Arbeitstag aus."""
    vortag_datum = eintrag.datum - timedelta(days=1)
    vortag = finde_eintrag(eintraege, vortag_datum)
    vortag_fehlt = ist_fehltag(vortag_datum, heute, eintraege, abwesenheiten, einstellungen)
    meldungen = arbzg.pruefe_tag(eintrag, vortag, vortag_fehlt)
    meldungen.extend(arbzg.pruefe_mit_anderen_tagen(eintrag, eintraege, abwesenheiten,
                                                    erfassung_beginn(eintraege, einstellungen), heute))
    return {"ist": ist_fuer_eintrag(eintrag),
            "soll": soll_fuer_tag(eintrag.datum, abwesenheiten, einstellungen),
            "saldo": saldo_fuer_eintrag(eintrag, abwesenheiten, einstellungen),
            "status": arbzg.status_aus_meldungen(meldungen), "meldungen": meldungen}


def tag_fuer_api(datum: date, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                 einstellungen: Einstellungen, heute: date) -> dict:
    """Ein Tag mit allem, was die Oberfläche zeigen will."""
    eintrag = finde_eintrag(eintraege, datum)
    abwesenheit = finde_abwesenheit(abwesenheiten, datum)
    tag = {"datum": datum_zu_text(datum), "wochentag": wochentag_name(datum), "wochenende": ist_wochenende(datum),
           "feiertag": arbzg.feiertag_name(datum), "eintrag": None, "abwesenheit": None,
           "soll": soll_fuer_tag(datum, abwesenheiten, einstellungen), "ist": 0, "saldo": 0,
           "status": "", "meldungen": [], "fehlt": False}
    if abwesenheit is not None:
        tag["abwesenheit"] = abwesenheit_fuer_api(abwesenheit)

    # Vergessener Arbeitstag zählt mit minus Soll
    if ist_fehltag(datum, heute, eintraege, abwesenheiten, einstellungen):
        tag["fehlt"] = True
        tag["saldo"] = -tag["soll"]
    if eintrag is not None:
        bewertung = bewerte_eintrag(eintrag, eintraege, abwesenheiten, einstellungen, heute)
        tag["eintrag"] = eintrag_fuer_api(eintrag)
        for schluessel in ["ist", "saldo", "status", "meldungen"]:
            tag[schluessel] = bewertung[schluessel]
    return tag


def tage_fuer_zeitraum(von: date, bis: date, eintraege: list[Zeiteintrag], abwesenheiten: list[Abwesenheit],
                       einstellungen: Einstellungen, heute: date) -> list[dict]:
    """Alle Tage von "von" bis "bis" (Monat, Quartal oder Jahr) als Liste für die Oberfläche."""
    tage = []
    datum = von
    while datum <= bis:
        tage.append(tag_fuer_api(datum, eintraege, abwesenheiten, einstellungen, heute))
        datum = datum + timedelta(days=1)
    return tage
