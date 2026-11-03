"""Stempeluhr: Einstempeln, Pause, Ausstempeln. Zeiten stehen als Text "2026-09-15T08:00:00" im Zustand."""
from datetime import datetime, time, timedelta

from logik.modelle import Pause, eintrag_mit_pausen

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


def pausen_liste(zustand: dict) -> list[Pause]:
    """Alle beendeten Pausen einzeln, in Minuten gerundet. Unter einer Minute zählt keine Pause."""
    pausen = []
    for pause in zustand["pausen"]:
        if pause["bis"] is not None:
            von = text_zu_zeitpunkt(pause["von"])
            minuten = round((text_zu_zeitpunkt(pause["bis"]) - von).total_seconds() / 60)
            if minuten > 0:
                pausen.append(Pause(time(von.hour, von.minute), minuten))
    return pausen


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

    # Jede Pause bleibt einzeln erhalten, sonst wäre "am Stück" (§ 4 ArbZG) nicht prüfbar
    eintrag = eintrag_mit_pausen(beginn.date(), time(beginn.hour, beginn.minute), time(ende.hour, ende.minute),
                                 pausen_liste(zustand))
    hinweis = ("Ausgestempelt. Eintrag für " + beginn.strftime("%d.%m.%Y") + " gespeichert: "
               + beginn.strftime("%H:%M") + " bis " + ende.strftime("%H:%M") + ", "
               + str(eintrag.pause_minuten) + " min Pause.")
    zuruecksetzen(zustand)
    return eintrag, hinweis