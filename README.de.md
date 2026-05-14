# Epson EcoTank Statistics für Home Assistant

[English](README.md) · 🌐 **Deutsch**

Eine Custom-Integration für Home Assistant, die das eingebettete Web-Interface
von Epson-EcoTank-Druckern ausliest und Daten verfügbar macht, die **keine
andere Integration** (IPP, SNMP, mDNS) liefert:

- Gesamtseitenzahl (insgesamt, S/W, Farbe, einseitig, beidseitig)
- Seitenzahlen nach Funktion (Kopie, Fax, Scan, Druck – S/W und Farbe)
- Tintenstände für K / C / M / Y
- Druckerstatus, Erstdruckdatum, Firmware, Epson-Connect-Status

Die Integration **hängt sich an das bestehende, per IPP erkannte Druckergerät
in der Geräteregistry**, sodass alle Sensoren unter dem Drucker auftauchen,
den du bereits kennst – kein doppelter Geräteeintrag.

> Referenzmodell während der Entwicklung: **Epson ET-2750 Series**. Andere
> Epson-Familien mit derselben `/PRESENTATION/ADVANCED/...`-Web-UI sollten
> direkt funktionieren.

## Features

- Auto-Discovery via Zeroconf (`_ipp._tcp.local.` / `_ipps._tcp.local.`) –
  der Drucker erscheint unter *Einstellungen → Geräte & Dienste → Erkannt*,
  sobald Home Assistant einen Epson-IPP-Drucker im Netzwerk sieht.
- Automatisches Mergen mit dem Geräteeintrag der Core-IPP-Integration. Der
  Identifier (`("ipp", <printer-uuid>)`) wird wortwörtlich übernommen, sodass
  die Sensoren auf derselben Gerätekarte landen.
- Manuelles Setup über Host/IP für Drucker ohne IPP-Discovery.
- Konfigurierbares Polling-Intervall (Standard 15 Minuten – Seitenzähler
  ändern sich langsam, und das Web-UI des Druckers ist nicht für Last
  ausgelegt).
- Locale-unabhängiger Parser (funktioniert unabhängig von der
  UI-Sprache des Druckers).

## Installation

### Über HACS (empfohlen)

1. In HACS: *Integrationen* → ⋮ → *Benutzerdefinierte Repositories*.
2. `https://github.com/wwerther/ha-epson-ecotank-stats` als Typ
   **Integration** hinzufügen.
3. **Epson EcoTank Statistics** installieren.
4. Home Assistant neu starten.

### Manuell

`custom_components/epson_ecotank_stats/` in das HA-Verzeichnis
`config/custom_components/` kopieren und Home Assistant neu starten.

## Konfiguration

Nach dem Neustart:

- **Auto-Discovery:** Ein erkannter Epson-Drucker erscheint unter
  *Einstellungen → Geräte & Dienste → Erkannt*. Auf *Konfigurieren* klicken
  und bestätigen.
- **Manuell:** *Einstellungen → Geräte & Dienste → Integration hinzufügen*
  → nach *Epson EcoTank Statistics* suchen → Host bzw. IP eingeben.

Das Polling-Intervall lässt sich nachträglich über *Konfigurieren* an der
Integrations-Karte anpassen (Minimum: 60 Sekunden).

## Sensoren

| Sensor | Beschreibung |
|--------|--------------|
| `Total pages` | Gesamtanzahl Seiten über die Lebensdauer |
| `Black & white pages` / `Color pages` | Lebensdauer-Summen pro Farbmodus |
| `Simplex pages` / `Duplex pages` | Lebensdauer-Summen pro Duplex-Modus |
| `Pages copied / faxed / scanned / printed (B/W / color)` | Zähler pro Funktion (standardmäßig deaktiviert, pro Entität aktivierbar) |
| `Ink level black / cyan / magenta / yellow` | Tintenfüllstände in % |
| `Printer status` | Lokalisierter Statustext des Druckers |
| `Epson Connect status` | Registrierungsstatus (Diagnose) |
| `First print date` | Datum des ersten Druckjobs (Diagnose) |
| `Firmware version` | Firmware-String des Druckers (Diagnose, standardmäßig deaktiviert) |

## Funktionsweise

Die Integration pollt zwei HTML-Endpoints des Druckers:

| Endpoint | Inhalt |
|----------|--------|
| `/PRESENTATION/ADVANCED/INFO_PRTINFO/TOP` | Produktstatus, Tinten-Grafiken, Papierquelle |
| `/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP` | Wartung: Seitenzähler nach Modus, Größe, Funktion |

Die Zähler werden anhand der **DOM-Position** in den
`<fieldset>`/`<legend>`-Blöcken gelesen (locale-unabhängig). Tintenstände
werden aus dem `height`-Attribut der `Ink_K/C/M/Y.PNG`-Balkengrafiken
abgeleitet und auf 0–100 % normalisiert. Der Coordinator setzt zusätzlich
einmal pro Session via `SEL_LANGA=1` die UI-Sprache auf Englisch – rein
defensiv für label-basierte Fallbacks.

## Voraussetzungen

- Home Assistant 2024.11.0 oder neuer
- Drucker im lokalen Netzwerk per HTTP (Standard) oder HTTPS erreichbar
- Empfohlen: die Core-`ipp`-Integration ist für denselben Drucker
  eingerichtet, damit die Sensoren in einer Gerätekarte zusammengeführt
  werden

## Einschränkungen & Hinweise

- Das Web-UI des Druckers ist **nicht authentifiziert**. Nur in einem
  vertrauenswürdigen LAN einsetzen.
- Die Referenzhöhe für die Tinten-Normalisierung (`INK_FULL_HEIGHT_PX`)
  stammt aus der ET-2750-Fixture. Für andere Modelle kann eine kleine
  Kalibrierungskonstante nötig sein – PRs willkommen.
- Zähler und Tintenstände ändern sich langsam. Polling-Intervalle unter 60
  Sekunden werden abgelehnt, damit das eingebettete Web-UI ansprechbar
  bleibt.

## Entwicklung

```bash
# Parser-Tests gegen die HTML-Fixtures laufen lassen
.venv/bin/python -m pytest tests/ -q

# Code zu einer Home-Assistant-OS-Instanz pushen (live-Test)
./sync_to_ha.sh
```

Die HTML-Fixtures unter [`docs/`](docs/) sind die Wahrheit für den Parser.
Neue Firmware-Layouts sollten dort abgelegt werden.

Architektur-Details siehe [AGENTS.md](AGENTS.md), Roadmap siehe
[TODO.md](TODO.md).

## Lizenz

Veröffentlicht unter der MIT-Lizenz – siehe [LICENSE](LICENSE).

## Disclaimer

Dies ist eine **inoffizielle** Community-Integration und steht in keiner
Verbindung zur Seiko Epson Corporation. „Epson" und „EcoTank" sind
Markenzeichen der jeweiligen Inhaber.
