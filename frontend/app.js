// Wendezeit – Oberfläche. Holt alle Daten vom Python-Server (Flask) und zeigt sie an.
// Rechnen passiert in Python. Hier wird nur formatiert und gezeichnet.

// Zustand der Oberfläche
const zustand = {
  seite: 'konto',            // konto | kalender | gesetz | einstellungen
  ansicht: 'kalender',       // kalender | tabelle
  filter: 'alle',            // alle | verletzung | warnung | abwesend | minus
  zeitraumArt: 'monat',      // monat | quartal | jahr  (Zeitraum-Filter im Kalender)
  jahr: 0,                   // z. B. 2026
  monatNr: 1,                // 1 bis 12
  quartal: 1,                // 1 bis 4
  gewaehlt: '',              // Datum im Popup
  daten: null,               // Antwort von /api/daten
  erststart: false,
  stempelHinweis: '',
  vorschauNummer: 0,         // zählt Vorschau-Anfragen, damit nur die neueste Antwort gilt
};

const MONATE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
const STATUS_NAME = { gruen: 'in Ordnung', orange: 'Warnung', rot: 'Verletzung' };
// Welche Meldung zu welchem Abschnitt auf der Seite "Arbeitszeitgesetz" führt
const GESETZ_ANKER = { '§ 3 ArbZG': 'gesetz-p3', '§ 4 ArbZG': 'gesetz-p4', '§ 5 ArbZG': 'gesetz-p5', '§ 6 ArbZG': 'gesetz-p6', '§ 9 ArbZG': 'gesetz-p9', '§ 11 ArbZG': 'gesetz-p11', 'Betrieb': 'gesetz-betrieb' };
// Pinnadel für den heutigen Tag im Kalender
const HEUTE_PIN = '<svg class="heute-pin" width="26" height="30" viewBox="0 0 26 30" aria-hidden="true"><line x1="13" y1="14" x2="13" y2="28" stroke="#3A3F4B" stroke-width="2.4" stroke-linecap="round"></line><circle cx="13" cy="9" r="7.5" fill="#C6372A"></circle><circle cx="10.5" cy="6.5" r="2.2" fill="#FFFFFF" opacity="0.6"></circle></svg>';
const AB_KLASSE = { 'Urlaub': 'urlaub', 'Krankheit': 'krankheit', 'Sonderurlaub': 'sonstige', 'Sonstige Abwesenheit': 'sonstige' };

// Server ansprechen
async function api(pfad, daten) {
  const optionen = daten ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(daten) } : {};
  // Fehler im Aufbau wie bei einem Fehler vom Server, dann zeigen die Aufrufer die Meldung wie gewohnt an
  let antwort;
  try {
    antwort = await fetch('/api' + pfad, optionen);
  } catch (fehler) {
    return { ok: false, fehler: 'Keine Verbindung zum Server. Bitte die Seite neu laden.' };
  }
  if (!antwort.ok) return { ok: false, fehler: 'Fehler auf dem Server (' + antwort.status + '). Bitte erneut versuchen.' };
  return antwort.json();
}

// Hilfsfunktionen zum Formatieren
const $ = (id) => document.getElementById(id);
// Zahl zweistellig, z. B. 7 wird 07
function zwei(n) { return String(n).padStart(2, '0'); }
// Minuten als Dauer, z. B. 465 wird 7:45 h
function dauer(min) { return Math.floor(min / 60) + ':' + zwei(min % 60) + ' h'; }
// Saldo mit Vorzeichen, z. B. +1:30 h oder −0:45 h
function saldoText(min) {
  const zeichen = min < 0 ? '−' : (min > 0 ? '+' : '±');
  const a = Math.abs(min);
  return zeichen + Math.floor(a / 60) + ':' + zwei(a % 60) + ' h';
}
// Datum von 2026-09-14 nach 14.09.2026
function datumText(iso) { const [j, m, t] = iso.split('-'); return t + '.' + m + '.' + j; }
// Uhrzeit eines Zeitpunkts, z. B. 08:05
function uhrText(datum) { const d = new Date(datum); return zwei(d.getHours()) + ':' + zwei(d.getMinutes()); }
// Sekunden als Stunden:Minuten:Sekunden für die Stempeluhr
function hms(sek) { sek = Math.max(0, Math.floor(sek)); return zwei(Math.floor(sek / 3600)) + ':' + zwei(Math.floor(sek / 60) % 60) + ':' + zwei(sek % 60); }
// Freier Text wie der Grund einer Abwesenheit kommt per innerHTML in die Seite. Ohne Maskieren
// würde z. B. <img onerror=...> als HTML ausgeführt
function maskiere(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
// Zahl mit einer Nachkommastelle und deutschem Komma
function komma(zahl) { return zahl.toFixed(1).replace('.', ','); }
// Element ein- oder ausblenden
function zeigen(el, sichtbar) { el.hidden = !sichtbar; }

// Daten laden und alles neu zeichnen
async function laden() {
  const z = zeitraum();
  const antwort = await api('/daten?von=' + z.von + '&bis=' + z.bis);
  if (antwort.ok === false) { alert(antwort.fehler); return; }
  zustand.daten = antwort;
  zeichneAlles();
}

// Erster Tag, letzter Tag und Beschriftung des gewählten Zeitraums
function zeitraum() {
  const j = zustand.jahr;
  const letzterTag = (m) => j + '-' + zwei(m) + '-' + zwei(new Date(j, m, 0).getDate());
  if (zustand.zeitraumArt === 'jahr') return { von: j + '-01-01', bis: j + '-12-31', text: 'Jahr ' + j };
  if (zustand.zeitraumArt === 'quartal') {
    const ersterMonat = (zustand.quartal - 1) * 3 + 1;
    return { von: j + '-' + zwei(ersterMonat) + '-01', bis: letzterTag(ersterMonat + 2), text: zustand.quartal + '. Quartal ' + j };
  }
  return { von: j + '-' + zwei(zustand.monatNr) + '-01', bis: letzterTag(zustand.monatNr), text: MONATE[zustand.monatNr - 1] + ' ' + j };
}

// Zeichnet alle Bereiche neu, nachdem neue Daten da sind
function zeichneAlles() {
  const d = zustand.daten;
  if (!d) return;
  zeichneSeitenleiste(d);
  zeichneKonto(d);
  zeichneFilter(d);
  zeichneStempeluhr(d);
  zeichneKalender(d);
  zeichneTabelle(d);
  zeichneEinstellungen(d);
  zeigeSeite();
}

// Blendet die gewählte Seite ein und die anderen aus
function zeigeSeite() {
  zeigen($('seite-konto'), zustand.seite === 'konto');
  zeigen($('seite-kalender'), zustand.seite === 'kalender');
  zeigen($('seite-gesetz'), zustand.seite === 'gesetz');
  zeigen($('seite-einstellungen'), zustand.seite === 'einstellungen');
  document.querySelectorAll('.nav').forEach(b => b.classList.toggle('aktiv', b.dataset.seite === zustand.seite));
  zeigen($('kalender-karte'), zustand.ansicht === 'kalender');
  zeigen($('tabelle-karte'), zustand.ansicht === 'tabelle');
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('aktiv', b.dataset.ansicht === zustand.ansicht));
  document.querySelectorAll('.chip').forEach(b => b.classList.toggle('aktiv', b.dataset.filter === zustand.filter));
  zeigen($('status-filter'), zustand.ansicht === 'tabelle');
}

// Seitenleiste
function zeichneSeitenleiste(d) {
  const name = d.einstellungen.name || 'Mitarbeiter';
  $('sb-name').textContent = name;
  $('sb-avatar').textContent = d.einstellungen.name ? initialen(name) : 'MA';
  $('sb-wochenstunden').textContent = d.einstellungen.wochenstunden + ' h/Woche';
}

// "Jason Reich" -> "JR", "Mitarbeiter" -> "MI"
function initialen(name) {
  const teile = name.trim().split(/\s+/);
  if (teile.length >= 2) return (teile[0][0] + teile[teile.length - 1][0]).toUpperCase();
  return name.trim().slice(0, 2).toUpperCase();
}
// Farbwert zur Ampelfarbe
function ampelFarbe(farbe) { return { gruen: '#3E9B6B', orange: '#E08A2E', rot: '#C6372A' }[farbe]; }

// Stundenkonto
function zeichneKonto(d) {
  const a = d.konto.ampel;
  $('konto-zahl').textContent = saldoText(d.konto.minuten);
  $('konto-meldungen').innerHTML = d.durchschnitt.map(m => meldungKnopf(m, true)).join('');
  zeigen($('konto-meldungen'), d.durchschnitt.length > 0);
  $('licht-rot').classList.toggle('an', a.farbe === 'rot');
  $('licht-orange').classList.toggle('an', a.farbe === 'orange');
  $('licht-gruen').classList.toggle('an', a.farbe === 'gruen');
  $('ampel-name').textContent = a.text;
  $('ampel-hinweis').textContent = a.hinweis;
  $('ampel-balken').style.width = a.prozent + '%';
  $('ampel-balken').style.background = ampelFarbe(a.farbe);
  $('ampel-rest').textContent = a.rest;
}

// Zeitraum-Filter und Gleitzeit oben rechts im Kalender
function zeichneFilter(d) {
  $('monat-titel').textContent = zeitraum().text;
  $('zeitraum-gleitzeit').textContent = saldoText(d.zeitraum_minuten);
  document.querySelectorAll('.zeitraum-tab').forEach(b => b.classList.toggle('aktiv', b.dataset.art === zustand.zeitraumArt));
  zeigen($('filter-monat-feld'), zustand.zeitraumArt === 'monat');
  zeigen($('filter-quartal-feld'), zustand.zeitraumArt === 'quartal');
  $('filter-jahr').value = zustand.jahr;
  $('filter-monat').value = zustand.monatNr;
  $('filter-quartal').value = zustand.quartal;
}

// Füllt die Jahresauswahl im Kalender
function jahreEintragen() {
  // Auswahl: zehn Jahre zurück bis fünf Jahre voraus
  const aktuell = new Date().getFullYear();
  const html = [];
  for (let j = aktuell - 10; j <= aktuell + 5; j++) html.push('<option value="' + j + '">' + j + '</option>');
  $('filter-jahr').innerHTML = html.join('');
}

// Stempeluhr (läuft jede Sekunde)
function zeichneStempeluhr(d) {
  const st = d.stempel;
  const jetzt = new Date();
  const heute = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'][jetzt.getDay()] + ', ' + datumText(d.heute);
  $('heute-text').textContent = heute;
  $('uhrzeit').textContent = zwei(jetzt.getHours()) + ':' + zwei(jetzt.getMinutes()) + ':' + zwei(jetzt.getSeconds());

  // Gearbeitete Sekunden und Pausensekunden aus den Zeitstempeln rechnen
  let pauseSek = 0, arbeitSek = 0;
  if (st.status !== 'aus') {
    zaehlendePausen(st, jetzt).forEach(p => { pauseSek += p.sek; });
    arbeitSek = (jetzt - new Date(st.beginn)) / 1000 - pauseSek;
  }
  const punkt = $('stempel-punkt');
  punkt.className = 'punkt ' + (st.status === 'aus' ? '' : st.status);
  let text = d.heute_hat_eintrag ? 'Heute bereits ausgestempelt' : 'Nicht eingestempelt';
  if (st.status === 'arbeitet') text = 'Eingestempelt seit ' + uhrText(st.beginn);
  if (st.status === 'pause') text = 'Pause seit ' + uhrText(st.pausen[st.pausen.length - 1].von);
  $('stempel-status-text').textContent = text;
  $('stempel-beginn').textContent = st.status === 'aus' ? '–' : uhrText(st.beginn);
  $('stempel-gearbeitet').textContent = hms(arbeitSek);
  $('stempel-pause').textContent = hms(pauseSek);
  zeigen($('btn-einstempeln'), st.status === 'aus');
  zeigen($('btn-pause-start'), st.status === 'arbeitet');
  zeigen($('btn-pause-ende'), st.status === 'pause');
  zeigen($('btn-ausstempeln'), st.status !== 'aus');
  $('stempel-hinweis').textContent = zustand.stempelHinweis;
  zeigen($('stempel-hinweis'), zustand.stempelHinweis !== '');

  const warnungen = st.status === 'aus' ? [] : stempelWarnungen(st, jetzt);
  const rot = warnungen.some(w => w.rot);
  $('stempel-warnung').className = 'meldung ' + (rot ? 'verletzung' : 'warnung');
  $('stempel-warnung').innerHTML = warnungen.map(w => w.text).join('<br>');
  zeigen($('stempel-warnung'), warnungen.length > 0);
}

// Wie in stempeluhr.py zählen nur Pausen ab 15 min, kürzere sind Arbeitszeit. Die laufende Pause zählt mit.
// Die 15 min werden wie dort auf ganze Minuten gerechnet (Sekunden abgeschnitten)
function zaehlendePausen(st, jetzt) {
  const liste = [];
  st.pausen.forEach(p => {
    const sek = ((p.bis ? new Date(p.bis) : jetzt) - new Date(p.von)) / 1000;
    const ganzeMinuten = p.bis ? Math.floor(new Date(p.bis) / 60000) - Math.floor(new Date(p.von) / 60000) : 0;
    if (!p.bis || ganzeMinuten >= 15) liste.push({ von: p.von, bis: p.bis, sek: sek });
  });
  return liste;
}

// Warnt schon während der Arbeit, bevor beim Ausstempeln eine Verletzung entsteht.
// Die Grenzen sind dieselben wie in logik/arbzg.py, bei einer Änderung beide Stellen anpassen.
function stempelWarnungen(st, jetzt) {
  const warnungen = [];
  const zaehlende = zaehlendePausen(st, jetzt);
  let pause = 0;
  zaehlende.forEach(p => { pause += p.sek / 60; });
  const arbeit = (jetzt - new Date(st.beginn)) / 60000 - pause;
  if (arbeit > 600) warnungen.push({ rot: true, text: '§ 3 ArbZG: Über 10 Stunden gearbeitet. Bitte jetzt ausstempeln.' });
  else if (arbeit > 480) warnungen.push({ rot: false, text: '§ 3 ArbZG: Über 8 Stunden gearbeitet, erlaubt sind höchstens 10.' });

  // Pflichtpause wie in pruefe_pause: über 6 h 30 min, über 9 h 45 min, Warnung 30 min vorher
  const pflicht = arbeit > 540 ? 45 : arbeit > 360 ? 30 : 0;
  const bald = arbeit > 510 ? 45 : arbeit > 330 ? 30 : 0;
  if (pause < pflicht) warnungen.push({ rot: true, text: '§ 4 ArbZG: Pause zu kurz, nötig sind ' + pflicht + ' min.' });
  else if (pause < bald) warnungen.push({ rot: false, text: '§ 4 ArbZG: Bald sind ' + bald + ' min Pause nötig, bisher ' + Math.floor(pause) + ' min.' });

  // Jedes Stück zwischen zwei zählenden Pausen zählt einzeln, wie in laengste_zeit_ohne_pause. Ohne Pause
  // meldet das schon die Prüfung oben, sonst käme § 4 doppelt (wie in pruefe_pause_am_stueck)
  if (zaehlende.length > 0) {
    let laengste = 0, stueckAb = new Date(st.beginn);
    zaehlende.forEach(p => {
      laengste = Math.max(laengste, (new Date(p.von) - stueckAb) / 60000);
      stueckAb = p.bis ? new Date(p.bis) : null;
    });
    // Das laufende Stück seit der letzten Pause (nicht während einer Pause)
    const aktuell = stueckAb ? (jetzt - stueckAb) / 60000 : 0;
    if (Math.max(laengste, aktuell) > 360) warnungen.push({ rot: true, text: '§ 4 ArbZG: Über 6 Stunden am Stück ohne Pause.' });
    else if (aktuell > 330) warnungen.push({ rot: false, text: '§ 4 ArbZG: Seit ' + dauer(Math.floor(aktuell)) + ' ohne Pause, nach 6 Stunden ist eine Pause Pflicht.' });
  }
  return warnungen;
}

// Kalender (ein Monatsraster je Monat im Zeitraum)
function zeichneKalender(d) {
  const monate = [];
  d.tage.forEach(t => {
    const schluessel = t.datum.slice(0, 7);
    if (monate.length === 0 || monate[monate.length - 1].schluessel !== schluessel) monate.push({ schluessel, tage: [] });
    monate[monate.length - 1].tage.push(t);
  });
  $('kalender-monate').innerHTML = monate.map(m => monatRaster(m, d, monate.length > 1)).join('');
}

// Ein Monat als Raster, die Woche beginnt am Montag
function monatRaster(m, d, mitTitel) {
  const [jahr, mon] = m.schluessel.split('-').map(Number);
  const fuehrend = (new Date(jahr, mon - 1, 1).getDay() + 6) % 7;   // Montag = 0
  const html = [];
  for (let i = 0; i < fuehrend; i++) html.push('<button class="tag leer"></button>');
  m.tage.forEach(t => html.push(tagKachel(t, d)));
  return '<div class="kalender-monat">'
    + (mitTitel ? '<h3 class="kalender-monat-titel">' + MONATE[mon - 1] + ' ' + jahr + '</h3>' : '')
    + '<div class="wochentage"><span>Mo</span><span>Di</span><span>Mi</span><span>Do</span><span>Fr</span><span class="grau">Sa</span><span class="grau">So</span></div>'
    + '<div class="tage">' + html.join('') + '</div></div>';
}

// Eine Kachel im Kalender mit Farbe, Stunden und Uhrzeit
function tagKachel(t, d) {
  let klasse = '', z1 = '', z2 = '';
  if (t.eintrag) { klasse = t.status; z1 = komma(t.ist / 60) + ' h'; z2 = t.eintrag.beginn + ' bis ' + t.eintrag.ende; }
  else if (t.feiertag) { klasse = 'feiertag'; z1 = 'Feiertag'; z2 = t.feiertag; }
  else if (t.abwesenheit) { klasse = AB_KLASSE[t.abwesenheit.art]; z1 = t.abwesenheit.art; z2 = maskiere(t.abwesenheit.grund || ''); }
  else if (t.wochenende) { klasse = 'wochenende'; }
  else if (t.fehlt) { z1 = 'kein Eintrag'; z2 = saldoText(t.saldo); }
  if (t.datum === d.heute) klasse += ' heute';
  if (t.datum === zustand.gewaehlt && !$('popup').hidden) klasse += ' gewaehlt';
  const nr = Number(t.datum.slice(8));
  const pin = t.datum === d.heute ? HEUTE_PIN : '';
  return '<button class="tag ' + klasse + '" data-datum="' + t.datum + '"' + (pin ? ' aria-label="Heute, ' + datumText(t.datum) + '"' : '') + '>' + pin + '<span class="tag-nr">' + nr + '</span><span class="tag-text"><span class="tag-z1">' + z1 + '</span><span class="tag-z2">' + z2 + '</span></span></button>';
}

// Tabelle
function zeichneTabelle(d) {
  const zeilen = [];
  d.tage.forEach(t => {
    let typ = '', saldoMin = 0;
    if (t.eintrag) { typ = t.status; saldoMin = t.saldo; }
    else if (t.abwesenheit && !t.wochenende && !t.feiertag) { typ = 'abwesend'; }
    else if (t.fehlt) { typ = 'fehlt'; saldoMin = t.saldo; }
    else return;

    const f = zustand.filter;
    const passt = f === 'alle' || (f === 'verletzung' && typ === 'rot') || (f === 'warnung' && typ === 'orange') || (f === 'abwesend' && typ === 'abwesend') || (f === 'minus' && saldoMin < 0);
    if (!passt) return;

    const statusText = typ === 'abwesend' ? t.abwesenheit.art : (typ === 'fehlt' ? 'kein Eintrag' : STATUS_NAME[typ]);
    const saldoKlasse = saldoMin < 0 ? 'minus' : (typ === 'abwesend' ? 'null' : 'plus');
    zeilen.push('<button class="tab-zeile" data-datum="' + t.datum + '">'
      + '<span class="tab-datum"><b>' + datumText(t.datum) + '</b><small>' + t.wochentag + '</small></span>'
      + '<span><span class="pille ' + typ + '">' + statusText + '</span></span>'
      + '<span>' + (t.eintrag ? t.eintrag.beginn : '') + '</span><span>' + (t.eintrag ? t.eintrag.ende : '') + '</span>'
      + '<span>' + (t.eintrag ? t.eintrag.pause + ' min' : '') + '</span>'
      + '<span style="font-weight:500">' + (t.eintrag ? dauer(t.ist) : (typ === 'abwesend' ? maskiere(t.abwesenheit.grund || '') : '0:00 h')) + '</span>'
      + '<span class="saldo ' + saldoKlasse + '">' + saldoText(saldoMin) + '</span></button>');
  });
  $('tabelle-zeilen').innerHTML = zeilen.join('');
  $('tabelle-leer').textContent = 'Keine Tage für diesen Filter im Zeitraum ' + zeitraum().text + '.';
  zeigen($('tabelle-leer'), zeilen.length === 0);
}

// Einstellungen
function zeichneEinstellungen(d) {
  const e = d.einstellungen;
  $('soll-tag-text').textContent = dauer(e.wochenstunden * 60 / 5);
  document.querySelectorAll('.modell-btn').forEach(b => b.classList.toggle('aktiv', Number(b.dataset.stunden) === e.wochenstunden));
  if (document.activeElement !== $('grenze-orange')) $('grenze-orange').value = e.ampel_orange_stunden;
  if (document.activeElement !== $('grenze-rot')) $('grenze-rot').value = e.ampel_rot_stunden;
  if (document.activeElement !== $('grenze-minus-orange')) $('grenze-minus-orange').value = e.ampel_minus_orange_stunden;
  if (document.activeElement !== $('grenze-minus-rot')) $('grenze-minus-rot').value = e.ampel_minus_rot_stunden;
  if (document.activeElement !== $('erfassung-ab')) $('erfassung-ab').value = e.erfassung_ab || '';
  if (document.activeElement !== $('name-eingabe')) $('name-eingabe').value = e.name || '';
  zeichneGrenzenBalken(e);
}

// Balken von Rot (Minus) über Grün bis Rot (Plus): feste Breiten, nur die Beschriftung kommt aus den Einstellungen
function zeichneGrenzenBalken(e) {
  $('gb-text-minus-rot').textContent = '−' + e.ampel_minus_rot_stunden + ' h';
  $('gb-text-minus-orange').textContent = '−' + e.ampel_minus_orange_stunden + ' h';
  $('gb-text-orange').textContent = '+' + e.ampel_orange_stunden + ' h';
  $('gb-text-rot').textContent = '+' + e.ampel_rot_stunden + ' h';
}

// Popup für einen Tag
function tagFinden(datum) { return zustand.daten.tage.find(t => t.datum === datum); }

// Öffnet das Tagesfenster und füllt das Formular mit dem gespeicherten Eintrag
function popupOeffnen(datum) {
  zustand.gewaehlt = datum;
  const t = tagFinden(datum);
  $('f-beginn').value = t.eintrag ? t.eintrag.beginn : '08:00';
  $('f-ende').value = t.eintrag ? t.eintrag.ende : '17:00';
  // Neuer Tag: 30 min ab 12 Uhr vorschlagen. Die erste Pause steht oben, weitere darunter
  const pausen = t.eintrag ? t.eintrag.pausen : [{ ab: '12:00', minuten: 30 }];
  $('f-pause').value = pausen.length > 0 ? pausen[0].minuten : 0;
  $('f-pause-ab').value = pausen.length > 0 ? pausen[0].ab : '';
  $('weitere-pausen').innerHTML = '';
  pausen.slice(1).forEach(p => pauseZeileDazu(p.minuten, p.ab));
  zeigen($('eintrag-fehler'), false);
  zeigen($('ab-fehler'), false);
  $('ab-bis').value = datum;
  $('ab-grund').value = '';
  zeigen($('popup'), true);
  zeichnePopup();
  zeichneKalender(zustand.daten);
}

// Schließt das Tagesfenster
function popupSchliessen() {
  zeigen($('popup'), false);
  zeichneKalender(zustand.daten);
}

// Zeichnet das Tagesfenster: Eintrag, Abwesenheit und Vorschau
async function zeichnePopup() {
  const t = tagFinden(zustand.gewaehlt);
  const arbeitstag = !t.feiertag && !(t.abwesenheit && !t.eintrag);
  $('tag-wochentag').textContent = t.wochentag;
  $('tag-datum').textContent = datumText(t.datum);
  $('ab-ab-datum').textContent = datumText(t.datum);

  zeigen($('tag-feiertag'), !!t.feiertag);
  $('tag-feiertag').textContent = 'Gesetzlicher Feiertag: ' + t.feiertag + '. Keine Sollzeit an diesem Tag.';
  zeigen($('tag-abwesend'), !!t.abwesenheit && !t.eintrag);
  if (t.abwesenheit) {
    const a = t.abwesenheit;
    $('tag-abwesend-text').textContent = a.art + (a.grund ? ' (' + a.grund + ')' : '') + (a.von !== a.bis ? ' vom ' + datumText(a.von) + ' bis ' + datumText(a.bis) : '');
  }
  zeigen($('tag-arbeit'), arbeitstag);
  zeigen($('abwesenheit-form'), !t.feiertag && !t.abwesenheit && !t.eintrag && !t.wochenende);
  zeigen($('btn-loeschen'), !!t.eintrag);
  $('form-titel').textContent = t.eintrag ? 'Eintrag bearbeiten' : 'Arbeitszeit eintragen';
  $('btn-speichern').textContent = t.eintrag ? 'Änderung speichern' : 'Eintrag speichern';
  $('tag-soll').textContent = dauer(t.soll);
  $('tag-soll-2').textContent = dauer(t.soll);
  $('tag-soll-marke').style.left = Math.min(100, t.soll / 600 * 100) + '%';

  const status = $('tag-status');
  if (!arbeitstag) {
    status.className = 'status-pille lila';
    status.textContent = t.feiertag ? 'Feiertag' : t.abwesenheit.art;
    return;
  }

  // Live-Vorschau: Python rechnet mit den gerade eingetippten Werten
  const eingabe = formularWerte();
  if (!eingabe) { vorschauLeeren('keine Eingabe'); zeigen($('eintrag-fehler'), false); return; }
  const nummer = ++zustand.vorschauNummer;
  const v = await api('/vorschau', eingabe);
  // Eine ältere Antwort darf eine neuere nicht überschreiben
  if (nummer !== zustand.vorschauNummer) return;
  zeigen($('eintrag-fehler'), v.ok === false);
  if (v.ok === false) {
    $('eintrag-fehler').textContent = v.fehler;
    vorschauLeeren('Eingabe prüfen');
    return;
  }
  status.className = 'status-pille ' + v.status;
  status.textContent = (t.eintrag ? '' : 'Vorschau: ') + STATUS_NAME[v.status];
  $('tag-ist').textContent = dauer(v.ist);
  $('tag-saldo').textContent = saldoText(v.saldo);
  $('tag-saldo').style.color = v.saldo < 0 ? '#8A2A1F' : '#1F5E3C';
  $('tag-balken').style.width = Math.min(100, v.ist / 600 * 100) + '%';
  $('tag-balken').className = 'tag-balken ' + v.status;
  const html = v.meldungen.map(m => meldungKnopf(m, true));
  $('tag-meldungen').innerHTML = html.join('');
  zeigen($('tag-meldungen'), html.length > 0);
}

// Setzt die Vorschau im Tagesfenster zurück, z. B. bei einer ungültigen Eingabe
function vorschauLeeren(text) {
  const status = $('tag-status');
  status.className = 'status-pille'; status.textContent = text;
  $('tag-ist').textContent = '0:00 h'; $('tag-saldo').textContent = '±0:00 h'; $('tag-saldo').style.color = '#1F5E3C';
  $('tag-balken').style.width = '0%'; $('tag-balken').className = 'tag-balken';
  zeigen($('tag-meldungen'), false);
}

// Weitere Pause unter der ersten. Nur Zahlen und Uhrzeiten, deshalb ist innerHTML hier unbedenklich
function pauseZeileDazu(minuten, ab) {
  const zeile = document.createElement('div');
  zeile.className = 'grid-4 pause-zeile';
  zeile.innerHTML = '<span></span>'
    + '<button type="button" class="btn-sekundaer pause-entfernen">Entfernen</button>'
    + '<label>Pause (min)<input class="w-pause" type="number" min="0" step="5"></label>'
    + '<label>Pause ab<input class="w-pause-ab" type="time"></label>';
  zeile.querySelector('.w-pause').value = minuten;
  zeile.querySelector('.w-pause-ab').value = ab;
  $('weitere-pausen').appendChild(zeile);
}

// Liest Beginn, Ende und Pausen aus dem Formular. Gibt null zurück, wenn etwas fehlt
function formularWerte() {
  const beginn = $('f-beginn').value, ende = $('f-ende').value;
  // Ende vor Beginn ist erlaubt: dann endet die Schicht am nächsten Tag
  if (!beginn || !ende || beginn === ende) return null;
  const pausen = [{ minuten: Number($('f-pause').value) || 0, ab: $('f-pause-ab').value }];
  document.querySelectorAll('.pause-zeile').forEach(z => {
    pausen.push({ minuten: Number(z.querySelector('.w-pause').value) || 0, ab: z.querySelector('.w-pause-ab').value });
  });
  // Pausen mit 0 Minuten zählen nicht, ihr Beginn ist egal
  return { datum: zustand.gewaehlt, beginn, ende, pausen: pausen.filter(p => p.minuten !== 0) };
}

// Warn-Popup bei grober Verletzung (nur rot, Warnungen bleiben im Tages-Popup)
function zeigeVerletzung(antwort) {
  if (!antwort || !antwort.verletzungen || antwort.verletzungen.length === 0) return;
  $('verletzung-datum').textContent = datumText(antwort.datum);
  $('verletzung-liste').innerHTML = antwort.verletzungen.map(m => meldungKnopf(m, false)).join('');
  zeigen($('verletzung-popup'), true);
  $('verletzung-ok').focus();
}

// Meldungen führen zum passenden Abschnitt im Arbeitszeitgesetz
function meldungKnopf(m, mitArt) {
  const kopf = (mitArt ? m.art + ' · ' : '') + m.paragraph;
  return '<button type="button" class="meldung ' + m.art.toLowerCase() + '" data-anker="' + (GESETZ_ANKER[m.paragraph] || '') + '">'
    + '<b>' + maskiere(kopf) + '</b><span>' + maskiere(m.text) + '</span><span class="meldung-link">Zum Gesetzestext ›</span></button>';
}

// Wechselt zur Seite Arbeitszeitgesetz und hebt den Abschnitt kurz hervor
function zeigeGesetz(anker) {
  if (!$('popup').hidden) popupSchliessen();
  zeigen($('verletzung-popup'), false);
  zustand.seite = 'gesetz';
  zeigeSeite();
  const ziel = $(anker);
  if (!ziel) return;
  ziel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  // Abschnitt kurz aufleuchten lassen
  ziel.classList.remove('hervorgehoben');
  void ziel.offsetWidth;
  ziel.classList.add('hervorgehoben');
}

// Klick auf eine Meldung führt zum passenden Gesetzestext
function gesetzKlick(ev) {
  const knopf = ev.target.closest('[data-anker]');
  if (knopf && knopf.dataset.anker) zeigeGesetz(knopf.dataset.anker);
}

// Login
function zeichneLogin() {
  $('login-titel').textContent = zustand.erststart ? 'Willkommen, bitte Passwort festlegen' : 'Anmelden';
  $('login-text').textContent = zustand.erststart ? 'Beim ersten Start legen Sie ein persönliches Passwort fest. Sie können es später in den Einstellungen ändern.' : 'Bitte geben Sie Ihr Passwort ein.';
  $('login-button').textContent = zustand.erststart ? 'Passwort speichern und starten' : 'Anmelden';
  zeigen($('pw2-label'), zustand.erststart);
  zeigen($('login-fehler'), false);
}

// Nach dem Login: Seitenleiste zeigen, Zeitraum auf den aktuellen Monat setzen, Daten laden
async function nachLogin() {
  zeigen($('login'), false);
  zeigen($('seitenleiste'), true);
  // Zeitraum-Filter starten beim aktuellen Monat
  const heute = new Date();
  zustand.jahr = heute.getFullYear();
  zustand.monatNr = heute.getMonth() + 1;
  zustand.quartal = Math.floor(heute.getMonth() / 3) + 1;
  jahreEintragen();
  await laden();
}

// Beim Öffnen der Seite: angemeldet, erster Start oder Login?
async function start() {
  const s = await api('/status');
  zustand.erststart = s.erststart;
  if (s.eingeloggt) { await nachLogin(); } else { zeichneLogin(); }
}

// Klicks und Eingaben verbinden
$('login-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const antwort = zustand.erststart
    ? await api('/passwort-setzen', { passwort: $('pw1').value, wiederholung: $('pw2').value })
    : await api('/login', { passwort: $('pw1').value });
  if (!antwort.ok) { $('login-fehler').textContent = antwort.fehler; zeigen($('login-fehler'), true); return; }
  $('pw1').value = ''; $('pw2').value = '';
  zustand.erststart = false;
  nachLogin();
});
$('btn-abmelden').addEventListener('click', async () => {
  await api('/logout', {});
  zeigen($('seitenleiste'), false);
  ['seite-konto', 'seite-kalender', 'seite-gesetz', 'seite-einstellungen', 'popup', 'verletzung-popup'].forEach(id => zeigen($(id), false));
  zeichneLogin();
  zeigen($('login'), true);
});
document.querySelectorAll('.nav').forEach(b => b.addEventListener('click', () => { zustand.seite = b.dataset.seite; zeigeSeite(); window.scrollTo(0, 0); }));
// Name unten links: zu den Einstellungen
$('nutzer-knopf').addEventListener('click', () => { zustand.seite = 'einstellungen'; zeigeSeite(); window.scrollTo(0, 0); });
// Logo oben links: immer zur Startseite (Stundenkonto)
$('marke-start').addEventListener('click', () => { zustand.seite = 'konto'; zeigeSeite(); window.scrollTo(0, 0); });
$('tag-meldungen').addEventListener('click', gesetzKlick);
$('konto-meldungen').addEventListener('click', gesetzKlick);
$('verletzung-liste').addEventListener('click', gesetzKlick);
document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { zustand.ansicht = b.dataset.ansicht; zeigeSeite(); }));
$('verletzung-ok').addEventListener('click', () => zeigen($('verletzung-popup'), false));
document.querySelectorAll('.chip').forEach(b => b.addEventListener('click', () => { zustand.filter = b.dataset.filter; zeichneTabelle(zustand.daten); zeigeSeite(); }));

// Zeitraum-Filter: Art wählen, Jahr / Monat / Quartal wählen
document.querySelectorAll('.zeitraum-tab').forEach(b => b.addEventListener('click', () => { zustand.zeitraumArt = b.dataset.art; laden(); }));
$('filter-jahr').addEventListener('change', () => { zustand.jahr = Number($('filter-jahr').value); laden(); });
$('filter-monat').addEventListener('change', () => {
  zustand.monatNr = Number($('filter-monat').value);
  zustand.quartal = Math.floor((zustand.monatNr - 1) / 3) + 1;
  laden();
});
$('filter-quartal').addEventListener('change', () => {
  zustand.quartal = Number($('filter-quartal').value);
  zustand.monatNr = (zustand.quartal - 1) * 3 + 1;
  laden();
});

// Pfeile: einen Monat, ein Quartal oder ein Jahr weiter bzw. zurück
function zeitraumWechseln(schritt) {
  if (zustand.zeitraumArt === 'jahr') {
    zustand.jahr += schritt;
  } else if (zustand.zeitraumArt === 'quartal') {
    zustand.quartal += schritt;
    if (zustand.quartal < 1) { zustand.quartal = 4; zustand.jahr -= 1; }
    if (zustand.quartal > 4) { zustand.quartal = 1; zustand.jahr += 1; }
    zustand.monatNr = (zustand.quartal - 1) * 3 + 1;
  } else {
    zustand.monatNr += schritt;
    if (zustand.monatNr < 1) { zustand.monatNr = 12; zustand.jahr -= 1; }
    if (zustand.monatNr > 12) { zustand.monatNr = 1; zustand.jahr += 1; }
    zustand.quartal = Math.floor((zustand.monatNr - 1) / 3) + 1;
  }
  jahrSicherstellen();
  laden();
}
$('monat-zurueck').addEventListener('click', () => zeitraumWechseln(-1));
$('monat-vor').addEventListener('click', () => zeitraumWechseln(1));

// Springen die Pfeile aus der Jahresliste heraus, wird das Jahr ergänzt
function jahrSicherstellen() {
  if (!$('filter-jahr').querySelector('option[value="' + zustand.jahr + '"]')) {
    $('filter-jahr').insertAdjacentHTML('beforeend', '<option value="' + zustand.jahr + '">' + zustand.jahr + '</option>');
  }
}

// Klick auf einen Tag (Kalender oder Tabelle) öffnet das Popup
$('kalender-monate').addEventListener('click', (ev) => { const b = ev.target.closest('.tag'); if (b && b.dataset.datum) popupOeffnen(b.dataset.datum); });
$('tabelle-zeilen').addEventListener('click', (ev) => { const b = ev.target.closest('.tab-zeile'); if (b) popupOeffnen(b.dataset.datum); });
$('popup-schliessen').addEventListener('click', popupSchliessen);
$('popup').addEventListener('click', (ev) => { if (ev.target === $('popup')) popupSchliessen(); });
['f-beginn', 'f-ende', 'f-pause', 'f-pause-ab', 'weitere-pausen'].forEach(id => $(id).addEventListener('input', zeichnePopup));
$('btn-pause-dazu').addEventListener('click', () => { pauseZeileDazu(15, ''); zeichnePopup(); });
$('weitere-pausen').addEventListener('click', (ev) => {
  const knopf = ev.target.closest('.pause-entfernen');
  if (!knopf) return;
  knopf.closest('.pause-zeile').remove();
  zeichnePopup();
});

$('eintrag-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const werte = formularWerte();
  if (!werte) return;
  const antwort = await api('/eintrag', werte);
  if (!antwort.ok) { $('eintrag-fehler').textContent = antwort.fehler; zeigen($('eintrag-fehler'), true); return; }
  popupSchliessen();
  await laden();
  zeigeVerletzung(antwort);
});
$('btn-loeschen').addEventListener('click', async () => {
  const antwort = await api('/eintrag-loeschen', { datum: zustand.gewaehlt });
  if (!antwort.ok) { $('eintrag-fehler').textContent = antwort.fehler; zeigen($('eintrag-fehler'), true); return; }
  popupSchliessen();
  laden();
});
$('ab-art').addEventListener('change', () => zeigen($('ab-grund-label'), $('ab-art').value === 'Sonstige Abwesenheit'));
$('abwesenheit-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const bis = $('ab-bis').value >= zustand.gewaehlt ? $('ab-bis').value : zustand.gewaehlt;
  const art = $('ab-art').value;
  const antwort = await api('/abwesenheit', { von: zustand.gewaehlt, bis, art, grund: art === 'Sonstige Abwesenheit' ? $('ab-grund').value : '' });
  if (!antwort.ok) { $('ab-fehler').textContent = antwort.fehler; zeigen($('ab-fehler'), true); return; }
  popupSchliessen();
  laden();
});
$('btn-abwesenheit-entfernen').addEventListener('click', async () => {
  const t = tagFinden(zustand.gewaehlt);
  const antwort = await api('/abwesenheit-loeschen', { von: t.abwesenheit.von });
  if (!antwort.ok) { $('ab-fehler').textContent = antwort.fehler; zeigen($('ab-fehler'), true); return; }
  popupSchliessen();
  laden();
});

// Stempeluhr
async function stempeln(aktion) {
  const antwort = await api('/stempel', { aktion });
  zustand.stempelHinweis = antwort.hinweis || '';
  let klasse = 'meldung-info';
  if (antwort.ok === false) klasse = 'meldung-fehler';
  else if (antwort.warnung) klasse = 'meldung warnung';
  $('stempel-hinweis').className = klasse;
  await laden();
  zeigeVerletzung(antwort);
}
$('btn-einstempeln').addEventListener('click', () => stempeln('einstempeln'));
$('btn-pause-start').addEventListener('click', () => stempeln('pause_start'));
$('btn-pause-ende').addEventListener('click', () => stempeln('pause_ende'));
$('btn-ausstempeln').addEventListener('click', () => stempeln('ausstempeln'));
setInterval(() => { if (zustand.daten && zustand.seite === 'konto') zeichneStempeluhr(zustand.daten); }, 1000);

// Einstellungen
async function einstellungenSpeichern(aenderung) {
  const e = Object.assign({}, zustand.daten.einstellungen, aenderung);
  const antwort = await api('/einstellungen', {
    wochenstunden: e.wochenstunden, ampel_orange_stunden: e.ampel_orange_stunden, ampel_rot_stunden: e.ampel_rot_stunden,
    ampel_minus_orange_stunden: e.ampel_minus_orange_stunden, ampel_minus_rot_stunden: e.ampel_minus_rot_stunden, erfassung_ab: e.erfassung_ab,
    name: e.name || '',
  });
  $('einstellungen-meldung').textContent = antwort.ok ? '' : antwort.fehler;
  zeigen($('einstellungen-meldung'), !antwort.ok);
  laden();
}
document.querySelectorAll('.modell-btn').forEach(b => b.addEventListener('click', () => einstellungenSpeichern({ wochenstunden: Number(b.dataset.stunden) })));
$('grenze-orange').addEventListener('change', () => einstellungenSpeichern({ ampel_orange_stunden: Number($('grenze-orange').value) }));
$('grenze-rot').addEventListener('change', () => einstellungenSpeichern({ ampel_rot_stunden: Number($('grenze-rot').value) }));
$('grenze-minus-orange').addEventListener('change', () => einstellungenSpeichern({ ampel_minus_orange_stunden: Number($('grenze-minus-orange').value) }));
$('grenze-minus-rot').addEventListener('change', () => einstellungenSpeichern({ ampel_minus_rot_stunden: Number($('grenze-minus-rot').value) }));
$('name-eingabe').addEventListener('change', () => einstellungenSpeichern({ name: $('name-eingabe').value }));
$('erfassung-ab').addEventListener('change', () => einstellungenSpeichern({ erfassung_ab: $('erfassung-ab').value }));
$('pw-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const antwort = await api('/passwort-aendern', { alt: $('pw-alt').value, neu: $('pw-neu').value });
  const m = $('pw-meldung');
  m.className = antwort.ok ? 'meldung-ok' : 'meldung-fehler';
  m.textContent = antwort.ok ? 'Passwort wurde geändert.' : antwort.fehler;
  zeigen(m, true);
  if (antwort.ok) { $('pw-alt').value = ''; $('pw-neu').value = ''; }
});

start();
