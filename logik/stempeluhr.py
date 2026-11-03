"""Stempeluhr: Einstempeln, Pause, Ausstempeln. Zeiten stehen als Text "2026-09-15T08:00:00" im Zustand."""
from datetime import datetime, time, timedelta

from logik.modelle import Zeiteintrag
from logik.zeit import PAUSE_ABSCHNITT_MIN

ZEITFORMAT = "%Y-%m-%dT%H:%M:%S"


def neuer_zustand() -> dict:
    """Leere Stempeluhr."""
    return {"status": "aus", "beginn": None, "pausen": []}


def zeitpunkt_zu_text(zeitpunkt: datetime) -> str:
    """datetime in Zeitformat: 2026-09-15T08:00:00."""
    return zeitpunkt.strftime(ZEITFORMAT)


def text_zu_zeitpunkt(text: str) -> datetime:
    """2026-09-15T08:00:00 in datetime."""
    return datetime.strptime(text, ZEITFORMAT)


# Bedienung

def einstempeln(zustand: dict, jetzt: datetime):
    """Startet den Arbeitstag. Geht nur, wenn die Uhr aus ist."""
    if zustand["status"] != "aus":
        return
    zustand["status"] = "arbeitet"
    zustand["beginn"] = zeitpunkt_zu_text(jetzt)
    zustand["pausen"] = []


def pause_starten(zustand: dict, jetzt: datetime):
    """Beginnt eine Pause. Geht nur, wenn gerade gearbeitet wird."""
    if zustand["status"] != "arbeitet":
        return
    zustand["pausen"].append({"von": zeitpunkt_zu_text(jetzt), "bis": None})
    zustand["status"] = "pause"


def pause_beenden(zustand: dict, jetzt: datetime):
    """Beendet die laufende Pause."""
    if zustand["status"] != "pause":
        return
    letzte_pause = zustand["pausen"][len(zustand["pausen"]) - 1]
    letzte_pause["bis"] = zeitpunkt_zu_text(jetzt)
    zustand["status"] = "arbeitet"


def pause_dauer(pause: dict) -> timedelta:
    """Wie lange eine beendete Pause gedauert hat."""
    return text_zu_zeitpunkt(pause["bis"]) - text_zu_zeitpunkt(pause["von"])


def zaehlende_pausen(zustand: dict) -> list[dict]:
    """Beendete Pausen ab 15 Minuten. Kürzere sind keine Ruhepause und zählen als Arbeitszeit."""
    pausen = []
    for pause in zustand["pausen"]:
        if pause["bis"] is not None and pause_dauer(pause) >= timedelta(minutes=PAUSE_ABSCHNITT_MIN):
            pausen.append(pause)
    return pausen


def pausen_minuten(zustand: dict) -> int:
    """Summe der zählenden Pausen in Minuten (gerundet)."""
    sekunden = 0
    for pause in zaehlende_pausen(zustand):
        sekunden = sekunden + pause_dauer(pause).total_seconds()
    return round(sekunden / 60)


def erste_pause_ab(zustand: dict):
    """Uhrzeit, zu der die erste zählende Pause begann. None, wenn es keine gab."""
    pausen = zaehlende_pausen(zustand)
    if len(pausen) == 0:
        return None
    von = text_zu_zeitpunkt(pausen[0]["von"])
    return time(von.hour, von.minute)


def zuruecksetzen(zustand: dict):
    """Stellt die Uhr wieder auf aus."""
    zustand["status"] = "aus"
    zustand["beginn"] = None
    zustand["pausen"] = []


def ausstempeln(zustand: dict, jetzt: datetime):
    """Beendet den Arbeitstag, auch nach Mitternacht. Gibt (Zeiteintrag, Hinweistext) zurück.
    Bei Uhr aus oder mehr als 24 Stunden gibt es keinen Eintrag (None)."""
    if zustand["status"] == "aus":
        return None, ""
    if zustand["status"] == "pause":
        pause_beenden(zustand, jetzt)

    beginn = text_zu_zeitpunkt(zustand["beginn"])
    if jetzt - beginn >= timedelta(hours=24):
        zuruecksetzen(zustand)
        return None, "Die Stempeluhr lief länger als 24 Stunden. Bitte den Arbeitstag im Kalender nachtragen."

    # In derselben Minute aus- wie eingestempelt: eine Minute zählen
    ende = jetzt
    if ende.hour == beginn.hour and ende.minute == beginn.minute:
        ende = beginn + timedelta(minutes=1)

    pause = pausen_minuten(zustand)
    kurze_pausen = len(zustand["pausen"]) - len(zaehlende_pausen(zustand))
    # Ohne zählende Pause gibt es keinen Pausenbeginn
    pause_ab = None
    if pause > 0:
        pause_ab = erste_pause_ab(zustand)
    eintrag = Zeiteintrag(beginn.date(), time(beginn.hour, beginn.minute), time(ende.hour, ende.minute),
                          pause, pause_ab)
    hinweis = ("Ausgestempelt. Eintrag für " + beginn.strftime("%d.%m.%Y") + " gespeichert: "
               + beginn.strftime("%H:%M") + " bis " + ende.strftime("%H:%M") + ", "
               + str(eintrag.pause_minuten) + " min Pause.")
    if kurze_pausen > 0:
        hinweis = hinweis + " Pausen unter " + str(PAUSE_ABSCHNITT_MIN) + " min zählen als Arbeitszeit."
    zuruecksetzen(zustand)
    return eintrag, hinweis