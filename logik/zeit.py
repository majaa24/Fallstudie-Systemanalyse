"""Rechnen mit Uhrzeiten, Minuten und Sollzeit."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

# Betriebliche Arbeitszeit zählt nur zwischen 6:00 und 22:00 Uhr
BETRIEB_BEGINN_MIN = 6 * 60
BETRIEB_ENDE_MIN = 22 * 60
MINUTEN_JE_TAG = 24 * 60


def zeit_in_minuten(zeit: time) -> int:
    """Rechnet eine Uhrzeit in Minuten seit Mitternacht um."""
    return zeit.hour * 60 + zeit.minute


def ist_nachtschicht(beginn: time, ende: time) -> bool:
    """Endet die Arbeit erst am nächsten Tag?"""
    return zeit_in_minuten(ende) < zeit_in_minuten(beginn)


def ende_in_minuten(beginn: time, ende: time) -> int:
    """Ende in Minuten ab Mitternacht des Starttags. Endet die Schicht nach Mitternacht, kommen 24h dazu."""
    ende_min = zeit_in_minuten(ende)
    if ist_nachtschicht(beginn, ende):
        ende_min = ende_min + MINUTEN_JE_TAG
    return ende_min


def berechne_arbeitsminuten(beginn: time, ende: time, pause_minuten: int) -> int:
    """Rechnet die Arbeitszeit in Minuten aus (ohne Pause), auch über Mitternacht."""
    arbeit = ende_in_minuten(beginn, ende) - zeit_in_minuten(beginn) - pause_minuten
    # um negative/ungültige Einträge zu vermeiden
    if arbeit < 0:
        arbeit = 0
    return arbeit


# Betriebliche Arbeitszeit (6 bis 22 Uhr)

def ueberschneidung(von_a: int, bis_a: int, von_b: int, bis_b: int) -> int:
    """Wie viele Minuten zwei Zeitspannen gemeinsam haben."""
    von = max(von_a, von_b) #späterer beginn ist entscheidend
    bis = min(bis_a, bis_b) #früheres ende ist entscheidend
    if bis < von:
        return 0 #keine überlappung
    return bis - von


def minuten_im_betrieb(von: int, bis: int) -> int:
    """Minuten einer Zeitspanne, die in 6 bis 22 Uhr liegen (am Starttag und am Folgetag)."""
    heute = ueberschneidung(von, bis, BETRIEB_BEGINN_MIN, BETRIEB_ENDE_MIN)
    morgen = ueberschneidung(von, bis, BETRIEB_BEGINN_MIN + MINUTEN_JE_TAG, BETRIEB_ENDE_MIN + MINUTEN_JE_TAG)
    return heute + morgen


def pause_lage(beginn: time, pause_beginn: time) -> int:
    """Beginn der Pause in Minuten ab Mitternacht des Starttags."""
    beginn_min = zeit_in_minuten(beginn)
    lage = zeit_in_minuten(pause_beginn)
    # Pause nach Mitternacht in einer Nachtschicht
    if lage < beginn_min:
        lage = lage + MINUTEN_JE_TAG
    return lage


def berechne_betriebsminuten(beginn: time, ende: time, pause_minuten: int, pause_beginn) -> int:
    """Arbeitsminuten für die Gleitzeit. Es zählt nur die Zeit zwischen 6 und 22 Uhr.
    Die Pause wird nur abgezogen, soweit sie auch zwischen 6 und 22 Uhr lag."""
    beginn_min = zeit_in_minuten(beginn)
    ende_min = ende_in_minuten(beginn, ende)
    arbeit = minuten_im_betrieb(beginn_min, ende_min)
    # Bei 0 Minuten gab es keine Pause, dann wird nichts abgezogen
    pause = 0
    if pause_minuten > 0:
        pause_von = pause_lage(beginn, pause_beginn)
        pause = minuten_im_betrieb(pause_von, pause_von + pause_minuten)
    ergebnis = arbeit - pause
    if ergebnis < 0:
        ergebnis = 0
    return ergebnis


def liegt_ausserhalb_betriebszeit(beginn: time, ende: time) -> bool:
    """Sagt, ob die Arbeit vor 6:00 beginnt, nach 22:00 Uhr endet oder über Mitternacht geht."""
    if ist_nachtschicht(beginn, ende):
        return True
    return zeit_in_minuten(beginn) < BETRIEB_BEGINN_MIN or zeit_in_minuten(ende) > BETRIEB_ENDE_MIN


def laengste_zeit_ohne_pause(beginn: time, ende: time, pause_minuten: int, pause_beginn) -> int:
    """Längste Zeit am Stück ohne Pause in Minuten (Pause als ein Block)."""
    beginn_min = zeit_in_minuten(beginn)
    ende_min = ende_in_minuten(beginn, ende)
    # Ohne Pause wurde der ganze Tag am Stück gearbeitet
    if pause_minuten == 0:
        return ende_min - beginn_min
    pause_von = pause_lage(beginn, pause_beginn)
    return max(pause_von - beginn_min, ende_min - (pause_von + pause_minuten))


# Eingaben prüfen 

def pruefe_eingabe(beginn: time, ende: time, pause_minuten: int, pause_beginn) -> str:
    """Prüft einen Arbeitstag auf unmögliche Angaben. Gibt den Fehlertext zurück oder ""."""
    if zeit_in_minuten(beginn) == zeit_in_minuten(ende):
        return "Beginn und Ende dürfen nicht gleich sein."
    if pause_minuten < 0:
        return "Die Pause darf nicht negativ sein."
    dauer = ende_in_minuten(beginn, ende) - zeit_in_minuten(beginn)
    if pause_minuten >= dauer:
        return "Die Pause ist länger als die Arbeitszeit."

    # Wer Pause gemacht hat, muss angeben, ab wann. Sonst lässt sich § 4 ArbZG nicht prüfen
    if pause_minuten > 0 and pause_beginn is None:
        return "Bitte angeben, ab wann die Pause war."

    # Die Pause muss innerhalb der Arbeitszeit liegen
    if pause_minuten > 0:
        pause_von = pause_lage(beginn, pause_beginn)
        if pause_von < zeit_in_minuten(beginn) or pause_von + pause_minuten > ende_in_minuten(beginn, ende):
            return "Die Pause muss zwischen Beginn und Ende liegen."
    return ""


# Soll und Kalender

def sollminuten_je_tag(wochenstunden: int) -> int:
    """Sollzeit je Arbeitstag: Wochenstunden auf 5 Tage verteilt."""
    return round(wochenstunden * 60 / 5)


def ist_wochenende(datum: date) -> bool:
    """Samstag oder Sonntag?"""
    return datum.weekday() >= 5


def minuten_als_text(minuten: int) -> str:
    """Macht aus 465 den Text "7:45 h"."""
    stunden = minuten // 60
    rest = minuten % 60
    return str(stunden) + ":" + str(rest).zfill(2) + " h"


WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def wochentag_name(datum: date) -> str:
    """Gibt den deutschen Wochentag zurück, z.B. "Dienstag"."""
    return WOCHENTAGE[datum.weekday()]


# Uhrzeit in Deutschland

def jetzt() -> datetime:
    """Aktuelle Uhrzeit in Deutschland, mit Sommer- und Winterzeit."""
    # Der Server auf Railway läuft in UTC, datetime.now() geht dort 1 bis 2 Stunden nach.
    # Die Zeitzone wird danach wieder entfernt, weil die Stempeluhr Zeiten ohne Zeitzone speichert
    return datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)


def heute() -> date:
    """Heutiges Datum in Deutschland."""
    return jetzt().date()
