"""Datenklassen für Wendezeit."""
from dataclasses import dataclass, field
from datetime import date, time

from logik.zeit import pause_lage


@dataclass
class Pause:
    """Eine Pause innerhalb eines Arbeitstags."""
    beginn: time
    minuten: int


@dataclass
class Zeiteintrag:
    """Ein Arbeitstag. Liegt das Ende vor dem Beginn, endet die Schicht am nächsten Tag."""
    datum: date
    beginn: time
    ende: time
    pause_minuten: int          # alle Pausen zusammen
    pause_beginn: time = None   # Beginn der ersten Pause; None, wenn es keine Pause gab
    pausen: list[Pause] = field(default_factory=list)   # mehrere Pausen einzeln; leer = höchstens eine Pause


def eintrag_mit_pausen(datum: date, beginn: time, ende: time, pausen: list[Pause]) -> Zeiteintrag:
    """Baut einen Eintrag aus einzelnen Pausen. Summe und erster Pausenbeginn ergeben sich daraus.
    Pausen mit 0 Minuten fallen weg."""
    echte_pausen = []
    alle_mit_beginn = True
    for pause in pausen:
        if pause.minuten != 0:
            echte_pausen.append(pause)
            if pause.beginn is None:
                alle_mit_beginn = False
    pausen = echte_pausen

    # Nach Lage in der Schicht sortieren, damit 2:00 bei einer Nachtschicht nach 23:30 kommt.
    # Fehlt ein Beginn, meldet das pruefe_eingabe, dann bleibt die Reihenfolge
    if alle_mit_beginn:
        nach_lage = []
        for nummer in range(len(pausen)):
            nach_lage.append((pause_lage(beginn, pausen[nummer].beginn), nummer))
        nach_lage.sort()
        sortiert = []
        for lage, nummer in nach_lage:
            sortiert.append(pausen[nummer])
        pausen = sortiert

    summe = 0
    for pause in pausen:
        summe = summe + pause.minuten
    erster_beginn = None
    if len(pausen) > 0:
        erster_beginn = pausen[0].beginn
    return Zeiteintrag(datum, beginn, ende, summe, erster_beginn, pausen)


def pausen_von(eintrag: Zeiteintrag) -> list[Pause]:
    """Alle Pausen eines Eintrags. Einträge mit nur einer Pause haben keine Liste, dann wird sie gebaut."""
    if len(eintrag.pausen) > 0:
        return eintrag.pausen
    if eintrag.pause_minuten > 0:
        return [Pause(eintrag.pause_beginn, eintrag.pause_minuten)]
    return []


@dataclass
class Abwesenheit:
    """Ein Zeitraum ohne Arbeit: Urlaub, Krankheit, Sonderurlaub oder Sonstige Abwesenheit."""
    von: date
    bis: date
    art: str          # "Urlaub", "Krankheit", "Sonderurlaub", "Sonstige Abwesenheit"
    grund: str = ""   # nur bei Sonstige Abwesenheit


@dataclass
class Einstellungen:
    """Alles, was der Mitarbeiter einstellen kann."""
    wochenstunden: int = 40 #Soll
    ampel_orange_stunden: float = 40.0 #ab wie viel Plusstunden wird Ampel orange
    ampel_rot_stunden: float = 80.0 #ab wie viel Plusstunden wird Ampel rot
    passwort_hash: str = "" 
    passwort_salt: str = ""
    erfassung_ab: date = None   # ab hier zählen fehlende Arbeitstage als Minus; None = erster Eintrag
    ampel_minus_orange_stunden: float = 10.0   # ab wie viel Minusstunden orange
    ampel_minus_rot_stunden: float = 20.0      # ab wie viel Minusstunden rot
    name: str = ""                              # Name unten links; leer = "Mitarbeiter"
