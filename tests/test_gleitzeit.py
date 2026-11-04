"""Tests für logik/gleitzeit.py."""
import unittest
from datetime import date, time, timedelta

from logik import gleitzeit
from logik.modelle import Zeiteintrag, Abwesenheit, Einstellungen


def normaltag(datum):
    """8:00 bis 16:30 mit 30 min Pause: genau 8 Stunden, Saldo 0."""
    return Zeiteintrag(datum, time(8, 0), time(16, 30), 30, time(12, 0))


class TestGleitzeit(unittest.TestCase):
    """Saldo, vergessene Tage, Ampel, Eingabeprüfungen und Tagesliste."""

    def setUp(self):
        """40 Stunden pro Woche, Ampel orange ab 40 h und rot ab 80 h."""
        self.einstellungen = Einstellungen(wochenstunden=40, ampel_orange_stunden=40.0, ampel_rot_stunden=80.0)

    # Saldo
    def test_fuenf_tage_neun_stunden(self):
        """Mo 7.9. bis Fr 11.9.2026, je 9 h netto bei 8 h Soll -> +5:00 h."""
        eintraege = []
        for tag in range(7, 12):
            eintraege.append(Zeiteintrag(date(2026, 9, tag), time(8, 0), time(17, 30), 30, time(12, 0)))
        self.assertEqual(gleitzeit.saldo_gesamt(eintraege, [], self.einstellungen, date(2026, 9, 12)), 300)

    def test_zeit_ausserhalb_zaehlt_nicht(self):
        """5:30 bis 15:00 Uhr: die halbe Stunde vor 6 Uhr zählt nicht für die Gleitzeit."""
        eintraege = [Zeiteintrag(date(2026, 9, 7), time(5, 30), time(15, 0), 45, time(12, 0))]
        self.assertEqual(gleitzeit.saldo_gesamt(eintraege, [], self.einstellungen, date(2026, 9, 8)), 495 - 480)

    def test_soll_null_bei_abwesenheit_feiertag_wochenende(self):
        """Urlaub, Feiertag und Wochenende haben kein Soll, ein Werktag 8 h."""
        abwesenheiten = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        self.assertEqual(gleitzeit.soll_fuer_tag(date(2026, 9, 16), abwesenheiten, self.einstellungen), 0)
        self.assertEqual(gleitzeit.soll_fuer_tag(date(2026, 10, 3), [], self.einstellungen), 0)
        self.assertEqual(gleitzeit.soll_fuer_tag(date(2026, 9, 13), [], self.einstellungen), 0)
        self.assertEqual(gleitzeit.soll_fuer_tag(date(2026, 9, 21), [], self.einstellungen), 480)

    def test_saldo_zeitraum_nur_im_zeitraum(self):
        """Nur der Eintrag im September zählt für den September."""
        eintraege = [Zeiteintrag(date(2026, 9, 7), time(8, 0), time(17, 30), 30, time(12, 0)),
                     Zeiteintrag(date(2026, 10, 5), time(8, 0), time(17, 30), 30, time(12, 0))]
        saldo = gleitzeit.saldo_zeitraum(eintraege, [], date(2026, 9, 1), date(2026, 9, 30), self.einstellungen,
                                         date(2026, 9, 8))
        self.assertEqual(saldo, 60)

    def test_gleitzeit_monat_quartal_jahr(self):
        """Dieselben Einträge ergeben je Monat, Quartal und Jahr den passenden Saldo."""
        eintraege = [Zeiteintrag(date(2026, 1, 5), time(8, 0), time(17, 30), 30, time(12, 0)),    # +1:00 h, 1. Quartal
                     Zeiteintrag(date(2026, 8, 3), time(8, 0), time(18, 0), 30, time(12, 0)),     # +1:30 h, 3. Quartal
                     Zeiteintrag(date(2026, 9, 1), time(8, 0), time(16, 0), 30, time(12, 0))]     # -0:30 h, September
        e = self.einstellungen
        # "heute" direkt nach dem ersten Eintrag, damit keine vergessenen Tage mitzählen
        heute = date(2026, 1, 6)
        self.assertEqual(gleitzeit.saldo_zeitraum(eintraege, [], date(2026, 9, 1), date(2026, 9, 30), e, heute), -30)
        self.assertEqual(gleitzeit.saldo_zeitraum(eintraege, [], date(2026, 7, 1), date(2026, 9, 30), e, heute), 60)
        self.assertEqual(gleitzeit.saldo_zeitraum(eintraege, [], date(2026, 1, 1), date(2026, 12, 31), e, heute), 120)
        self.assertEqual(gleitzeit.saldo_zeitraum(eintraege, [], date(2026, 4, 1), date(2026, 6, 30), e, heute), 0)

    # Vergessene Arbeitstage
    def test_vergessener_tag_zaehlt_minus(self):
        """Mo 7.9. und Mi 9.9. erfasst, Di 8.9. vergessen."""
        eintraege = [normaltag(date(2026, 9, 7)), normaltag(date(2026, 9, 9))]
        self.assertEqual(gleitzeit.saldo_gesamt(eintraege, [], self.einstellungen, date(2026, 9, 10)), -480)
        tag = gleitzeit.tag_fuer_api(date(2026, 9, 8), eintraege, [], self.einstellungen, date(2026, 9, 10))
        self.assertTrue(tag["fehlt"])
        self.assertEqual(tag["saldo"], -480)

    def test_kein_minus_vor_erfassungsbeginn_und_heute(self):
        """Vor dem Beginn der Erfassung und am heutigen Tag gibt es kein Minus."""
        eintraege = [normaltag(date(2026, 9, 7)), normaltag(date(2026, 9, 9))]
        self.einstellungen.erfassung_ab = date(2026, 9, 9)
        self.assertEqual(gleitzeit.saldo_gesamt(eintraege, [], self.einstellungen, date(2026, 9, 10)), 0)
        # Der heutige Tag ist noch nicht vorbei und zählt nie als vergessen
        self.assertFalse(gleitzeit.ist_fehltag(date(2026, 9, 10), date(2026, 9, 10), eintraege, [], self.einstellungen))

    def test_abwesenheit_ist_kein_vergessener_tag(self):
        """Ein Krankheitstag ohne Eintrag zählt nicht als vergessen."""
        eintraege = [normaltag(date(2026, 9, 7)), normaltag(date(2026, 9, 9))]
        abwesenheiten = [Abwesenheit(date(2026, 9, 8), date(2026, 9, 8), "Krankheit")]
        self.assertEqual(gleitzeit.saldo_gesamt(eintraege, abwesenheiten, self.einstellungen, date(2026, 9, 10)), 0)

    # Arbeit an Ruhe- und Abwesenheitstagen
    def test_arbeit_an_feiertag_und_urlaub_zaehlt_als_plus(self):
        """Feiertag, Urlaub und Sonntag haben kein Soll, die 8 h zählen ganz als Plus."""
        feiertag = normaltag(date(2026, 10, 3))
        urlaub = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        self.assertEqual(gleitzeit.saldo_fuer_eintrag(feiertag, [], self.einstellungen), 480)
        self.assertEqual(gleitzeit.saldo_fuer_eintrag(normaltag(date(2026, 9, 16)), urlaub, self.einstellungen), 480)
        self.assertEqual(gleitzeit.saldo_fuer_eintrag(normaltag(date(2026, 9, 13)), [], self.einstellungen), 480)

    def test_arbeit_am_samstag_zaehlt(self):
        """Samstag hat kein Soll, 8 h Arbeit sind also 8 h Plus."""
        samstag = normaltag(date(2026, 9, 12))
        self.assertEqual(gleitzeit.saldo_fuer_eintrag(samstag, [], self.einstellungen), 480)

    # Eingaben prüfen
    def test_abwesenheit_gueltig(self):
        """Eine Krankheit nach dem Urlaub ohne Überschneidung ist in Ordnung."""
        vorhanden = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        neu = Abwesenheit(date(2026, 9, 21), date(2026, 9, 21), "Krankheit")
        self.assertEqual(gleitzeit.pruefe_abwesenheit(neu, vorhanden), "")

    def test_abwesenheit_ungueltig(self):
        """Ende vor Beginn, Überschneidung und unbekannte Art werden abgelehnt."""
        vorhanden = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        rueckwaerts = Abwesenheit(date(2026, 9, 25), date(2026, 9, 21), "Urlaub")
        ueberschneidung = Abwesenheit(date(2026, 9, 18), date(2026, 9, 22), "Krankheit")
        unbekannt = Abwesenheit(date(2026, 9, 25), date(2026, 9, 25), "Kur")
        self.assertEqual(gleitzeit.pruefe_abwesenheit(rueckwaerts, vorhanden), "Das Ende der Abwesenheit liegt vor dem Beginn.")
        self.assertIn("Überschneidet sich mit Urlaub", gleitzeit.pruefe_abwesenheit(ueberschneidung, vorhanden))
        self.assertEqual(gleitzeit.pruefe_abwesenheit(unbekannt, vorhanden), "Unbekannte Art der Abwesenheit.")

    def test_einstellungen_gueltig(self):
        """35 Stunden mit Ampel 40 und 80 sind gültig."""
        self.assertEqual(gleitzeit.pruefe_einstellungen(Einstellungen(35, 40.0, 80.0)), "")

    def test_einstellungen_ungueltig(self):
        """Falsche Wochenstunden, vertauschte und negative Ampelgrenzen werden abgelehnt."""
        self.assertIn("30, 35 oder 40", gleitzeit.pruefe_einstellungen(Einstellungen(99, 40.0, 80.0)))
        self.assertEqual(gleitzeit.pruefe_einstellungen(Einstellungen(40, 80.0, 40.0)),
                         "Die Rot-Grenze muss über der Orange-Grenze liegen.")
        self.assertEqual(gleitzeit.pruefe_einstellungen(Einstellungen(40, -5.0, 80.0)),
                         "Die Ampelgrenzen dürfen nicht negativ sein.")
        verdreht = Einstellungen(40, 40.0, 80.0, ampel_minus_orange_stunden=20.0, ampel_minus_rot_stunden=10.0)
        self.assertEqual(gleitzeit.pruefe_einstellungen(verdreht),
                         "Bei den Minusstunden muss die Rot-Grenze über der Orange-Grenze liegen.")
        zu_lang = Einstellungen(40, 40.0, 80.0, name="x" * 41)
        self.assertEqual(gleitzeit.pruefe_einstellungen(zu_lang), "Der Name darf höchstens 40 Zeichen lang sein.")

    # Ampel
    def test_ampel_gruen(self):
        """Knapp 3 Plusstunden: grün, mit Abstand bis Orange."""
        ergebnis = gleitzeit.ampel(175, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "gruen")
        self.assertEqual(ergebnis["text"], "Grün")
        self.assertEqual(ergebnis["rest"], "noch 37,1 h bis Orange (+40 h)")
        self.assertAlmostEqual(ergebnis["prozent"], 7.3, places=1)

    def test_ampel_orange_an_der_grenze(self):
        """Genau 40 Plusstunden: schon orange."""
        ergebnis = gleitzeit.ampel(40 * 60, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "orange")
        self.assertEqual(ergebnis["rest"], "noch 40,0 h bis Rot (+80 h)")
        self.assertEqual(ergebnis["prozent"], 0.0)

    def test_ampel_rot_an_der_grenze(self):
        """Genau 80 Plusstunden: rot."""
        ergebnis = gleitzeit.ampel(80 * 60, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "rot")
        self.assertEqual(ergebnis["rest"], "Grenze von +80 h überschritten")
        self.assertEqual(ergebnis["prozent"], 100.0)

    # Ampel bei Minusstunden (Standard: orange ab -10 h, rot ab -20 h)
    def test_ampel_minus_gruen(self):
        """9 Minusstunden: noch grün."""
        ergebnis = gleitzeit.ampel(-9 * 60, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "gruen")
        self.assertEqual(ergebnis["rest"], "noch 1,0 h bis Orange (−10 h)")

    def test_ampel_minus_orange_an_der_grenze(self):
        """Genau 10 Minusstunden: orange."""
        ergebnis = gleitzeit.ampel(-10 * 60, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "orange")
        self.assertEqual(ergebnis["rest"], "noch 10,0 h bis Rot (−20 h)")

    def test_ampel_minus_rot_an_der_grenze(self):
        """Genau 20 Minusstunden: rot."""
        ergebnis = gleitzeit.ampel(-20 * 60, self.einstellungen)
        self.assertEqual(ergebnis["farbe"], "rot")
        self.assertEqual(ergebnis["rest"], "Grenze von −20 h unterschritten")
        self.assertEqual(ergebnis["prozent"], 100.0)

    # Tagesliste und Bewertung
    def test_tage_fuer_zeitraum_monat(self):
        """September mit einem Eintrag und Urlaub: 30 Tage mit allem für die Oberfläche."""
        eintraege = [Zeiteintrag(date(2026, 9, 1), time(8, 0), time(17, 0), 30, time(12, 0))]
        abwesenheiten = [Abwesenheit(date(2026, 9, 14), date(2026, 9, 18), "Urlaub")]
        tage = gleitzeit.tage_fuer_zeitraum(date(2026, 9, 1), date(2026, 9, 30), eintraege, abwesenheiten,
                                            self.einstellungen, date(2026, 9, 2))
        self.assertEqual(len(tage), 30)
        erster = tage[0]
        self.assertEqual(erster["eintrag"], {"beginn": "08:00", "ende": "17:00", "pause": 30,
                                             "pausen": [{"ab": "12:00", "minuten": 30}]})
        self.assertEqual(erster["ist"], 510)
        self.assertEqual(erster["saldo"], 30)
        self.assertEqual(erster["status"], "orange")
        urlaub = tage[13]
        self.assertEqual(urlaub["abwesenheit"]["art"], "Urlaub")
        self.assertEqual(urlaub["soll"], 0)
        self.assertEqual(urlaub["status"], "")
        self.assertIsNone(urlaub["eintrag"])

    def test_tage_fuer_zeitraum_quartal_und_jahr(self):
        """3. Quartal: 1.7. bis 30.9. sind 92 Tage, das ganze Jahr 2026 hat 365 Tage."""
        heute = date(2026, 9, 28)
        quartal = gleitzeit.tage_fuer_zeitraum(date(2026, 7, 1), date(2026, 9, 30), [], [], self.einstellungen, heute)
        self.assertEqual(len(quartal), 92)
        self.assertEqual(quartal[0]["datum"], "2026-07-01")
        self.assertEqual(quartal[91]["datum"], "2026-09-30")
        jahr = gleitzeit.tage_fuer_zeitraum(date(2026, 1, 1), date(2026, 12, 31), [], [], self.einstellungen, heute)
        self.assertEqual(len(jahr), 365)

    def test_letzter_tag_im_monat(self):
        """Februar mit und ohne Schaltjahr und Dezember."""
        self.assertEqual(gleitzeit.letzter_tag_im_monat(2026, 2), date(2026, 2, 28))
        self.assertEqual(gleitzeit.letzter_tag_im_monat(2028, 2), date(2028, 2, 29))
        self.assertEqual(gleitzeit.letzter_tag_im_monat(2026, 12), date(2026, 12, 31))

    def test_bewerte_eintrag(self):
        """7 h ohne Pause: Ist, Saldo und Status rot wegen § 4."""
        eintrag = Zeiteintrag(date(2026, 9, 15), time(8, 0), time(15, 0), 0)
        ergebnis = gleitzeit.bewerte_eintrag(eintrag, [], [], self.einstellungen, date(2026, 9, 16))
        self.assertEqual(ergebnis["ist"], 420)
        self.assertEqual(ergebnis["saldo"], -60)
        self.assertEqual(ergebnis["status"], "rot")

    def test_bewerte_eintrag_vortag_vergessen(self):
        """Fehlt der Vortag, warnt die Bewertung, dass die Ruhezeit nicht prüfbar ist."""
        eintraege = [normaltag(date(2026, 9, 7)), normaltag(date(2026, 9, 9))]
        ergebnis = gleitzeit.bewerte_eintrag(eintraege[1], eintraege, [], self.einstellungen, date(2026, 9, 10))
        self.assertEqual(ergebnis["meldungen"][0]["text"], "Ruhezeit nicht prüfbar: Für den Vortag fehlt ein Eintrag.")

    def test_bewerte_eintrag_mit_p11(self):
        """Die Tagesbewertung enthält auch § 11: Sonntag ohne Ersatzruhetag in zwei Wochen."""
        eintraege = []
        for nummer in range(31):
            datum = date(2026, 8, 31) + timedelta(days=nummer)
            if datum.weekday() < 6 or datum == date(2026, 9, 13):
                eintraege.append(normaltag(datum))
        sonntag = finde(eintraege, date(2026, 9, 13))
        ergebnis = gleitzeit.bewerte_eintrag(sonntag, eintraege, [], self.einstellungen, date(2026, 10, 5))
        paragraphen = []
        for meldung in ergebnis["meldungen"]:
            paragraphen.append(meldung["paragraph"])
        self.assertIn("§ 11 ArbZG", paragraphen)


def finde(eintraege, datum):
    """Hilfe: den Eintrag an einem Datum aus der Liste holen."""
    for eintrag in eintraege:
        if eintrag.datum == datum:
            return eintrag
    return None


if __name__ == "__main__":
    unittest.main()
