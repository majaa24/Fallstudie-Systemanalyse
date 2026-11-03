"""Tests für logik/arbzg.py."""
import unittest
from datetime import date, time, timedelta

from logik import arbzg
from logik.modelle import Zeiteintrag, Abwesenheit, Pause, eintrag_mit_pausen


def tag(datum, beginn, ende, pause, pause_beginn=None):
    """Kurze Hilfe zum Bauen eines Zeiteintrags."""
    return Zeiteintrag(datum, beginn, ende, pause, pause_beginn)


class TestArbZG(unittest.TestCase):
    """Je Paragraph ein Fall, der erfüllt, und einer, der verletzt."""

    # § 3 Höchstarbeitszeit
    def test_p3_erfuellt(self):
        self.assertEqual(arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(8, 0), time(16, 30), 30)), [])

    def test_p3_warnung_ueber_8h(self):
        meldungen = arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(8, 0), time(17, 30), 30))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    def test_p3_verletzung_ueber_10h(self):
        meldungen = arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(7, 0), time(18, 30), 45))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertEqual(meldungen[0]["text"], "Arbeitszeit 10:45 h überschreitet die Höchstgrenze von 10 Stunden.")

    # § 4 Pause
    def test_p4_erfuellt(self):
        self.assertEqual(arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(16, 30), 30)), [])

    def test_p4_verletzung_keine_pause(self):
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(15, 0), 0))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertIn("0 min statt 30 min", meldungen[0]["text"])

    def test_p4_verletzung_45_min_noetig(self):
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(7, 0), time(17, 0), 30))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_p4_warnung_ab_5_5h(self):
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(13, 45), 0))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    # § 5 Ruhezeit
    def test_p5_erfuellt(self):
        vortag = tag(date(2026, 9, 14), time(8, 0), time(19, 0), 30)
        heute = tag(date(2026, 9, 15), time(6, 0), time(14, 0), 30)
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, vortag), [])

    def test_p5_verletzung(self):
        vortag = tag(date(2026, 9, 14), time(8, 0), time(21, 30), 45)
        heute = tag(date(2026, 9, 15), time(6, 30), time(14, 0), 30)
        meldungen = arbzg.pruefe_ruhezeit(heute, vortag)
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertIn("9:00 h", meldungen[0]["text"])

    # § 9 Sonntag und Feiertag
    def test_p9_erfuellt(self):
        self.assertEqual(arbzg.pruefe_sonntag_feiertag(tag(date(2026, 9, 14), time(8, 0), time(16, 0), 30)), [])

    def test_p9_sonntag(self):
        meldungen = arbzg.pruefe_sonntag_feiertag(tag(date(2026, 9, 13), time(9, 0), time(13, 0), 0))
        self.assertEqual(meldungen[0]["paragraph"], "§ 9 ArbZG")

    def test_p9_feiertag(self):
        meldungen = arbzg.pruefe_sonntag_feiertag(tag(date(2026, 10, 3), time(9, 0), time(13, 0), 0))
        self.assertIn("Tag der Deutschen Einheit", meldungen[0]["text"])

    def test_feiertage_bw(self):
        feiertage = arbzg.feiertage_bw(2026)
        self.assertEqual(feiertage[date(2026, 4, 3)], "Karfreitag")
        self.assertEqual(feiertage[date(2026, 6, 4)], "Fronleichnam")
        self.assertEqual(arbzg.feiertag_name(date(2026, 9, 14)), "")

    # Betriebszeit
    def test_betriebszeit_erfuellt(self):
        self.assertEqual(arbzg.pruefe_betriebszeit(tag(date(2026, 9, 14), time(6, 0), time(22, 0), 45)), [])

    def test_betriebszeit_warnung(self):
        meldungen = arbzg.pruefe_betriebszeit(tag(date(2026, 9, 14), time(5, 30), time(15, 0), 45))
        self.assertEqual(meldungen[0]["paragraph"], "Betrieb")

    # Alles zusammen
    def test_pruefe_tag_sammelt_alles(self):
        vortag = tag(date(2026, 9, 12), time(8, 0), time(22, 0), 30, time(12, 0))
        heute = tag(date(2026, 9, 13), time(6, 0), time(17, 0), 0)
        paragraphen = []
        for meldung in arbzg.pruefe_tag(heute, vortag):
            paragraphen.append(meldung["paragraph"])
        self.assertEqual(paragraphen, ["§ 3 ArbZG", "§ 4 ArbZG", "§ 9 ArbZG", "§ 5 ArbZG"])

    def test_status(self):
        self.assertEqual(arbzg.status_aus_meldungen([]), "gruen")
        self.assertEqual(arbzg.status_aus_meldungen([{"art": "Warnung"}]), "orange")
        self.assertEqual(arbzg.status_aus_meldungen([{"art": "Warnung"}, {"art": "Verletzung"}]), "rot")

    # Nur grobe Verletzungen für das Warn-Popup
    def test_nur_verletzungen_ohne_verletzung(self):
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(8, 0), time(17, 30), 30, time(12, 0)), None)
        self.assertEqual(meldungen[0]["art"], "Warnung")
        self.assertEqual(arbzg.nur_verletzungen(meldungen), [])

    def test_nur_verletzungen_mit_verletzung(self):
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(7, 0), time(18, 30), 30, time(12, 0)), None)
        verletzungen = arbzg.nur_verletzungen(meldungen)
        self.assertEqual(len(verletzungen), 2)
        self.assertEqual(verletzungen[0]["paragraph"], "§ 3 ArbZG")
        self.assertEqual(verletzungen[1]["paragraph"], "§ 4 ArbZG")

    # 6-Monats-Durchschnitt je Werktag (Montag bis Samstag)
    def arbeitstage(self, von, bis, beginn, ende, mit_samstag):
        """Hilfe: Eintraege fuer jeden Arbeitstag von "von" bis "bis"."""
        eintraege = []
        datum = von
        while datum <= bis:
            if datum.weekday() < 5 or (mit_samstag and datum.weekday() == 5):
                if arbzg.feiertag_name(datum) == "":
                    eintraege.append(tag(datum, beginn, ende, 45))
            datum = datum + timedelta(days=1)
        return eintraege

    def test_durchschnitt_erfuellt(self):
        # 6 Monate lang Montag bis Freitag je 9 h: 45 h pro Woche, im Schnitt 7:30 h je Werktag
        eintraege = self.arbeitstage(date(2026, 3, 1), date(2026, 9, 28), time(8, 0), time(17, 45), False)
        self.assertEqual(arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 3, 1), date(2026, 9, 28)), [])

    def test_durchschnitt_verletzt(self):
        # 6 Monate lang Montag bis Samstag je 9 h: im Schnitt mehr als 8 h je Werktag
        eintraege = self.arbeitstage(date(2026, 3, 1), date(2026, 9, 28), time(8, 0), time(17, 45), True)
        meldungen = arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 3, 1), date(2026, 9, 28))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_durchschnitt_kurz_erfasst_nur_warnung(self):
        # Erst eine Woche erfasst: Ausgleich noch möglich, deshalb nur eine Warnung
        eintraege = self.arbeitstage(date(2026, 9, 14), date(2026, 9, 19), time(7, 0), time(17, 45), True)
        meldungen = arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 9, 14), date(2026, 9, 19))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    def test_werktage_ohne_sonntag_feiertag_urlaub(self):
        # 28.09. bis 04.10.2026: Mo-Sa sind 6 Tage, der 03.10. ist Feiertag, der 29.09. Urlaub
        urlaub = [Abwesenheit(date(2026, 9, 29), date(2026, 9, 29), "Urlaub")]
        self.assertEqual(arbzg.werktage_im_zeitraum(date(2026, 9, 28), date(2026, 10, 4), urlaub), 4)

    # Osterformel und Feiertage nach 2030
    def test_ostersonntag(self):
        self.assertEqual(arbzg.ostersonntag(2026), date(2026, 4, 5))
        self.assertEqual(arbzg.ostersonntag(2031), date(2031, 4, 13))
        self.assertEqual(arbzg.ostersonntag(2038), date(2038, 4, 25))

    def test_feiertage_nach_2030(self):
        feiertage = arbzg.feiertage_bw(2031)
        self.assertEqual(len(feiertage), 12)
        self.assertEqual(feiertage[date(2031, 4, 11)], "Karfreitag")

    # § 4 Satz 3: höchstens 6 Stunden am Stück
    def test_p4_am_stueck_erfuellt(self):
        eintrag = Zeiteintrag(date(2026, 9, 14), time(8, 0), time(17, 0), 30, time(12, 0))
        self.assertEqual(arbzg.pruefe_pause_am_stueck(eintrag), [])

    def test_p4_am_stueck_verletzt(self):
        eintrag = Zeiteintrag(date(2026, 9, 14), time(8, 0), time(17, 0), 30, time(15, 0))
        meldungen = arbzg.pruefe_pause_am_stueck(eintrag)
        self.assertEqual(meldungen[0]["text"], "7:00 h am Stück ohne Pause, erlaubt sind 6 Stunden.")

    def test_p4_am_stueck_mit_zwei_pausen_erfuellt(self):
        # Früher als ein Block ab 10:00 gerechnet: 10:30 bis 17:00 wären 6:30 h am Stück gewesen
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(8, 0), time(17, 0),
                                     [Pause(time(10, 0), 15), Pause(time(14, 0), 15)])
        self.assertEqual(arbzg.pruefe_pause_am_stueck(eintrag), [])

    def test_pausen_werden_nach_lage_sortiert(self):
        # Nachtschicht: 2:00 liegt nach 23:30, erste Pause ist also 23:30
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(22, 0), time(6, 0),
                                     [Pause(time(2, 0), 15), Pause(time(23, 30), 15)])
        self.assertEqual(eintrag.pause_beginn, time(23, 30))

    def test_p4_am_stueck_mit_zwei_pausen_verletzt(self):
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(7, 0), time(17, 0),
                                     [Pause(time(8, 0), 15), Pause(time(9, 0), 30)])
        meldungen = arbzg.pruefe_pause_am_stueck(eintrag)
        self.assertEqual(meldungen[0]["text"], "7:30 h am Stück ohne Pause, erlaubt sind 6 Stunden.")

    def test_p4_ohne_pause_nur_eine_meldung(self):
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(8, 0), time(15, 0), 0), None)
        self.assertEqual(len(meldungen), 1)
        self.assertEqual(meldungen[0]["text"], "Pause zu kurz: 0 min statt 30 min.")

    # Nachtschichten
    def test_nachtschicht_in_den_sonntag(self):
        samstag_nacht = tag(date(2026, 9, 12), time(22, 0), time(6, 0), 30)
        meldungen = arbzg.pruefe_sonntag_feiertag(samstag_nacht)
        self.assertEqual(meldungen[0]["text"], "Arbeit an einem Sonntag (nach Mitternacht) ist nicht zulässig.")

    def test_nachtschicht_an_werktagen_erfuellt(self):
        montag_nacht = tag(date(2026, 9, 14), time(22, 0), time(6, 0), 30)
        self.assertEqual(arbzg.pruefe_sonntag_feiertag(montag_nacht), [])

    def test_ruhezeit_nach_nachtschicht(self):
        vortag = tag(date(2026, 9, 14), time(22, 0), time(6, 0), 30)
        heute = tag(date(2026, 9, 15), time(14, 0), time(20, 0), 0)
        self.assertIn("8:00 h", arbzg.pruefe_ruhezeit(heute, vortag)[0]["text"])

    def test_ruhezeit_vortag_fehlt(self):
        heute = tag(date(2026, 9, 15), time(8, 0), time(16, 0), 30)
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, None, True)[0]["art"], "Warnung")
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, None, False), [])


if __name__ == "__main__":
    unittest.main()
