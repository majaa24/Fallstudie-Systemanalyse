"""Lädt die Beispieldaten aus daten_demo/ in den Datenordner. Start: python demo_laden.py

Die Demodaten werden um ganze Wochen verschoben, damit sie bis gestern reichen. So bleiben die
Wochentage gleich und es gibt keine vergessenen Tage. Passwort und Einstellungen bleiben, nur
erfassung_ab wird auf den ersten Demotag gesetzt."""
import os
from datetime import date, timedelta

from logik import arbzg, speicher

PROJEKT_ORDNER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(PROJEKT_ORDNER, "daten_demo")


def wochen_verschiebung(letzter_tag: date, heute: date) -> timedelta:
    """Verschiebung in ganzen Wochen, nach der der letzte Demotag auf gestern oder später fällt."""
    tage = (heute - timedelta(days=1) - letzter_tag).days
    wochen = -(-tage // 7)   # aufrunden
    return timedelta(weeks=wochen)


def demo_laden(heute: date = None, ziel: str = speicher.DATEN_ORDNER) -> list[str]:
    """Verschiebt und speichert die Demodaten. Gibt Hinweise zu Einträgen an Feiertagen zurück."""
    if heute is None:
        heute = date.today()
    eintraege = speicher.lade_eintraege(QUELLE)
    abwesenheiten = speicher.lade_abwesenheiten(QUELLE)

    letzter_tag = max(eintrag.datum for eintrag in eintraege)
    verschiebung = wochen_verschiebung(letzter_tag, heute)
    for eintrag in eintraege:
        eintrag.datum = eintrag.datum + verschiebung
    for abwesenheit in abwesenheiten:
        abwesenheit.von = abwesenheit.von + verschiebung
        abwesenheit.bis = abwesenheit.bis + verschiebung

    # Ab heute ist noch nichts gearbeitet, diese Tage fallen weg
    eintraege = [eintrag for eintrag in eintraege if eintrag.datum < heute]
    speicher.speichere_eintraege(eintraege, ziel)
    speicher.speichere_abwesenheiten(abwesenheiten, ziel)

    # Ohne passendes erfassung_ab würden die Wochen vor den Demodaten als vergessen zählen
    einstellungen = speicher.lade_einstellungen(ziel)
    einstellungen.erfassung_ab = min(eintrag.datum for eintrag in eintraege)
    speicher.speichere_einstellungen(einstellungen, ziel)

    # Eine laufende Stempeluhr passt nicht zu den Demodaten
    stempeluhr = os.path.join(ziel, speicher.DATEI_STEMPELUHR)
    if os.path.exists(stempeluhr):
        os.remove(stempeluhr)

    # Feiertage wandern nicht mit, ein Eintrag kann deshalb auf einem Feiertag landen
    hinweise = []
    for eintrag in eintraege:
        name = arbzg.feiertag_name(eintrag.datum)
        if name != "":
            hinweise.append(speicher.datum_zu_text(eintrag.datum) + " liegt auf " + name + " (§ 9 ArbZG)")
    return hinweise


if __name__ == "__main__":
    for hinweis in demo_laden():
        print("Hinweis:", hinweis)
    print("Fertig. Demodaten liegen in", speicher.DATEN_ORDNER)
