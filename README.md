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
- [ ] Gleitzeit und Ampel
- [x] Stempeluhr
- [ ] Webserver und Railway
- [ ] Oberfläche
- [ ] Beispieldaten und Dokumentation

## Technik

- Python 3.10 oder neuer
- Flask als Webserver, auf Railway 
- Oberfläche mit HTML, CSS und JavaScript, sie holt ihre Daten als JSON vom Server
- Daten liegen als JSON-Dateien im Ordner `daten/`, auf Railway in einem Volume, damit sie einen neuen
  Deploy überstehen. Der Ordner wird nicht eingecheckt.
- keine Lizenzkosten: Flask ist Open Source (BSD- bzw. MIT-Lizenz)

Die Fachlogik (ArbZG, Gleitzeit, Stempeluhr) liegt in einem eigenen Ordner `logik/` und weiß nichts von
Flask. Eine spätere Mobile App kann dieselbe JSON-Schnittstelle nutzen wie die Weboberfläche.

## Installation

```
python -m pip install -r requirements.txt
```

Wie man das Programm lokal startet und auf Railway bringt, steht hier, sobald der Webserver drin ist.

## Branches

Wir arbeiten nach GitHub Flow:

- `main`: lauffähiger Stand, wird nie direkt bearbeitet
- `feature/...`: ein Branch je Aufgabe, zweigt von `main` ab und kommt per Pull Request zurück, nachdem jemand aus dem Team ihn gelesen hat
