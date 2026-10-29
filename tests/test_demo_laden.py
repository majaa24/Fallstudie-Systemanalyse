"""Tests für demo_laden.py."""
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta

import demo_laden
from logik import gleitzeit, speicher


class TestDemoLaden(unittest.TestCase):
    """Demodaten werden um ganze Wochen verschoben und reichen bis gestern."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.ordner)

    def test_wochen_verschiebung(self):
        # Letzter Demotag Fr 25.9.2026, heute Do 29.10.2026 -> 5 Wochen, letzter Tag Fr 30.10.
        self.assertEqual(demo_laden.wochen_verschiebung(date(2026, 9, 25), date(2026, 10, 29)), timedelta(weeks=5))
        # Liegt der letzte Tag schon auf gestern, bleibt alles, wie es ist
        self.assertEqual(demo_laden.wochen_verschiebung(date(2026, 9, 25), date(2026, 9, 26)), timedelta(0))

    def test_wochentage_bleiben_und_nichts_ab_heute(self):
        heute = date(2026, 10, 29)
        original = speicher.lade_eintraege(demo_laden.QUELLE)
        demo_laden.demo_laden(heute, self.ordner)
        eintraege = speicher.lade_eintraege(self.ordner)
        self.assertEqual(eintraege[0].datum.weekday(), original[0].datum.weekday())
        self.assertLess(max(eintrag.datum for eintrag in eintraege), heute)
        self.assertEqual(eintraege[-1].datum, date(2026, 10, 28))

    def test_abwesenheiten_wandern_mit(self):
        demo_laden.demo_laden(date(2026, 10, 29), self.ordner)
        abwesenheiten = speicher.lade_abwesenheiten(self.ordner)
        # Urlaub 14.-18.9. liegt 5 Wochen später auf 19.-23.10.
        self.assertIsNotNone(speicher.finde_abwesenheit(abwesenheiten, date(2026, 10, 21)))

    def test_nur_der_absichtlich_vergessene_tag(self):
        # In den Demodaten fehlt mit Absicht genau ein Arbeitstag (Fr 11.9.), egal an welchem Tag man lädt
        for tage in range(14):
            heute = date(2026, 10, 29) + timedelta(days=tage)
            demo_laden.demo_laden(heute, self.ordner)
            eintraege = speicher.lade_eintraege(self.ordner)
            abwesenheiten = speicher.lade_abwesenheiten(self.ordner)
            einstellungen = speicher.lade_einstellungen(self.ordner)
            self.assertEqual(einstellungen.erfassung_ab, eintraege[0].datum)
            fehlend = gleitzeit.summe_fehltage(eintraege, abwesenheiten, date(1900, 1, 1), date(2999, 12, 31),
                                               einstellungen, heute)
            self.assertEqual(fehlend, -480, heute)

    def test_passwort_bleibt_stempeluhr_weg(self):
        einstellungen = speicher.lade_einstellungen(self.ordner)
        einstellungen.passwort_hash = "abc"
        speicher.speichere_einstellungen(einstellungen, self.ordner)
        speicher.speichere_stempeluhr({"laeuft": True}, self.ordner)
        demo_laden.demo_laden(date(2026, 10, 29), self.ordner)
        self.assertEqual(speicher.lade_einstellungen(self.ordner).passwort_hash, "abc")
        self.assertFalse(os.path.exists(os.path.join(self.ordner, speicher.DATEI_STEMPELUHR)))

    def test_hinweis_bei_feiertag(self):
        # Heute Sa 2.1.2027: der letzte Demotag (ein Freitag) landet auf Neujahr
        hinweise = demo_laden.demo_laden(date(2027, 1, 2), self.ordner)
        self.assertEqual(len(hinweise), 1)
        self.assertIn("Neujahr", hinweise[0])
