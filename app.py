"""Wendezeit - Arbeitszeiterfassung für die BBQ GmbH. Start: python app.py, dann http://localhost:5000"""
import os
import secrets
from datetime import date, datetime

from flask import Flask, request, jsonify, session, send_from_directory

from logik import speicher, gleitzeit, stempeluhr, arbzg, zeit
from logik.modelle import Zeiteintrag, Abwesenheit, Pause, eintrag_mit_pausen, pausen_von
from logik.speicher import text_zu_datum, text_zu_zeit, datum_zu_text, zeit_zu_text

FRONTEND_ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

app = Flask(__name__, static_folder=None)
# Auf Railway steht der Schlüssel fest in SECRET_KEY. Würde er bei jedem Start neu erzeugt,
# wäre danach jeder ausgeloggt
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))


# Hilfen

def angemeldet() -> bool:
    """Ist in dieser Sitzung jemand eingeloggt?"""
    return session.get("angemeldet", False)


def fehler(text: str):
    """Antwort mit Fehlertext."""
    return jsonify({"ok": False, "fehler": text})


def nicht_angemeldet():
    """Antwort, wenn eine geschützte Route ohne Login aufgerufen wird."""
    return fehler("Nicht angemeldet")


@app.errorhandler(KeyError)
@app.errorhandler(TypeError)
@app.errorhandler(ValueError)
def ungueltige_anfrage(_fehler):
    """Fehlt ein Feld oder steht Unsinn darin (z. B. "abc" als Uhrzeit), gibt es eine Meldung statt Fehler 500.
    Ohne JSON liefert get_json(silent=True) None, das landet als TypeError auch hier."""
    # Im Log steht der ganze Fehler, falls es doch ein Programmierfehler war
    app.logger.warning("Ungültige Anfrage: %r", _fehler)
    return fehler("Die Eingabe ist unvollständig oder ungültig.")


# Oberfläche ausliefern

@app.route("/")
def startseite():
    """Liefert die Startseite der Oberfläche."""
    return send_from_directory(FRONTEND_ORDNER, "index.html")


@app.route("/<path:dateiname>")
def frontend_datei(dateiname):
    """Liefert style.css, app.js und die anderen Dateien aus frontend/."""
    return send_from_directory(FRONTEND_ORDNER, dateiname)


# Login

@app.route("/api/status")
def api_status():
    """Erststart (noch kein Passwort) und Login-Zustand."""
    einstellungen = speicher.lade_einstellungen()
    return jsonify({"erststart": einstellungen.passwort_hash == "", "eingeloggt": angemeldet()})


@app.route("/api/passwort-setzen", methods=["POST"])
def api_passwort_setzen():
    """Erster Start: Passwort zweimal eingeben und als Hash speichern."""
    daten = request.get_json(silent=True)
    einstellungen = speicher.lade_einstellungen()
    if einstellungen.passwort_hash != "":
        return fehler("Es gibt schon ein Passwort.")
    if len(daten["passwort"]) < 6:
        return fehler("Das Passwort muss mindestens 6 Zeichen haben.")
    if daten["passwort"] != daten["wiederholung"]:
        return fehler("Die Passwörter stimmen nicht überein.")
    hash_wert, salt = speicher.passwort_hash_erzeugen(daten["passwort"])
    einstellungen.passwort_hash = hash_wert
    einstellungen.passwort_salt = salt
    speicher.speichere_einstellungen(einstellungen)
    session["angemeldet"] = True
    return jsonify({"ok": True})


@app.route("/api/login", methods=["POST"])
def api_login():
    """Passwort prüfen und Sitzung starten."""
    daten = request.get_json(silent=True)
    einstellungen = speicher.lade_einstellungen()
    if not speicher.passwort_pruefen(daten["passwort"], einstellungen.passwort_hash, einstellungen.passwort_salt):
        return fehler("Falsches Passwort.")
    session["angemeldet"] = True
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Sitzung beenden."""
    session["angemeldet"] = False
    return jsonify({"ok": True})


@app.route("/api/passwort-aendern", methods=["POST"])
def api_passwort_aendern():
    """Altes Passwort prüfen, neues Passwort speichern."""
    if not angemeldet():
        return nicht_angemeldet()
    daten = request.get_json(silent=True)
    einstellungen = speicher.lade_einstellungen()
    if not speicher.passwort_pruefen(daten["alt"], einstellungen.passwort_hash, einstellungen.passwort_salt):
        return fehler("Aktuelles Passwort ist falsch.")
    if len(daten["neu"]) < 6:
        return fehler("Neues Passwort muss mindestens 6 Zeichen haben.")
    hash_wert, salt = speicher.passwort_hash_erzeugen(daten["neu"])
    einstellungen.passwort_hash = hash_wert
    einstellungen.passwort_salt = salt
    speicher.speichere_einstellungen(einstellungen)
    return jsonify({"ok": True})


# Daten für die Oberfläche

def lade_alles():
    """Lädt Einstellungen, Zeiteinträge und Abwesenheiten."""
    return speicher.lade_einstellungen(), speicher.lade_eintraege(), speicher.lade_abwesenheiten()


def einstellungen_fuer_api(einstellungen) -> dict:
    """Die Einstellungen ohne Passwort, so wie die Oberfläche sie braucht."""
    erfassung_ab = ""
    if einstellungen.erfassung_ab is not None:
        erfassung_ab = datum_zu_text(einstellungen.erfassung_ab)
    return {"wochenstunden": einstellungen.wochenstunden,
            "ampel_orange_stunden": einstellungen.ampel_orange_stunden,
            "ampel_rot_stunden": einstellungen.ampel_rot_stunden,
            "ampel_minus_orange_stunden": einstellungen.ampel_minus_orange_stunden,
            "ampel_minus_rot_stunden": einstellungen.ampel_minus_rot_stunden,
            "erfassung_ab": erfassung_ab,
            "name": einstellungen.name}


def zeitraum_aus_anfrage(heute: date):
    """Liest den Zeitraum aus der URL, z. B. /api/daten?von=2026-07-01&bis=2026-09-30.
    Fehlt "von" oder "bis", gilt der aktuelle Monat."""
    von_text = request.args.get("von", "")
    bis_text = request.args.get("bis", "")
    if von_text == "" or bis_text == "":
        return date(heute.year, heute.month, 1), gleitzeit.letzter_tag_im_monat(heute.year, heute.month)
    return text_zu_datum(von_text), text_zu_datum(bis_text)


@app.route("/api/daten")
def api_daten():
    """Alles für einen Zeitraum: Konto, Ampel, Stempeluhr, Tagesliste, Gleitzeit und 6-Monats-Durchschnitt."""
    if not angemeldet():
        return nicht_angemeldet()
    heute = zeit.heute()
    von, bis = zeitraum_aus_anfrage(heute)
    einstellungen, eintraege, abwesenheiten = lade_alles()
    saldo = gleitzeit.saldo_gesamt(eintraege, abwesenheiten, einstellungen, heute)
    return jsonify({
        "heute": datum_zu_text(heute),
        "heute_hat_eintrag": speicher.finde_eintrag(eintraege, heute) is not None,
        "einstellungen": einstellungen_fuer_api(einstellungen),
        "konto": {"minuten": saldo, "ampel": gleitzeit.ampel(saldo, einstellungen)},
        "durchschnitt": arbzg.pruefe_sechs_monate_durchschnitt(
            eintraege, abwesenheiten, gleitzeit.erfassung_beginn(eintraege, einstellungen), heute),
        "stempel": speicher.lade_stempeluhr(),
        "zeitraum_minuten": gleitzeit.saldo_zeitraum(eintraege, abwesenheiten, von, bis, einstellungen, heute),
        "tage": gleitzeit.tage_fuer_zeitraum(von, bis, eintraege, abwesenheiten, einstellungen, heute),
    })


# Einträge

def eintrag_aus_anfrage(daten: dict) -> Zeiteintrag:
    """Baut aus den Formulardaten einen Zeiteintrag. "pausen" ist eine Liste aus {"ab": "12:00", "minuten": 30}.
    Pausen mit 0 Minuten fallen weg, ein leeres "ab" wird None."""
    pausen = []
    for pause in daten["pausen"]:
        pausen.append(Pause(speicher.text_oder_none_zu_zeit(pause.get("ab", "")), int(pause["minuten"])))
    return eintrag_mit_pausen(text_zu_datum(daten["datum"]), text_zu_zeit(daten["beginn"]),
                              text_zu_zeit(daten["ende"]), pausen)


def fehler_fuer_eintrag(eintrag: Zeiteintrag) -> str:
    """Unmögliche Angaben wie Pause länger als die Arbeitszeit. "" wenn alles passt."""
    return zeit.pruefe_eingabe(eintrag.beginn, eintrag.ende, pausen_von(eintrag))


def verletzungen_fuer(eintrag: Zeiteintrag, eintraege: list, abwesenheiten: list, einstellungen) -> list[dict]:
    """Nur die Verletzungen (rote Meldungen) für einen gespeicherten Tag, für das Warn-Popup."""
    bewertung = gleitzeit.bewerte_eintrag(eintrag, eintraege, abwesenheiten, einstellungen, zeit.heute())
    return arbzg.nur_verletzungen(bewertung["meldungen"])


@app.route("/api/vorschau", methods=["POST"])
def api_vorschau():
    """Rechnet eine Eingabe durch, ohne sie zu speichern."""
    if not angemeldet():
        return nicht_angemeldet()
    eintrag = eintrag_aus_anfrage(request.get_json(silent=True))
    fehlertext = fehler_fuer_eintrag(eintrag)
    if fehlertext != "":
        return fehler(fehlertext)
    einstellungen, eintraege, abwesenheiten = lade_alles()
    return jsonify(gleitzeit.bewerte_eintrag(eintrag, eintraege, abwesenheiten, einstellungen, zeit.heute()))


@app.route("/api/eintrag", methods=["POST"])
def api_eintrag():
    """Speichert einen Zeiteintrag. Ein Eintrag am selben Datum wird ersetzt."""
    if not angemeldet():
        return nicht_angemeldet()
    eintrag = eintrag_aus_anfrage(request.get_json(silent=True))
    fehlertext = fehler_fuer_eintrag(eintrag)
    if fehlertext != "":
        return fehler(fehlertext)
    einstellungen, eintraege, abwesenheiten = lade_alles()
    speicher.setze_eintrag(eintraege, eintrag)
    speicher.speichere_eintraege(eintraege)
    return jsonify({"ok": True, "datum": datum_zu_text(eintrag.datum),
                    "verletzungen": verletzungen_fuer(eintrag, eintraege, abwesenheiten, einstellungen)})


@app.route("/api/eintrag-loeschen", methods=["POST"])
def api_eintrag_loeschen():
    """Löscht den Zeiteintrag an einem Datum."""
    if not angemeldet():
        return nicht_angemeldet()
    daten = request.get_json(silent=True)
    eintraege = speicher.lade_eintraege()
    speicher.entferne_eintrag(eintraege, text_zu_datum(daten["datum"]))
    speicher.speichere_eintraege(eintraege)
    return jsonify({"ok": True})


# Abwesenheiten

@app.route("/api/abwesenheit", methods=["POST"])
def api_abwesenheit():
    """Speichert eine Abwesenheit von ... bis ..., wenn sie sich mit keiner anderen überschneidet."""
    if not angemeldet():
        return nicht_angemeldet()
    daten = request.get_json(silent=True)
    abwesenheit = Abwesenheit(text_zu_datum(daten["von"]), text_zu_datum(daten["bis"]),
                              daten["art"], daten.get("grund", ""))
    abwesenheiten = speicher.lade_abwesenheiten()
    fehlertext = gleitzeit.pruefe_abwesenheit(abwesenheit, abwesenheiten)
    if fehlertext != "":
        return fehler(fehlertext)
    abwesenheiten.append(abwesenheit)
    speicher.speichere_abwesenheiten(abwesenheiten)
    return jsonify({"ok": True})


@app.route("/api/abwesenheit-loeschen", methods=["POST"])
def api_abwesenheit_loeschen():
    """Löscht die Abwesenheit, die an diesem Datum beginnt."""
    if not angemeldet():
        return nicht_angemeldet()
    daten = request.get_json(silent=True)
    abwesenheiten = speicher.lade_abwesenheiten()
    speicher.entferne_abwesenheit(abwesenheiten, text_zu_datum(daten["von"]))
    speicher.speichere_abwesenheiten(abwesenheiten)
    return jsonify({"ok": True})


# Einstellungen

def einstellungen_aus_anfrage(daten: dict):
    """Übernimmt die Formularwerte in die gespeicherten Einstellungen (Passwort bleibt, wie es ist)."""
    einstellungen = speicher.lade_einstellungen()
    einstellungen.wochenstunden = int(daten["wochenstunden"])
    einstellungen.ampel_orange_stunden = float(daten["ampel_orange_stunden"])
    einstellungen.ampel_rot_stunden = float(daten["ampel_rot_stunden"])
    einstellungen.ampel_minus_orange_stunden = float(daten.get("ampel_minus_orange_stunden", 10))
    einstellungen.ampel_minus_rot_stunden = float(daten.get("ampel_minus_rot_stunden", 20))
    einstellungen.erfassung_ab = speicher.text_oder_none_zu_datum(daten.get("erfassung_ab", ""))
    einstellungen.name = daten.get("name", einstellungen.name).strip()
    return einstellungen


@app.route("/api/einstellungen", methods=["POST"])
def api_einstellungen():
    """Speichert Wochenstunden, Ampelgrenzen für Plus und Minus, Beginn der Zeiterfassung und Namen."""
    if not angemeldet():
        return nicht_angemeldet()
    einstellungen = einstellungen_aus_anfrage(request.get_json(silent=True))
    fehlertext = gleitzeit.pruefe_einstellungen(einstellungen)
    if fehlertext != "":
        return fehler(fehlertext)
    speicher.speichere_einstellungen(einstellungen)
    return jsonify({"ok": True})


# Stempeluhr

@app.route("/api/stempel", methods=["POST"])
def api_stempel():
    """Stempeluhr bedienen: einstempeln, pause_start, pause_ende, ausstempeln."""
    if not angemeldet():
        return nicht_angemeldet()
    aktion = request.get_json(silent=True)["aktion"]
    zustand = speicher.lade_stempeluhr()
    jetzt = zeit.jetzt()
    antwort = {"ok": True, "hinweis": ""}
    if aktion == "einstempeln":
        antwort = einstempeln_wenn_frei(zustand, jetzt)
    elif aktion == "pause_start":
        stempeluhr.pause_starten(zustand, jetzt)
    elif aktion == "pause_ende":
        stempeluhr.pause_beenden(zustand, jetzt)
    elif aktion == "ausstempeln":
        antwort = ausstempeln_und_speichern(zustand, jetzt)
    speicher.speichere_stempeluhr(zustand)
    return jsonify(antwort)


def einstempeln_wenn_frei(zustand: dict, jetzt: datetime) -> dict:
    """Stempelt ein, außer für heute gibt es schon einen Eintrag."""
    if zustand["status"] == "aus" and speicher.finde_eintrag(speicher.lade_eintraege(), jetzt.date()) is not None:
        return {"ok": False, "hinweis": "Für heute gibt es schon einen Eintrag. Bitte im Kalender bearbeiten."}
    stempeluhr.einstempeln(zustand, jetzt)
    return {"ok": True, "hinweis": ""}


def schon_vorhanden_text(neu: Zeiteintrag, vorhanden: Zeiteintrag) -> str:
    """Hinweis, wenn beim Ausstempeln für den Tag schon ein Eintrag existiert."""
    return ("Nicht gespeichert: Für " + neu.datum.strftime("%d.%m.%Y") + " gibt es schon einen Eintrag ("
            + zeit_zu_text(vorhanden.beginn) + " bis " + zeit_zu_text(vorhanden.ende) + "). Gestempelt wurde "
            + zeit_zu_text(neu.beginn) + " bis " + zeit_zu_text(neu.ende) + " mit " + str(neu.pause_minuten)
            + " min Pause. Bitte im Kalender zusammenführen.")


def ausstempeln_und_speichern(zustand: dict, jetzt: datetime) -> dict:
    """Macht aus der Stempeluhr einen Zeiteintrag und speichert ihn, ohne einen vorhandenen zu überschreiben.
    Gibt Hinweistext und die Verletzungen des Tages zurück."""
    eintrag, hinweis = stempeluhr.ausstempeln(zustand, jetzt)
    if eintrag is None:
        return {"ok": hinweis == "", "hinweis": hinweis}
    einstellungen, eintraege, abwesenheiten = lade_alles()
    vorhanden = speicher.finde_eintrag(eintraege, eintrag.datum)
    if vorhanden is not None:
        return {"ok": False, "hinweis": schon_vorhanden_text(eintrag, vorhanden)}
    fehlertext = fehler_fuer_eintrag(eintrag)
    if fehlertext != "":
        return {"ok": False, "hinweis": "Nicht gespeichert: " + fehlertext}
    speicher.setze_eintrag(eintraege, eintrag)
    speicher.speichere_eintraege(eintraege)
    return {"ok": True, "hinweis": hinweis, "datum": datum_zu_text(eintrag.datum),
            "verletzungen": verletzungen_fuer(eintrag, eintraege, abwesenheiten, einstellungen)}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
