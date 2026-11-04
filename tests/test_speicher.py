"""Tests für logik/speicher.py."""
import shutil
import tempfile
import unittest
from datetime import date, time

from logik import speicher
from logik.modelle import Zeiteintrag, Abwesenheit, Einstellungen, Pause, eintrag_mit_pausen, pausen_von


class TestSpeicher(unittest.TestCase):
    """Speichern, Laden und Passwort."""

    def setUp(self):
        """Jeder Test bekommt einen eigenen leeren Ordner."""
        self.ordner = tempfile.mkdtemp()

    def tearDown(self):
        """Räumt den Ordner wieder weg."""
        shutil.rmtree(self.ordner)

    def test_eintraege_speichern_und_laden(self):
        """Einträge kommen genauso zurück, nach Datum sortiert."""
        eintraege = [
            Zeiteintrag(date(2026, 10, 2), time(9, 0), time(17, 30), 30, time(12, 0)),
            Zeiteintrag(date(2026, 10, 1), time(8, 30), time(17, 0), 45, time(12, 0)),
        ]
        speicher.speichere_eintraege(eintraege, self.ordner)
        geladen = speicher.lade_eintraege(self.ordner)
        # Beim Laden wird nach Datum sortiert
        self.assertEqual(geladen[0], eintraege[1])
        self.assertEqual(geladen[1], eintraege[0])

    def test_abwesenheiten_speichern_und_laden(self):
        """Eine Abwesenheit mit Grund kommt genauso zurück."""
        abwesenheiten = [Abwesenheit(date(2026, 10, 5), date(2026, 10, 9), "Sonstige Abwesenheit", "Fortbildung")]
        speicher.speichere_abwesenheiten(abwesenheiten, self.ordner)
        self.assertEqual(speicher.lade_abwesenheiten(self.ordner), abwesenheiten)

    def test_einstellungen_speichern_und_laden(self):
        """Alle Einstellungen kommen genauso zurück."""
        einstellungen = Einstellungen(35, 30.0, 60.0, "abc", "123", date(2026, 9, 1), 5.0, 15.0, "Jason Reich")
        speicher.speichere_einstellungen(einstellungen, self.ordner)
        self.assertEqual(speicher.lade_einstellungen(self.ordner), einstellungen)

    def test_stempeluhr_speichern_und_laden(self):
        """Eine laufende Pause in der Stempeluhr bleibt erhalten."""
        zustand = {"status": "pause", "beginn": "2026-09-15T08:00:00",
                   "pausen": [{"von": "2026-09-15T12:00:00", "bis": None}]}
        speicher.speichere_stempeluhr(zustand, self.ordner)
        self.assertEqual(speicher.lade_stempeluhr(self.ordner), zustand)

    def test_fehlende_dateien_geben_standard(self):
        """Ohne Dateien gibt es leere Listen und Standardwerte."""
        self.assertEqual(speicher.lade_eintraege(self.ordner), [])
        self.assertEqual(speicher.lade_abwesenheiten(self.ordner), [])
        self.assertEqual(speicher.lade_einstellungen(self.ordner), Einstellungen())
        self.assertEqual(speicher.lade_stempeluhr(self.ordner)["status"], "aus")

    def test_pausenbeginn_speichern_und_laden(self):
        """Der Pausenbeginn einer Nachtschicht bleibt erhalten."""
        eintraege = [Zeiteintrag(date(2026, 10, 1), time(22, 0), time(6, 0), 30, time(2, 0))]
        speicher.speichere_eintraege(eintraege, self.ordner)
        self.assertEqual(speicher.lade_eintraege(self.ordner), eintraege)

    def test_eintrag_ohne_pause(self):
        """Ein Eintrag ohne Pause hat auch keinen Pausenbeginn."""
        eintraege = [Zeiteintrag(date(2026, 10, 1), time(8, 0), time(14, 0), 0, None)]
        speicher.speichere_eintraege(eintraege, self.ordner)
        geladen = speicher.lade_eintraege(self.ordner)
        self.assertEqual(geladen, eintraege)
        self.assertIsNone(geladen[0].pause_beginn)

    def test_mehrere_pausen_speichern_und_laden(self):
        """Zwei Pausen werden einzeln gespeichert und geladen."""
        eintraege = [eintrag_mit_pausen(date(2026, 10, 1), time(8, 0), time(17, 0),
                                        [Pause(time(10, 0), 15), Pause(time(14, 0), 15)])]
        speicher.speichere_eintraege(eintraege, self.ordner)
        self.assertEqual(speicher.lade_eintraege(self.ordner), eintraege)

    def test_altes_format_ohne_pausenliste(self):
        """So liegen Einträge gespeichert, die vor der Pausenliste entstanden sind."""
        daten = {"datum": "2026-10-01", "beginn": "08:00", "ende": "17:00",
                 "pause_minuten": 30, "pause_beginn": "12:00"}
        eintrag = speicher.dict_zu_eintrag(daten)
        self.assertEqual(eintrag, Zeiteintrag(date(2026, 10, 1), time(8, 0), time(17, 0), 30, time(12, 0)))
        self.assertEqual(pausen_von(eintrag), [Pause(time(12, 0), 30)])

    def test_passwort_richtig(self):
        """Das richtige Passwort passt zum Hash."""
        hash_wert, salt = speicher.passwort_hash_erzeugen("geheim")
        self.assertTrue(speicher.passwort_pruefen("geheim", hash_wert, salt))

    def test_passwort_falsch(self):
        """Ein falsches Passwort passt nicht."""
        hash_wert, salt = speicher.passwort_hash_erzeugen("geheim")
        self.assertFalse(speicher.passwort_pruefen("falsch", hash_wert, salt))

    def test_finde_abwesenheit_im_zeitraum(self):
        """Ein Tag im Urlaub wird gefunden, der Tag danach nicht."""
        abwesenheiten = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        self.assertIsNotNone(speicher.finde_abwesenheit(abwesenheiten, date(2026, 9, 16)))
        self.assertIsNone(speicher.finde_abwesenheit(abwesenheiten, date(2026, 9, 19)))

    def test_setze_und_entferne_eintrag(self):
        """Ein Eintrag am selben Tag wird ersetzt und kann wieder entfernt werden."""
        eintraege = [Zeiteintrag(date(2026, 10, 1), time(8, 0), time(16, 0), 30, time(12, 0))]
        speicher.setze_eintrag(eintraege, Zeiteintrag(date(2026, 10, 1), time(9, 0), time(17, 0), 30, time(12, 0)))
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0].beginn, time(9, 0))
        speicher.entferne_eintrag(eintraege, date(2026, 10, 1))
        self.assertEqual(eintraege, [])


if __name__ == "__main__":
    unittest.main()
