"""Tests für logik/stempeluhr.py."""
import unittest
from datetime import datetime, time, date

from logik import stempeluhr
from logik.modelle import Pause


class TestStempeluhr(unittest.TestCase):
    """Einstempeln, Pause, Ausstempeln."""

    def test_ganzer_tag(self):
        # 8:00 einstempeln, Pause 12:00 bis 12:30, 17:00 ausstempeln
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 12, 0))
        stempeluhr.pause_beenden(zustand, datetime(2026, 9, 15, 12, 30))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 17, 0))

        self.assertEqual(eintrag.datum, date(2026, 9, 15))
        self.assertEqual(eintrag.beginn, time(8, 0))
        self.assertEqual(eintrag.ende, time(17, 0))
        self.assertEqual(eintrag.pause_minuten, 30)
        self.assertEqual(hinweis, "Ausgestempelt. Eintrag für 15.09.2026 gespeichert: 08:00 bis 17:00, 30 min Pause.")
        self.assertEqual(zustand, stempeluhr.neuer_zustand())

    def test_zustand_als_text(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 12, 0))
        self.assertEqual(zustand["status"], "pause")
        self.assertEqual(zustand["beginn"], "2026-09-15T08:00:00")
        self.assertEqual(zustand["pausen"], [{"von": "2026-09-15T12:00:00", "bis": None}])

    def test_ausstempeln_in_pause_beendet_pause(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 12, 0))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 12, 20))
        self.assertEqual(eintrag.pause_minuten, 20)

    def test_kurze_pause_zaehlt_nicht(self):
        # 20 Sekunden Pause werden 0 min, dann gibt es keinen Pausenbeginn
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 12, 0, 0))
        stempeluhr.pause_beenden(zustand, datetime(2026, 9, 15, 12, 0, 20))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 17, 0))
        self.assertEqual(eintrag.pause_minuten, 0)
        self.assertIsNone(eintrag.pause_beginn)

    def test_mehrere_pausen_bleiben_einzeln(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 10, 0))
        stempeluhr.pause_beenden(zustand, datetime(2026, 9, 15, 10, 15))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 14, 0))
        stempeluhr.pause_beenden(zustand, datetime(2026, 9, 15, 14, 15))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 17, 0))
        self.assertEqual(eintrag.pause_minuten, 30)
        self.assertEqual(eintrag.pause_beginn, time(10, 0))
        self.assertEqual(eintrag.pausen, [Pause(time(10, 0), 15), Pause(time(14, 0), 15)])

    def test_falsche_reihenfolge_aendert_nichts(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 15, 8, 0))
        self.assertEqual(zustand["status"], "aus")
        self.assertEqual(stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 9, 0)), (None, ""))

    def test_ende_nie_vor_beginn(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 15, 8, 0))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 15, 8, 0, 20))
        self.assertEqual(eintrag.ende, time(8, 1))


    def test_ueber_mitternacht(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 21, 23, 0))
        stempeluhr.pause_starten(zustand, datetime(2026, 9, 22, 1, 0))
        stempeluhr.pause_beenden(zustand, datetime(2026, 9, 22, 1, 30))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 22, 7, 0))
        self.assertEqual(eintrag.datum, date(2026, 9, 21))
        self.assertEqual(eintrag.ende, time(7, 0))
        self.assertEqual(eintrag.pause_beginn, time(1, 0))
        self.assertEqual(eintrag.pause_minuten, 30)

    def test_laenger_als_24_stunden(self):
        zustand = stempeluhr.neuer_zustand()
        stempeluhr.einstempeln(zustand, datetime(2026, 9, 20, 8, 0))
        eintrag, hinweis = stempeluhr.ausstempeln(zustand, datetime(2026, 9, 21, 9, 0))
        self.assertIsNone(eintrag)
        self.assertIn("länger als 24 Stunden", hinweis)
        self.assertEqual(zustand, stempeluhr.neuer_zustand())


if __name__ == "__main__":
    unittest.main()
