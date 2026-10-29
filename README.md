# Wendezeit

Arbeitszeiterfassung für die BBQ GmbH. Fallstudie im Fach Systemanalyse an der DHBW Stuttgart.

Die Mitarbeiter tragen ihre Arbeitszeit selbst ein oder stempeln sich ein und aus. Jeder Tag wird gegen das
Arbeitszeitgesetz (ArbZG) geprüft. Bei einem Verstoß oder kurz davor gibt das Programm einen Hinweis.
Außerdem zeigt es die Gleitzeit je Monat, Quartal und Jahr und das Stundenkonto als Ampel.

Wendezeit ist eine Webapplikation. Sie läuft auf Railway und wird unter Windows 11 einfach im Browser
geöffnet, installieren muss man nichts.

## Stand

- [x] Grundgerüst: README, requirements.txt, .gitignore
- [x] Datenmodell und Zeitrechnung
- [x] Speichern, Benutzer und Passwort
- [x] Prüfungen nach dem ArbZG
- [x] Gleitzeit und Ampel
- [x] Stempeluhr
- [x] Webserver und Railway
- [x] Oberfläche
- [x] Beispieldaten und Dokumentation

## Technik

- Python 3.10 oder neuer
- Flask als Webserver, auf Railway 
- Oberfläche mit HTML, CSS und JavaScript, sie holt ihre Daten als JSON vom Server
- Daten liegen als JSON-Dateien im Ordner `daten/`, auf Railway in einem Volume, damit sie einen neuen
  Deploy überstehen. Der Ordner wird nicht eingecheckt.
- keine Lizenzkosten: Flask ist Open Source (BSD- bzw. MIT-Lizenz)

Die Fachlogik (ArbZG, Gleitzeit, Stempeluhr) liegt in einem eigenen Ordner `logik/` und weiß nichts von
Flask. Eine spätere Mobile App kann dieselbe JSON-Schnittstelle nutzen wie die Weboberfläche.

## Lokal starten

Unter Windows reicht ein Doppelklick auf `start.bat`. Das Skript installiert die Pakete, startet den
Server und öffnet http://localhost:5000 im Browser.

Von Hand geht es so:

```
python -m pip install -r requirements.txt
python app.py
```

Danach http://localhost:5000 im Browser öffnen. Beim ersten Start legt man das Passwort fest. Alle Daten
landen als JSON im Ordner `daten/`.

Die Tests laufen mit:

```
python -m unittest
```

## Beispieldaten

```
python demo_laden.py
```

Das Skript kopiert die Beispieldaten aus `daten_demo/` in den Datenordner. Vorhandene Einträge und
Abwesenheiten werden dabei überschrieben, Passwort und Einstellungen bleiben.

Damit die Demo zu jedem Zeitpunkt passt, werden die Daten um ganze Wochen verschoben, sodass sie bis
gestern reichen. Die Wochentage bleiben gleich, Urlaub und Krankheit wandern mit und `erfassung_ab` wird
auf den ersten Demotag gesetzt. Die Demo zeigt Warnungen und Verletzungen nach dem ArbZG und einen
absichtlich vergessenen Arbeitstag.

Feiertage wandern nicht mit. Landet ein Eintrag auf einem Feiertag, gibt das Skript einen Hinweis aus
(§ 9 ArbZG). Vor einer Präsentation die Demo deshalb am Vortag laden und einmal durchklicken.

## Railway

Einmalig einrichten:

1. Neues Projekt anlegen, Dienst aus diesem Repo, Branch `main`
2. Ein Volume anlegen und unter `/data` einhängen, damit Passwort und Einträge einen Deploy überstehen
3. Variablen setzen:
   - `WENDEZEIT_DATEN` = `/data`
   - `SECRET_KEY` = ein langer Zufallswert, z. B. aus `python -c "import secrets; print(secrets.token_hex(32))"`
   - `TZ` = `Europe/Berlin`
4. Unter Settings → Networking eine Domain erzeugen

Railway erkennt Python an der `requirements.txt`, nimmt die Version aus `.python-version` und startet
über das `Procfile` mit gunicorn.

Nach dem ersten Deploy sofort die Seite öffnen und das Passwort festlegen. Solange keins gesetzt ist,
kann das jeder, der die Adresse kennt.

Ist der Dienst mit dem Repo verbunden, geht jeder Merge nach `main` automatisch live. Sonst lädt man
den aktuellen Stand im Projektordner mit `railway up` hoch.

Die Beispieldaten kommen auf Railway über `railway ssh` in den Dienst, dort `python demo_laden.py`.

## Branches

Wir arbeiten nach GitHub Flow:

- `main`: lauffähiger Stand, wird nie direkt bearbeitet
- `feature/...`: ein Branch je Aufgabe, zweigt von `main` ab und kommt per Pull Request zurück, nachdem jemand aus dem Team ihn gelesen hat
