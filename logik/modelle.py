"""Datenklassen für Wendezeit."""
from dataclasses import dataclass
from datetime import date, time


@dataclass
class Zeiteintrag:
    """Ein Arbeitstag. Liegt das Ende vor dem Beginn, endet die Schicht am nächsten Tag."""
    datum: date
    beginn: time
    ende: time
    pause_minuten: int
    pause_beginn: time = None   # Uhrzeit, ab der die Pause lief; None, wenn es keine Pause gab


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
