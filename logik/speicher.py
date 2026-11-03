"""JSON-Dateien laden und speichern, Passwort-Hash, Listen durchsuchen."""
import hashlib
import json
import os
import secrets
from datetime import date, time

from logik.modelle import Zeiteintrag, Abwesenheit, Einstellungen, Pause, eintrag_mit_pausen

# Der Ordner "daten" liegt neben app.py
PROJEKT_ORDNER = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
# Auf Railway steht in WENDEZEIT_DATEN der Pfad zum Volume, sonst wären die Daten nach jedem Deploy weg
DATEN_ORDNER = os.environ.get("WENDEZEIT_DATEN", os.path.join(PROJEKT_ORDNER, "daten"))

DATEI_EINTRAEGE = "zeiteintraege.json"
DATEI_ABWESENHEITEN = "abwesenheiten.json"
DATEI_EINSTELLUNGEN = "einstellungen.json"
DATEI_STEMPELUHR = "stempeluhr.json"


# JSON lesen und schreiben

def lade_json(dateiname: str, standard, ordner: str = DATEN_ORDNER):
    """Liest eine JSON-Datei. Fehlt die Datei, kommt standard zurück."""
    pfad = os.path.join(ordner, dateiname)
    if not os.path.exists(pfad):
        return standard
    with open(pfad, "r", encoding="utf-8") as datei:
        return json.load(datei)


def speichere_json(dateiname: str, daten, ordner: str = DATEN_ORDNER):
    """Schreibt Daten als JSON-Datei. Legt den Ordner an, wenn er fehlt."""
    os.makedirs(ordner, exist_ok=True) #erstellt Ordner falls er nicht existiert
    pfad = os.path.join(ordner, dateiname)
    with open(pfad, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, indent=2, ensure_ascii=False) #ensure_ascii für Umlaute/Sonderzeichen 


# Datum und Uhrzeit als Text

def datum_zu_text(datum: date) -> str:
    """Macht aus einem Datum den Text "2026-10-01"."""
    return datum.isoformat()


def text_zu_datum(text: str) -> date:
    """Macht aus "2026-10-01" wieder ein Datum."""
    return date.fromisoformat(text)


def zeit_zu_text(zeit: time) -> str:
    """Macht aus einer Uhrzeit den Text "08:30"."""
    #zeit_zu_text wirft bewusst Fehler falls der Zeiteintrag (Arbeit) kein Beginn/Ende hat
    return zeit.strftime("%H:%M")


def text_zu_zeit(text: str) -> time:
    """Macht aus "08:30" wieder eine Uhrzeit."""
    teile = text.split(":")
    return time(int(teile[0]), int(teile[1]))


# Zeiteinträge 

def zeit_oder_leer(zeit) -> str:
    """Uhrzeit als Text "08:30", fehlende Uhrzeit (None) als ""."""
    #getrennt von zeit_zu_text, da nur Pausenbeginn/ende still fehlen darf
    if zeit is None:
        return ""
    return zeit_zu_text(zeit)


def text_oder_none_zu_zeit(text: str):
    """Text "08:30" als Uhrzeit, leerer Text als None."""
    if text == "":
        return None
    return text_zu_zeit(text)


def text_oder_none_zu_datum(text: str):
    """Text "2026-10-01" als Datum, leerer Text als None."""
    if text == "":
        return None
    return text_zu_datum(text)


def eintrag_zu_dict(eintrag: Zeiteintrag) -> dict:
    """Wandelt einen Zeiteintrag in ein Dictionary für JSON um."""
    pausen = []
    for pause in eintrag.pausen:
        pausen.append({"beginn": zeit_oder_leer(pause.beginn), "minuten": pause.minuten})
    return {
        "datum": datum_zu_text(eintrag.datum),
        "beginn": zeit_zu_text(eintrag.beginn),
        "ende": zeit_zu_text(eintrag.ende),
        "pause_minuten": eintrag.pause_minuten,
        "pause_beginn": zeit_oder_leer(eintrag.pause_beginn),
        "pausen": pausen,
    }


def dict_zu_eintrag(daten: dict) -> Zeiteintrag:
    """Wandelt ein Dictionary aus JSON in einen Zeiteintrag um. Ohne Pause ist der Pausenbeginn leer.
    Ältere Einträge haben kein Feld "pausen", sie hatten nur eine Pause."""
    if len(daten.get("pausen", [])) > 0:
        pausen = []
        for pause in daten["pausen"]:
            pausen.append(Pause(text_oder_none_zu_zeit(pause["beginn"]), int(pause["minuten"])))
        return eintrag_mit_pausen(text_zu_datum(daten["datum"]), text_zu_zeit(daten["beginn"]),
                                  text_zu_zeit(daten["ende"]), pausen)
    return Zeiteintrag(
        datum=text_zu_datum(daten["datum"]),
        beginn=text_zu_zeit(daten["beginn"]),
        ende=text_zu_zeit(daten["ende"]),
        pause_minuten=int(daten["pause_minuten"]),
        pause_beginn=text_oder_none_zu_zeit(daten["pause_beginn"]),
    )


def lade_eintraege(ordner: str = DATEN_ORDNER) -> list[Zeiteintrag]:
    """Lädt alle Zeiteinträge, sortiert nach Datum."""
    liste = []
    for daten in lade_json(DATEI_EINTRAEGE, [], ordner):
        liste.append(dict_zu_eintrag(daten))
    sortiere_eintraege(liste)
    return liste


def speichere_eintraege(eintraege: list[Zeiteintrag], ordner: str = DATEN_ORDNER):
    """Speichert alle Zeiteinträge."""
    liste = []
    for eintrag in eintraege:
        liste.append(eintrag_zu_dict(eintrag))
    speichere_json(DATEI_EINTRAEGE, liste, ordner)


# Abwesenheiten 

def abwesenheit_zu_dict(abwesenheit: Abwesenheit) -> dict:
    """Wandelt eine Abwesenheit in ein Dictionary für JSON um."""
    return {
        "von": datum_zu_text(abwesenheit.von),
        "bis": datum_zu_text(abwesenheit.bis),
        "art": abwesenheit.art,
        "grund": abwesenheit.grund,
    }


def dict_zu_abwesenheit(daten: dict) -> Abwesenheit:
    """Wandelt ein Dictionary aus JSON in eine Abwesenheit um."""
    return Abwesenheit(
        von=text_zu_datum(daten["von"]),
        bis=text_zu_datum(daten["bis"]),
        art=daten["art"],
        grund=daten.get("grund", ""),
    )


def lade_abwesenheiten(ordner: str = DATEN_ORDNER) -> list[Abwesenheit]:
    """Lädt alle Abwesenheiten."""
    liste = []
    for daten in lade_json(DATEI_ABWESENHEITEN, [], ordner):
        liste.append(dict_zu_abwesenheit(daten))
    return liste


def speichere_abwesenheiten(abwesenheiten: list[Abwesenheit], ordner: str = DATEN_ORDNER):
    """Speichert alle Abwesenheiten."""
    liste = []
    for abwesenheit in abwesenheiten:
        liste.append(abwesenheit_zu_dict(abwesenheit))
    speichere_json(DATEI_ABWESENHEITEN, liste, ordner)


# Einstellungen 

def lade_einstellungen(ordner: str = DATEN_ORDNER) -> Einstellungen:
    """Lädt die Einstellungen. Fehlt die Datei, gelten die Standardwerte."""
    daten = lade_json(DATEI_EINSTELLUNGEN, {}, ordner)
    einstellungen = Einstellungen()
    einstellungen.wochenstunden = int(daten.get("wochenstunden", 40)) # Zahl bildet immer Standardwert ab
    einstellungen.ampel_orange_stunden = float(daten.get("ampel_orange_stunden", 40.0))
    einstellungen.ampel_rot_stunden = float(daten.get("ampel_rot_stunden", 80.0))
    einstellungen.passwort_hash = daten.get("passwort_hash", "")
    einstellungen.passwort_salt = daten.get("passwort_salt", "")
    einstellungen.ampel_minus_orange_stunden = float(daten.get("ampel_minus_orange_stunden", 10.0))
    einstellungen.ampel_minus_rot_stunden = float(daten.get("ampel_minus_rot_stunden", 20.0))
    einstellungen.name = daten.get("name", "")
    if daten.get("erfassung_ab", "") != "":
        einstellungen.erfassung_ab = text_zu_datum(daten["erfassung_ab"])
    return einstellungen


def speichere_einstellungen(einstellungen: Einstellungen, ordner: str = DATEN_ORDNER):
    """Speichert die Einstellungen."""
    daten = {
        "wochenstunden": einstellungen.wochenstunden,
        "ampel_orange_stunden": einstellungen.ampel_orange_stunden,
        "ampel_rot_stunden": einstellungen.ampel_rot_stunden,
        "passwort_hash": einstellungen.passwort_hash,
        "passwort_salt": einstellungen.passwort_salt,
        "erfassung_ab": "",
        "ampel_minus_orange_stunden": einstellungen.ampel_minus_orange_stunden,
        "ampel_minus_rot_stunden": einstellungen.ampel_minus_rot_stunden,
        "name": einstellungen.name,
    }
    if einstellungen.erfassung_ab is not None:
        daten["erfassung_ab"] = datum_zu_text(einstellungen.erfassung_ab)
    speichere_json(DATEI_EINSTELLUNGEN, daten, ordner)


# Stempeluhr 

def lade_stempeluhr(ordner: str = DATEN_ORDNER) -> dict:
    """Lädt den Zustand der Stempeluhr. Fehlt die Datei, ist die Uhr aus."""
    return lade_json(DATEI_STEMPELUHR, {"status": "aus", "beginn": None, "pausen": []}, ordner)


def speichere_stempeluhr(zustand: dict, ordner: str = DATEN_ORDNER):
    """Speichert den Zustand der Stempeluhr."""
    speichere_json(DATEI_STEMPELUHR, zustand, ordner)


# Passwort 

def passwort_hash_erzeugen(passwort: str):
    """Erzeugt Salt und Hash für ein Passwort. Gibt (hash, salt) zurück."""
    salt = secrets.token_hex(16) #erzeugt 16 zufällige bytes (nicht vorhersehbar)
    hash_wert = hashlib.sha256((salt + passwort).encode("utf-8")).hexdigest() 
    return hash_wert, salt #ohne salt passwort nicht mehr prüfbar


def passwort_pruefen(passwort: str, hash_wert: str, salt: str) -> bool:
    """Prüft, ob ein eingegebenes Passwort zum gespeicherten Hash passt."""
    vergleich = hashlib.sha256((salt + passwort).encode("utf-8")).hexdigest()
    return vergleich == hash_wert


# Listen durchsuchen und pflegen 

def sortiere_eintraege(eintraege: list[Zeiteintrag]):
    """Sortiert Zeiteinträge nach Datum (einfaches Tauschen, Bubble Sort)."""
    for i in range(len(eintraege)):
        for j in range(len(eintraege) - 1 - i):
            if eintraege[j].datum > eintraege[j + 1].datum:
                eintraege[j], eintraege[j + 1] = eintraege[j + 1], eintraege[j]


def finde_eintrag(eintraege: list[Zeiteintrag], datum: date):
    """Sucht den Zeiteintrag zu einem Datum. None, wenn es keinen gibt."""
    for eintrag in eintraege:
        if eintrag.datum == datum:
            return eintrag
    return None


def finde_abwesenheit(abwesenheiten: list[Abwesenheit], datum: date):
    """Sucht die Abwesenheit, in deren Zeitraum das Datum liegt. None, wenn keine."""
    for abwesenheit in abwesenheiten:
        if abwesenheit.von <= datum <= abwesenheit.bis:
            return abwesenheit
    return None


def entferne_eintrag(eintraege: list[Zeiteintrag], datum: date):
    """Entfernt den Zeiteintrag mit diesem Datum aus der Liste."""
    neue_liste = []
    for eintrag in eintraege:
        if eintrag.datum != datum:
            neue_liste.append(eintrag)
    eintraege.clear()
    eintraege.extend(neue_liste)


def setze_eintrag(eintraege: list[Zeiteintrag], neuer_eintrag: Zeiteintrag):
    """Ersetzt den Eintrag am selben Datum oder hängt ihn neu an."""
    entferne_eintrag(eintraege, neuer_eintrag.datum)
    eintraege.append(neuer_eintrag)
    sortiere_eintraege(eintraege)


def entferne_abwesenheit(abwesenheiten: list[Abwesenheit], von: date):
    """Entfernt alle Abwesenheiten, die an diesem Datum beginnen."""
    neue_liste = []
    for abwesenheit in abwesenheiten:
        if abwesenheit.von != von:
            neue_liste.append(abwesenheit)
    abwesenheiten.clear()
    abwesenheiten.extend(neue_liste)
