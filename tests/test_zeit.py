"""Tests für logik/zeit.py."""
import unittest
from datetime import date, time

from logik import zeit
from logik.modelle import Pause


class TestZeit(unittest.TestCase):
    """Minuten rechnen, Betriebszeit, Sollzeit."""

    def test_arbeitsminuten_normaler_tag(self):
        self.assertEqual(zeit.berechne_arbeitsminuten(time(8, 0), time(16, 45), 30), 495)

    def test_arbeitsminuten_nie_negativ(self):
        self.assertEqual(zeit.berechne_arbeitsminuten(time(8, 0), time(8, 10), 30), 0)

    def test_frueher_tag_gesamt_und_betrieblich(self):
        # 5:30 bis 15:00 mit 45 min Pause: gesamt 8:45 h, betrieblich 8:15 h
        self.assertEqual(zeit.berechne_arbeitsminuten(time(5, 30), time(15, 0), 45), 8 * 60 + 45)
        self.assertEqual(zeit.berechne_betriebsminuten(time(5, 30), time(15, 0), [Pause(time(12, 0), 45)]), 8 * 60 + 15)

    def test_betriebsminuten_innerhalb_bleibt_gleich(self):
        self.assertEqual(zeit.berechne_betriebsminuten(time(8, 0), time(17, 0), [Pause(time(12, 0), 30)]), 510)

    def test_ausserhalb_betriebszeit(self):
        self.assertTrue(zeit.liegt_ausserhalb_betriebszeit(time(8, 0), time(22, 30)))
        self.assertFalse(zeit.liegt_ausserhalb_betriebszeit(time(6, 0), time(22, 0)))

    def test_sollminuten(self):
        self.assertEqual(zeit.sollminuten_je_tag(40), 480)
        self.assertEqual(zeit.sollminuten_je_tag(35), 420)
        self.assertEqual(zeit.sollminuten_je_tag(30), 360)

    def test_wochenende(self):
        self.assertTrue(zeit.ist_wochenende(date(2026, 9, 13)))
        self.assertFalse(zeit.ist_wochenende(date(2026, 9, 14)))

    def test_minuten_als_text(self):
        self.assertEqual(zeit.minuten_als_text(465), "7:45 h")
        self.assertEqual(zeit.wochentag_name(date(2026, 9, 15)), "Dienstag")


    # Nachtschichten über Mitternacht
    def test_nachtschicht_arbeitsminuten(self):
        self.assertEqual(zeit.berechne_arbeitsminuten(time(22, 0), time(6, 0), 30), 450)
        self.assertTrue(zeit.ist_nachtschicht(time(22, 0), time(6, 0)))
        self.assertFalse(zeit.ist_nachtschicht(time(8, 0), time(17, 0)))

    def test_nachtschicht_betrieblich(self):
        # 20:00 bis 07:00, Pause 02:00 bis 02:30: nur 20-22 Uhr und 6-7 Uhr zählen
        self.assertEqual(zeit.berechne_betriebsminuten(time(20, 0), time(7, 0), [Pause(time(2, 0), 30)]), 180)
        self.assertTrue(zeit.liegt_ausserhalb_betriebszeit(time(20, 0), time(7, 0)))

    # Pause außerhalb der Betriebszeit wird nicht doppelt abgezogen
    def test_pause_vor_6_uhr(self):
        self.assertEqual(zeit.berechne_betriebsminuten(time(5, 0), time(14, 0), [Pause(time(5, 5), 45)]), 480)

    def test_pause_im_betrieb(self):
        self.assertEqual(zeit.berechne_betriebsminuten(time(5, 0), time(14, 0), [Pause(time(12, 0), 45)]), 435)

    # Längstes Stück ohne Pause
    def test_laengste_zeit_ohne_pause(self):
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(8, 0), time(17, 0), [Pause(time(12, 0), 30)]), 270)
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(8, 0), time(17, 0), [Pause(time(15, 0), 30)]), 420)

    def test_mehrere_pausen_am_stueck(self):
        # 8 bis 17 Uhr, Pausen 10:00 bis 10:15 und 14:00 bis 14:15: am längsten 10:15 bis 14:00
        pausen = [Pause(time(10, 0), 15), Pause(time(14, 0), 15)]
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(8, 0), time(17, 0), pausen), 225)

    def test_mehrere_pausen_reihenfolge_egal(self):
        pausen = [Pause(time(14, 0), 15), Pause(time(10, 0), 15)]
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(8, 0), time(17, 0), pausen), 225)
        self.assertEqual(zeit.berechne_betriebsminuten(time(8, 0), time(17, 0), pausen), 510)

    def test_mehrere_pausen_ueber_mitternacht(self):
        # 22 bis 6 Uhr, Pausen 23:30 und 2:00: Stücke 1:30, 2:15 und 3:45
        pausen = [Pause(time(23, 30), 15), Pause(time(2, 0), 15)]
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(22, 0), time(6, 0), pausen), 225)
        self.assertEqual(zeit.pruefe_eingabe(time(22, 0), time(6, 0), pausen), "")

    def test_pausen_ueberschneiden_sich(self):
        pausen = [Pause(time(12, 0), 30), Pause(time(12, 15), 15)]
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(17, 0), pausen),
                         "Die Pausen dürfen sich nicht überschneiden.")

    # Eingaben prüfen
    def test_eingabe_gueltig(self):
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(17, 0), [Pause(time(12, 0), 30)]), "")
        self.assertEqual(zeit.pruefe_eingabe(time(22, 0), time(6, 0), [Pause(time(2, 0), 30)]), "")

    def test_eingabe_ungueltig(self):
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(8, 0), []), "Beginn und Ende dürfen nicht gleich sein.")
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(17, 0), [Pause(None, 600)]), "Die Pause ist länger als die Arbeitszeit.")
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(17, 0), [Pause(time(16, 45), 30)]),
                         "Die Pause muss zwischen Beginn und Ende liegen.")
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(17, 0), [Pause(None, 30)]),
                         "Bitte angeben, ab wann die Pause war.")

    # Ohne Pause
    def test_ohne_pause_nichts_abziehen(self):
        self.assertEqual(zeit.berechne_betriebsminuten(time(8, 0), time(14, 0), []), 360)
        self.assertEqual(zeit.pruefe_eingabe(time(8, 0), time(14, 0), []), "")

    def test_ohne_pause_alles_am_stueck(self):
        # 8:00 bis 16:00 ohne Pause: 8 Stunden am Stück
        self.assertEqual(zeit.laengste_zeit_ohne_pause(time(8, 0), time(16, 0), []), 480)

    def test_jetzt_ohne_zeitzone(self):
        # jetzt() gibt die Zeit ohne Zeitzone zurück, so wie die Stempeluhr sie speichert
        self.assertIsNone(zeit.jetzt().tzinfo)
        self.assertEqual(zeit.heute(), zeit.jetzt().date())


if __name__ == "__main__":
    unittest.main()
