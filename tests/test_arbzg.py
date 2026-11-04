"""Tests für logik/arbzg.py."""
import unittest
from datetime import date, datetime, time, timedelta

from logik import arbzg
from logik.modelle import Zeiteintrag, Abwesenheit, Pause, eintrag_mit_pausen


def tag(datum, beginn, ende, pause, pause_beginn=None):
    """Kurze Hilfe zum Bauen eines Zeiteintrags."""
    return Zeiteintrag(datum, beginn, ende, pause, pause_beginn)


class TestArbZG(unittest.TestCase):
    """Je Paragraph ein Fall, der erfüllt, und einer, der verletzt."""

    # § 3 Höchstarbeitszeit
    def test_p3_erfuellt(self):
        """8:00 bis 16:30 mit 30 min Pause: genau 8 h, keine Meldung."""
        self.assertEqual(arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(8, 0), time(16, 30), 30)), [])

    def test_p3_warnung_ueber_8h(self):
        """9 h Arbeit: über 8 h ist eine Warnung."""
        meldungen = arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(8, 0), time(17, 30), 30))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    def test_p3_verletzung_ueber_10h(self):
        """10:45 h Arbeit: über 10 h ist eine Verletzung."""
        meldungen = arbzg.pruefe_hoechstarbeitszeit(tag(date(2026, 9, 14), time(7, 0), time(18, 30), 45))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertEqual(meldungen[0]["text"], "Arbeitszeit 10:45 h überschreitet die Höchstgrenze von 10 Stunden.")

    # § 4 Pause
    def test_p4_erfuellt(self):
        """8 h Arbeit mit 30 min Pause: genug Pause."""
        self.assertEqual(arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(16, 30), 30)), [])

    def test_p4_verletzung_keine_pause(self):
        """7 h ohne Pause: 30 min hätten es sein müssen."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(15, 0), 0))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertIn("0 min statt 30 min", meldungen[0]["text"])

    def test_p4_verletzung_45_min_noetig(self):
        """Über 9 h Arbeit reichen 30 min Pause nicht, nötig sind 45 min."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(7, 0), time(17, 0), 30))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_p4_pause_unter_15_min_zaehlt_nicht(self):
        """Nur 10 min Pause: das ist keine Ruhepause, gezählt werden 0 min."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(15, 0), 10, time(12, 0)))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertEqual(meldungen[0]["text"], "Pause zu kurz: 0 min statt 30 min. Pausen unter 15 min zählen nicht.")

    def test_p4_kurze_pause_ist_arbeitszeit(self):
        """10 min Pause werden nicht abgezogen: 6:05 h Arbeit, also sind 30 min Pause nötig."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(14, 5), 10, time(12, 0)))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_p4_pause_genau_15_min_zaehlt(self):
        """Genau 15 min zählen schon als Pause."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(14, 15), 15, time(12, 0)))
        self.assertEqual(meldungen[0]["text"], "Bald sind 30 min Pause nötig, bisher nur 15 min.")

    def test_p4_warnung_ab_5_5h(self):
        """5:45 h ohne Pause: bald sind 30 min nötig, deshalb eine Warnung."""
        meldungen = arbzg.pruefe_pause(tag(date(2026, 9, 14), time(8, 0), time(13, 45), 0))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    # § 5 Ruhezeit
    def test_p5_erfuellt(self):
        """Ende 19 Uhr, Beginn am nächsten Tag um 6 Uhr: genau 11 h Ruhe."""
        vortag = tag(date(2026, 9, 14), time(8, 0), time(19, 0), 30)
        heute = tag(date(2026, 9, 15), time(6, 0), time(14, 0), 30)
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, vortag), [])

    def test_p5_verletzung(self):
        """Ende 21:30 Uhr, Beginn um 6:30 Uhr: nur 9 h Ruhe."""
        vortag = tag(date(2026, 9, 14), time(8, 0), time(21, 30), 45)
        heute = tag(date(2026, 9, 15), time(6, 30), time(14, 0), 30)
        meldungen = arbzg.pruefe_ruhezeit(heute, vortag)
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertIn("9:00 h", meldungen[0]["text"])

    # § 9 Sonntag und Feiertag
    def test_p9_erfuellt(self):
        """Arbeit an einem Montag: keine Meldung."""
        self.assertEqual(arbzg.pruefe_sonntag_feiertag(tag(date(2026, 9, 14), time(8, 0), time(16, 0), 30)), [])

    def test_p9_sonntag(self):
        """Arbeit an einem Sonntag ist eine Verletzung nach § 9."""
        meldungen = arbzg.pruefe_sonntag_feiertag(tag(date(2026, 9, 13), time(9, 0), time(13, 0), 0))
        self.assertEqual(meldungen[0]["paragraph"], "§ 9 ArbZG")

    def test_p9_feiertag(self):
        """Arbeit am 3. Oktober: die Meldung nennt den Feiertag."""
        meldungen = arbzg.pruefe_sonntag_feiertag(tag(date(2026, 10, 3), time(9, 0), time(13, 0), 0))
        self.assertIn("Tag der Deutschen Einheit", meldungen[0]["text"])

    def test_feiertage_bw(self):
        """Bewegliche Feiertage 2026 und ein normaler Tag ohne Feiertag."""
        feiertage = arbzg.feiertage_bw(2026)
        self.assertEqual(feiertage[date(2026, 4, 3)], "Karfreitag")
        self.assertEqual(feiertage[date(2026, 6, 4)], "Fronleichnam")
        self.assertEqual(arbzg.feiertag_name(date(2026, 9, 14)), "")

    # Betriebszeit
    def test_betriebszeit_erfuellt(self):
        """6 bis 22 Uhr liegt ganz in der Betriebszeit."""
        self.assertEqual(arbzg.pruefe_betriebszeit(tag(date(2026, 9, 14), time(6, 0), time(22, 0), 45)), [])

    def test_betriebszeit_warnung(self):
        """Beginn um 5:30 Uhr: Warnung, weil die Zeit vor 6 Uhr nicht zählt."""
        meldungen = arbzg.pruefe_betriebszeit(tag(date(2026, 9, 14), time(5, 30), time(15, 0), 45))
        self.assertEqual(meldungen[0]["paragraph"], "Betrieb")

    # Alles zusammen
    def test_pruefe_tag_sammelt_alles(self):
        """Ein Sonntag mit zu wenig Ruhe und ohne Pause: pruefe_tag sammelt alle Meldungen."""
        vortag = tag(date(2026, 9, 12), time(8, 0), time(22, 0), 30, time(12, 0))
        heute = tag(date(2026, 9, 13), time(6, 0), time(17, 0), 0)
        paragraphen = []
        for meldung in arbzg.pruefe_tag(heute, vortag):
            paragraphen.append(meldung["paragraph"])
        self.assertEqual(paragraphen, ["§ 3 ArbZG", "§ 4 ArbZG", "§ 9 ArbZG", "§ 5 ArbZG"])

    def test_status(self):
        """Ohne Meldung grün, mit Warnung orange, mit Verletzung rot."""
        self.assertEqual(arbzg.status_aus_meldungen([]), "gruen")
        self.assertEqual(arbzg.status_aus_meldungen([{"art": "Warnung"}]), "orange")
        self.assertEqual(arbzg.status_aus_meldungen([{"art": "Warnung"}, {"art": "Verletzung"}]), "rot")

    # Nur grobe Verletzungen für das Warn-Popup
    def test_nur_verletzungen_ohne_verletzung(self):
        """Nur eine Warnung: für das Warnfenster bleibt nichts übrig."""
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(8, 0), time(17, 30), 30, time(12, 0)), None)
        self.assertEqual(meldungen[0]["art"], "Warnung")
        self.assertEqual(arbzg.nur_verletzungen(meldungen), [])

    def test_nur_verletzungen_mit_verletzung(self):
        """Über 10 h mit zu wenig Pause: zwei Verletzungen, die Warnung fällt weg."""
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(7, 0), time(18, 30), 30, time(12, 0)), None)
        verletzungen = arbzg.nur_verletzungen(meldungen)
        self.assertEqual(len(verletzungen), 2)
        self.assertEqual(verletzungen[0]["paragraph"], "§ 3 ArbZG")
        self.assertEqual(verletzungen[1]["paragraph"], "§ 4 ArbZG")

    # 6-Monats-Durchschnitt je Werktag (Montag bis Samstag)
    def arbeitstage(self, von, bis, beginn, ende, mit_samstag):
        """Hilfe: Einträge für jeden Arbeitstag von "von" bis "bis"."""
        eintraege = []
        datum = von
        while datum <= bis:
            if datum.weekday() < 5 or (mit_samstag and datum.weekday() == 5):
                if arbzg.feiertag_name(datum) == "":
                    eintraege.append(tag(datum, beginn, ende, 45))
            datum = datum + timedelta(days=1)
        return eintraege

    def test_durchschnitt_erfuellt(self):
        """6 Monate lang Montag bis Freitag je 9 h: 45 h pro Woche, im Schnitt 7:30 h je Werktag."""
        eintraege = self.arbeitstage(date(2026, 3, 1), date(2026, 9, 28), time(8, 0), time(17, 45), False)
        self.assertEqual(arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 3, 1), date(2026, 9, 28)), [])

    def test_durchschnitt_verletzt(self):
        """6 Monate lang Montag bis Samstag je 9 h: im Schnitt mehr als 8 h je Werktag."""
        eintraege = self.arbeitstage(date(2026, 3, 1), date(2026, 9, 28), time(8, 0), time(17, 45), True)
        meldungen = arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 3, 1), date(2026, 9, 28))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_durchschnitt_kurz_erfasst_nur_warnung(self):
        """Erst eine Woche erfasst: Ausgleich noch möglich, deshalb nur eine Warnung."""
        eintraege = self.arbeitstage(date(2026, 9, 14), date(2026, 9, 19), time(7, 0), time(17, 45), True)
        meldungen = arbzg.pruefe_sechs_monate_durchschnitt(eintraege, [], date(2026, 9, 14), date(2026, 9, 19))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    def test_werktage_ohne_sonntag_feiertag_urlaub(self):
        """28.09. bis 04.10.2026: Mo-Sa sind 6 Tage, der 03.10. ist Feiertag, der 29.09. Urlaub."""
        urlaub = [Abwesenheit(date(2026, 9, 29), date(2026, 9, 29), "Urlaub")]
        self.assertEqual(arbzg.werktage_im_zeitraum(date(2026, 9, 28), date(2026, 10, 4), urlaub), 4)

    def test_durchschnitt_sonntag_zaehlt_als_tag(self):
        """Mo 14.9. bis So 20.9. je 8 h: der Sonntag steht im Zähler und im Nenner, also 7 Tage."""
        eintraege = []
        for nummer in range(14, 21):
            eintraege.append(tag(date(2026, 9, nummer), time(8, 0), time(16, 45), 45))
        summe, tage = arbzg.minuten_und_tage(eintraege, [], date(2026, 9, 14), date(2026, 9, 20))
        self.assertEqual(tage, 7)
        self.assertEqual(summe // tage, 480)

    # § 6 Nachtarbeit
    def nachtschichten(self, von, bis):
        """Hilfe: jede Nacht von Montag bis Samstag 22:00 bis 7:30 mit 30 min Pause, also 9 h."""
        eintraege = []
        datum = von
        while datum <= bis:
            if datum.weekday() < 6:
                eintraege.append(tag(datum, time(22, 0), time(7, 30), 30, time(2, 0)))
            datum = datum + timedelta(days=1)
        return eintraege

    def test_p6_nachtarbeit_ueber_8h_warnung(self):
        """Eine einzelne Nacht mit 9 h: noch ausgleichbar, deshalb nur eine Warnung."""
        nacht = tag(date(2026, 9, 14), time(22, 0), time(7, 30), 30, time(2, 0))
        meldungen = arbzg.pruefe_nachtarbeit(nacht, [nacht], [], None)
        self.assertEqual(meldungen[0]["art"], "Warnung")
        self.assertEqual(meldungen[0]["paragraph"], "§ 6 ArbZG")

    def test_p6_schnitt_ueber_4_wochen_verletzt(self):
        """4 Wochen lang jede Nacht 9 h: im Schnitt mehr als 8 h je Werktag."""
        eintraege = self.nachtschichten(date(2026, 8, 17), date(2026, 9, 14))
        meldungen = arbzg.pruefe_nachtarbeit(eintraege[-1], eintraege, [], None)
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertIn("9:00 h je Werktag in 4 Wochen", meldungen[0]["text"])

    def test_p6_kurz_erfasst_nur_warnung(self):
        """Erst seit einer Woche erfasst: der Schnitt kann noch sinken."""
        eintraege = self.nachtschichten(date(2026, 9, 7), date(2026, 9, 14))
        meldungen = arbzg.pruefe_nachtarbeit(eintraege[-1], eintraege, [], date(2026, 9, 7))
        self.assertEqual(meldungen[0]["art"], "Warnung")
        self.assertIn("Bis 4 Wochen erfasst sind", meldungen[0]["text"])

    def test_p6_tagschicht_nicht_betroffen(self):
        """10 h am Tag sind keine Nachtarbeit, dafür ist § 3 zuständig."""
        lang = tag(date(2026, 9, 14), time(7, 0), time(17, 30), 30, time(12, 0))
        self.assertEqual(arbzg.pruefe_nachtarbeit(lang, [lang], [], None), [])

    # § 11 Ersatzruhetag und freie Sonntage
    def werktage_mit_arbeit(self, von, bis, ausser=None):
        """Hilfe: Arbeit an jedem Werktag (Montag bis Samstag, kein Feiertag) außer am Tag "ausser"."""
        eintraege = []
        datum = von
        while datum <= bis:
            if datum.weekday() < 6 and arbzg.feiertag_name(datum) == "" and datum != ausser:
                eintraege.append(tag(datum, time(8, 0), time(16, 30), 30, time(12, 0)))
            datum = datum + timedelta(days=1)
        return eintraege

    def test_p11_ersatzruhetag_vorhanden(self):
        """Arbeit am So 13.9., dafür ist Sa 19.9. frei."""
        sonntag = tag(date(2026, 9, 13), time(8, 0), time(12, 0), 0)
        eintraege = self.werktage_mit_arbeit(date(2026, 8, 31), date(2026, 9, 26), date(2026, 9, 19)) + [sonntag]
        self.assertEqual(arbzg.pruefe_ersatzruhetag(sonntag, eintraege, date(2026, 8, 31), date(2026, 10, 1)), [])

    def test_p11_kein_ersatzruhetag_verletzt(self):
        """Arbeit am So 13.9. und zwei Wochen davor und danach kein freier Werktag."""
        sonntag = tag(date(2026, 9, 13), time(8, 0), time(12, 0), 0)
        eintraege = self.werktage_mit_arbeit(date(2026, 8, 31), date(2026, 9, 26)) + [sonntag]
        meldungen = arbzg.pruefe_ersatzruhetag(sonntag, eintraege, date(2026, 8, 31), date(2026, 10, 1))
        self.assertEqual(meldungen[0]["art"], "Verletzung")
        self.assertEqual(meldungen[0]["text"], "Für die Arbeit am Sonntag gab es innerhalb von 2 Wochen keinen Ersatzruhetag.")

    def test_p11_frist_laeuft_noch_warnung(self):
        """Am 15.9. ist die Frist noch offen: Warnung mit dem letzten möglichen Tag."""
        sonntag = tag(date(2026, 9, 13), time(8, 0), time(12, 0), 0)
        eintraege = self.werktage_mit_arbeit(date(2026, 8, 31), date(2026, 9, 14)) + [sonntag]
        meldungen = arbzg.pruefe_ersatzruhetag(sonntag, eintraege, date(2026, 8, 31), date(2026, 9, 15))
        self.assertEqual(meldungen[0]["art"], "Warnung")
        self.assertIn("Bis 26.09.2026 einen Werktag frei nehmen.", meldungen[0]["text"])

    def test_p11_feiertag_acht_wochen(self):
        """Arbeit am Sa 3.10. (Feiertag): ohne freien Werktag in 8 Wochen ist das eine Verletzung."""
        feiertag = tag(date(2026, 10, 3), time(8, 0), time(12, 0), 0)
        eintraege = self.werktage_mit_arbeit(date(2026, 8, 1), date(2026, 12, 1)) + [feiertag]
        meldungen = arbzg.pruefe_ersatzruhetag(feiertag, eintraege, date(2026, 8, 1), date(2026, 12, 15))
        self.assertIn("innerhalb von 8 Wochen", meldungen[0]["text"])

    def test_p11_15_sonntage_frei(self):
        """2026 hat 52 Sonntage: an 37 arbeiten ist erlaubt, ab 38 bleiben keine 15 mehr frei."""
        sonntage = []
        datum = date(2026, 1, 4)
        while len(sonntage) < 38:
            sonntage.append(tag(datum, time(8, 0), time(12, 0), 0))
            datum = datum + timedelta(days=7)
        self.assertEqual(arbzg.pruefe_freie_sonntage(sonntage[36], sonntage[:37]), [])
        meldungen = arbzg.pruefe_freie_sonntage(sonntage[37], sonntage)
        self.assertEqual(meldungen[0]["text"], "Im Jahr 2026 bleiben nur 14 Sonntage frei, mindestens 15 müssen es sein.")

    def test_p11_freier_tag_zaehlt_nur_einmal(self):
        """Arbeit an den Sonntagen 7.6. und 14.6., frei nur Sa 13.6.: der zweite Sonntag hat keinen Ersatzruhetag."""
        erster = tag(date(2026, 6, 7), time(8, 0), time(12, 0), 0)
        zweiter = tag(date(2026, 6, 14), time(8, 0), time(12, 0), 0)
        eintraege = self.werktage_mit_arbeit(date(2026, 5, 25), date(2026, 6, 27), date(2026, 6, 13)) + [erster, zweiter]
        self.assertEqual(arbzg.pruefe_ersatzruhetag(erster, eintraege, date(2026, 5, 25), date(2026, 7, 1)), [])
        meldungen = arbzg.pruefe_ersatzruhetag(zweiter, eintraege, date(2026, 5, 25), date(2026, 7, 1))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_p11_tag_nach_nachtschicht_ist_nicht_frei(self):
        """Nachtschicht So 13.9. 22 Uhr bis Mo 6 Uhr: der Montag hat keinen eigenen Eintrag, ist aber nicht frei."""
        sonntag = tag(date(2026, 9, 13), time(22, 0), time(6, 0), 30, time(2, 0))
        eintraege = self.werktage_mit_arbeit(date(2026, 8, 31), date(2026, 9, 26), date(2026, 9, 14)) + [sonntag]
        meldungen = arbzg.pruefe_ersatzruhetag(sonntag, eintraege, date(2026, 8, 31), date(2026, 10, 1))
        self.assertEqual(meldungen[0]["art"], "Verletzung")

    def test_p11_tage_vor_der_erfassung_sind_nicht_frei(self):
        """Erster Eintrag ist ein Sonntag: die Tage davor sind unbekannt und zählen nicht als Ersatzruhetag."""
        sonntag = tag(date(2026, 9, 13), time(8, 0), time(12, 0), 0)
        meldungen = arbzg.pruefe_ersatzruhetag(sonntag, [sonntag], date(2026, 9, 13), date(2026, 9, 14))
        self.assertEqual(meldungen[0]["art"], "Warnung")

    def test_p11_nachtschicht_in_den_sonntag_zaehlt(self):
        """38 Nachtschichten von Samstag auf Sonntag: der Teil nach Mitternacht zählt als Arbeit am Sonntag."""
        nachtschichten = []
        datum = date(2026, 1, 3)
        while len(nachtschichten) < 38:
            nachtschichten.append(tag(datum, time(22, 0), time(4, 0), 0))
            datum = datum + timedelta(days=7)
        meldungen = arbzg.pruefe_freie_sonntage(nachtschichten[37], nachtschichten)
        self.assertEqual(meldungen[0]["text"], "Im Jahr 2026 bleiben nur 14 Sonntage frei, mindestens 15 müssen es sein.")

    # Warnung beim Einstempeln
    def test_einstempeln_warnt_bei_kurzer_ruhezeit(self):
        """Ende am Vortag um 23 Uhr, Einstempeln um 6 Uhr: erst 7 h Ruhe."""
        vortag = tag(date(2026, 9, 14), time(14, 0), time(23, 0), 30, time(18, 0))
        warnungen = arbzg.warnungen_beim_einstempeln(datetime(2026, 9, 15, 6, 0), vortag)
        self.assertEqual(warnungen[0]["art"], "Warnung")
        self.assertEqual(warnungen[0]["text"], "Seit dem Ende am Vortag sind erst 7:00 h vergangen, nötig sind 11 Stunden Ruhezeit.")

    def test_einstempeln_warnt_am_sonntag(self):
        """Einstempeln an einem Sonntag: Warnung nach § 9."""
        warnungen = arbzg.warnungen_beim_einstempeln(datetime(2026, 9, 13, 9, 0), None)
        self.assertEqual(warnungen[0]["paragraph"], "§ 9 ArbZG")
        self.assertEqual(warnungen[0]["art"], "Warnung")

    def test_einstempeln_am_nachmittag_vor_sonntag(self):
        """Samstag 15 Uhr einstempeln: die Schicht kann in den Sonntag laufen, morgens am Samstag nicht."""
        warnungen = arbzg.warnungen_beim_einstempeln(datetime(2026, 9, 12, 15, 0), None)
        self.assertEqual(warnungen[0]["text"], "Arbeit an einem Sonntag (nach Mitternacht) ist nicht zulässig.")
        self.assertEqual(arbzg.warnungen_beim_einstempeln(datetime(2026, 9, 12, 9, 0), None), [])

    def test_einstempeln_ohne_warnung(self):
        """Normaler Arbeitstag nach normalem Vortag: keine Warnung."""
        vortag = tag(date(2026, 9, 14), time(8, 0), time(16, 30), 30, time(12, 0))
        self.assertEqual(arbzg.warnungen_beim_einstempeln(datetime(2026, 9, 15, 8, 0), vortag), [])

    # Osterformel und Feiertage nach 2030
    def test_ostersonntag(self):
        """Gaußsche Osterformel für drei Jahre."""
        self.assertEqual(arbzg.ostersonntag(2026), date(2026, 4, 5))
        self.assertEqual(arbzg.ostersonntag(2031), date(2031, 4, 13))
        self.assertEqual(arbzg.ostersonntag(2038), date(2038, 4, 25))

    def test_feiertage_nach_2030(self):
        """Auch 2031 gibt es 12 Feiertage, Karfreitag hängt an Ostern."""
        feiertage = arbzg.feiertage_bw(2031)
        self.assertEqual(len(feiertage), 12)
        self.assertEqual(feiertage[date(2031, 4, 11)], "Karfreitag")

    # § 4 Satz 3: höchstens 6 Stunden am Stück
    def test_p4_am_stueck_erfuellt(self):
        """Pause um 12 Uhr: nie mehr als 6 h am Stück."""
        eintrag = Zeiteintrag(date(2026, 9, 14), time(8, 0), time(17, 0), 30, time(12, 0))
        self.assertEqual(arbzg.pruefe_pause_am_stueck(eintrag), [])

    def test_p4_am_stueck_verletzt(self):
        """Pause erst um 15 Uhr: vorher 7 h am Stück."""
        eintrag = Zeiteintrag(date(2026, 9, 14), time(8, 0), time(17, 0), 30, time(15, 0))
        meldungen = arbzg.pruefe_pause_am_stueck(eintrag)
        self.assertEqual(meldungen[0]["text"], "7:00 h am Stück ohne Pause, erlaubt sind 6 Stunden.")

    def test_p4_am_stueck_mit_zwei_pausen_erfuellt(self):
        """Früher als ein Block ab 10:00 gerechnet: 10:30 bis 17:00 wären 6:30 h am Stück gewesen."""
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(8, 0), time(17, 0),
                                     [Pause(time(10, 0), 15), Pause(time(14, 0), 15)])
        self.assertEqual(arbzg.pruefe_pause_am_stueck(eintrag), [])

    def test_pausen_werden_nach_lage_sortiert(self):
        """Nachtschicht: 2:00 liegt nach 23:30, erste Pause ist also 23:30."""
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(22, 0), time(6, 0),
                                     [Pause(time(2, 0), 15), Pause(time(23, 30), 15)])
        self.assertEqual(eintrag.pause_beginn, time(23, 30))

    def test_p4_zwei_kurze_pausen_zaehlen_nicht(self):
        """Zweimal 10 min sind keine Ruhepause, auch nicht zusammen."""
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(8, 0), time(15, 0),
                                     [Pause(time(10, 0), 10), Pause(time(12, 0), 10)])
        meldungen = arbzg.pruefe_pause(eintrag)
        self.assertEqual(meldungen[0]["text"], "Pause zu kurz: 0 min statt 30 min. Pausen unter 15 min zählen nicht.")
        self.assertEqual(arbzg.pruefe_pause_am_stueck(eintrag), [])

    def test_p4_am_stueck_mit_zwei_pausen_verletzt(self):
        """Beide Pausen am Vormittag: danach 7:30 h am Stück."""
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(7, 0), time(17, 0),
                                     [Pause(time(8, 0), 15), Pause(time(9, 0), 30)])
        meldungen = arbzg.pruefe_pause_am_stueck(eintrag)
        self.assertEqual(meldungen[0]["text"], "7:30 h am Stück ohne Pause, erlaubt sind 6 Stunden.")

    def test_p4_ohne_pause_nur_eine_meldung(self):
        """Ganz ohne Pause kommt § 4 nur einmal, nicht noch für am Stück."""
        meldungen = arbzg.pruefe_tag(tag(date(2026, 9, 14), time(8, 0), time(15, 0), 0), None)
        self.assertEqual(len(meldungen), 1)
        self.assertEqual(meldungen[0]["text"], "Pause zu kurz: 0 min statt 30 min.")

    def test_p4_meldung_nennt_nur_zaehlende_pausen(self):
        """10 und 20 min Pause: nur die 20 min zählen, das steht auch so in der Meldung."""
        eintrag = eintrag_mit_pausen(date(2026, 9, 14), time(8, 0), time(15, 0),
                                     [Pause(time(10, 0), 10), Pause(time(12, 0), 20)])
        meldungen = arbzg.pruefe_pause(eintrag)
        self.assertEqual(meldungen[0]["text"], "Pause zu kurz: 20 min statt 30 min. Pausen unter 15 min zählen nicht.")

    # Nachtschichten
    def test_nachtschicht_in_den_sonntag(self):
        """Samstag 22 Uhr bis Sonntag 6 Uhr: der Teil nach Mitternacht liegt am Sonntag."""
        samstag_nacht = tag(date(2026, 9, 12), time(22, 0), time(6, 0), 30)
        meldungen = arbzg.pruefe_sonntag_feiertag(samstag_nacht)
        self.assertEqual(meldungen[0]["text"], "Arbeit an einem Sonntag (nach Mitternacht) ist nicht zulässig.")

    def test_nachtschicht_an_werktagen_erfuellt(self):
        """Nachtschicht von Montag auf Dienstag: kein Ruhetag betroffen."""
        montag_nacht = tag(date(2026, 9, 14), time(22, 0), time(6, 0), 30)
        self.assertEqual(arbzg.pruefe_sonntag_feiertag(montag_nacht), [])

    def test_ruhezeit_nach_nachtschicht(self):
        """Nachtschicht endet um 6 Uhr, Beginn um 14 Uhr: nur 8 h Ruhe."""
        vortag = tag(date(2026, 9, 14), time(22, 0), time(6, 0), 30)
        heute = tag(date(2026, 9, 15), time(14, 0), time(20, 0), 0)
        self.assertIn("8:00 h", arbzg.pruefe_ruhezeit(heute, vortag)[0]["text"])

    def test_ruhezeit_vortag_fehlt(self):
        """Fehlt der Vortag, gibt es eine Warnung, aber nur, wenn er vergessen wurde."""
        heute = tag(date(2026, 9, 15), time(8, 0), time(16, 0), 30)
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, None, True)[0]["art"], "Warnung")
        self.assertEqual(arbzg.pruefe_ruhezeit(heute, None, False), [])


if __name__ == "__main__":
    unittest.main()
