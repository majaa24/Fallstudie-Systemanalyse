# Wendezeit

Arbeitszeiterfassung für die BBQ GmbH. Fallstudie im Fach Systemanalyse an der DHBW Stuttgart.

Die Mitarbeiter tragen ihre Arbeitszeit selbst ein oder stempeln sich ein und aus. Jeder Tag wird gegen das
Arbeitszeitgesetz (ArbZG) geprüft. Bei einem Verstoß oder kurz davor gibt das Programm einen Hinweis.
Außerdem zeigt es die Gleitzeit je Monat, Quartal und Jahr und das Stundenkonto als Ampel.

Wendezeit ist eine Webapplikation. Sie läuft auf Railway und wird unter Windows 11 einfach im Browser
geöffnet, installieren muss man nichts.

## Benutzen

Wendezeit läuft unter https://wendezeit-production-05e4.up.railway.app

1. Den Link im Browser öffnen (unter Windows 11 z. B. Edge oder Chrome)
2. Mit dem Passwort anmelden, das Passwort gibt es beim Team

Mehr braucht es nicht. In der Anwendung sind Beispieldaten geladen, damit Gleitzeit, Ampel und die
Hinweise nach dem ArbZG gleich zu sehen sind.

## Stand

- [x] Grundgerüst: README, requirements.txt, .gitignore
- [x] Datenmodell und Zeitrechnung
- [x] Speichern und Passwort
- [x] Prüfungen nach dem ArbZG
- [x] Gleitzeit und Ampel
- [x] Stempeluhr
- [x] Webserver und Railway
- [x] Oberfläche
- [x] Beispieldaten und Dokumentation

## Technik

- Python 3.10 oder neuer
- Flask als Webserver, auf Railway startet ihn gunicorn
- Oberfläche mit HTML, CSS und JavaScript, sie holt ihre Daten als JSON vom Server
- Daten liegen als JSON-Dateien im Ordner `daten/`, auf Railway in einem Volume, damit sie einen neuen
  Deploy überstehen. Der Ordner wird nicht eingecheckt.
- keine Lizenzkosten: Flask (BSD-3), gunicorn (MIT) und tzdata (Apache 2.0) sind Open Source. Bezahlt
  wird nur das Hosting auf Railway.

## Aufbau

Die Fachlogik (ArbZG, Gleitzeit, Stempeluhr) liegt in einem eigenen Ordner `logik/` und weiß nichts von
Flask. Eine spätere Mobile App kann dieselbe JSON-Schnittstelle nutzen wie die Weboberfläche.

- `app.py` ist der Webserver. Er nimmt die Anfragen der Oberfläche an, ruft die Fachlogik auf und gibt
  das Ergebnis als JSON zurück. Hier liegt auch der Login.
- `logik/modelle.py` enthält die Datenklassen: Zeiteintrag, Pause, Abwesenheit und Einstellungen.
- `logik/zeit.py` rechnet mit Uhrzeiten und Minuten: Arbeitszeit, Zeit zwischen 6 und 22 Uhr, Nachtzeit
  und Sollzeit je Tag.
- `logik/speicher.py` liest und schreibt die JSON-Dateien und erzeugt den Passwort-Hash.
- `logik/arbzg.py` prüft einen Tag nach dem ArbZG (§§ 3, 4, 5, 6, 9 und 11) und kennt die Feiertage in
  Baden-Württemberg.
- `logik/gleitzeit.py` berechnet Gleitzeit und Ampel und stellt die Tagesliste für die Oberfläche zusammen.
- `logik/stempeluhr.py` macht aus Einstempeln, Pausen und Ausstempeln einen Zeiteintrag.
- `frontend/` ist die Oberfläche: `index.html`, `style.css` und `app.js`.
- `tests/` enthält die Tests für die Fachlogik und für `demo_laden.py`.
- `demo_laden.py` kopiert die Beispieldaten aus `daten_demo/` in den Datenordner.

Die Module bauen aufeinander auf. Unten stehen `zeit.py` und `modelle.py`, darauf `speicher.py`, darüber
`arbzg.py`, `gleitzeit.py` und `stempeluhr.py`. `app.py` benutzt sie alle.

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

## Beispieldaten

Auf Railway kommen die Beispieldaten so in den Dienst:

```
railway ssh --service wendezeit
WENDEZEIT_DATEN=/data /app/.venv/bin/python demo_laden.py
exit
```

Das Skript kopiert die Beispieldaten aus `daten_demo/` in den Datenordner. Vorhandene Einträge und
Abwesenheiten werden dabei überschrieben, Passwort und Einstellungen bleiben.

Damit die Demo zu jedem Zeitpunkt passt, werden die Daten um ganze Wochen verschoben, sodass sie bis
gestern reichen. Die Wochentage bleiben gleich, Urlaub und Krankheit wandern mit und `erfassung_ab` wird
auf den ersten Demotag gesetzt. Die Demo zeigt Warnungen und Verletzungen nach dem ArbZG und einen
absichtlich vergessenen Arbeitstag.

Feiertage wandern nicht mit. Landet ein Eintrag auf einem Feiertag, gibt das Skript einen Hinweis aus
(§ 9 ArbZG). Vor einer Präsentation die Demo deshalb am Vortag laden und einmal durchklicken.

## Für Entwickler

Zum Ausprobieren von Änderungen läuft Wendezeit auch lokal:

```
python -m pip install -r requirements.txt
python app.py
```

Danach http://localhost:5000 öffnen. Unter Windows reicht auch ein Doppelklick auf `start.bat`: Das Skript
legt beim ersten Start eine eigene Python-Umgebung im Ordner `.venv` an, installiert dort die Pakete,
startet Wendezeit und öffnet nach zwei Sekunden den Browser. Das Fenster muss offen bleiben, solange
Wendezeit läuft.

Die Daten liegen dann im Ordner `daten/`, Beispieldaten kommen mit `python demo_laden.py` hinein.

Die Tests laufen mit:

```
python -m unittest
```

## Branches

Wir arbeiten nach GitHub Flow:

- `main`: lauffähiger Stand, wird nie direkt bearbeitet
- `feature/...`: ein Branch je Aufgabe, zweigt von `main` ab und kommt per Pull Request zurück
- `fix/...`: genauso, nur für Fehlerkorrekturen
