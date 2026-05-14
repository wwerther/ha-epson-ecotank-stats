# TODO – Epson Ecotank Stats

Living document. Update immediately when status changes. Mirrors the real
implementation state of the repo.

## Status quo (Stand: Mai 2026)

Das Repo enthält erst einen **Scaffold-Entwurf**:

- `custom_components/epson_ecotank_stats/__init__.py` ist **leer** → kein `async_setup_entry`, also kein Config-Flow möglich.
- `custom_components/epson_ecotank_stats/manifest.json` deklariert `domain: "epson_extended"` (passt **nicht** zum Ordnernamen `epson_ecotank_stats`) und es fehlen Pflichtfelder (`documentation`, `issue_tracker`, `integration_type`, `iot_class`, `config_flow`).
- `custom_components/epson_ecotank_stats/sensor.py` ist YAML-Plattform-Code mit hartkodierter `URL = "http://PRINTER_IP/status.html"`, einem unbenutzten `device_info`-`@property` **außerhalb** der Klasse (Bug) und ohne Bezug zum tatsächlichen Status-HTML.
- HTML-Beispiele aus dem realen Drucker liegen unter `docs/`.
- `sync_to_ha.sh` rsynct nach `root@homeassistant.lan:/root/homeassistant/custom_components/epson_ecotank_stats`.

## P0 – Bootstrap auf HA-Standard bringen

- [ ] `manifest.json` reparieren: `domain` = `epson_ecotank_stats`, `config_flow: true`, `integration_type: "device"`, `iot_class: "local_polling"`, `documentation`, `issue_tracker`, `codeowners`.
- [ ] `const.py` anlegen: `DOMAIN`, `MANUFACTURER`, Pfade `PATH_PRTINFO` / `PATH_MENTINFO`, `DEFAULT_SCAN_INTERVAL`, Sensor-Keys.
- [ ] `__init__.py` mit echtem `async_setup_entry` / `async_unload_entry` und Plattform-Forward (`Platform.SENSOR`).
- [ ] `config_flow.py` (User-Step: Host/IP, optional Name) inkl. Validierung durch Test-Fetch einer Statusseite.
- [ ] `translations/en.json` mit allen User-sichtbaren Strings (Config-Flow + Sensor-Namen).

## P0 – Parser auf Basis der Fixtures

- [ ] `parser.py`: reine Funktionen
  - [ ] `parse_maintenance(html: str) -> dict[str, Any]` → totals (overall, B/W, color, simplex, duplex), per-size matrix, per-function counters, first print date.
  - [ ] `parse_product_status(html: str) -> dict[str, Any]` → printer status, ink levels (`{"K": 0..100, ...}`), paper source info, optional Epson Connect status.
- [ ] Strukturelles Parsen (Position innerhalb `<fieldset>`/`<legend>`) statt Label-Match, **oder** Sprache des Druckers vor dem Fetch auf Englisch zwingen (`SEL_LANGA=1`). Entscheidung dokumentieren.
- [ ] Tinten-Level aus `height`-Attribut der `IMAGE/Ink_*.PNG` ableiten und auf 0–100 % normalisieren (Referenzhöhe ermitteln).
- [ ] Pytest-Suite gegen die Fixtures in `docs/`.

## P0 – Coordinator & Sensoren

- [ ] `coordinator.py`: `EpsonStatsCoordinator(DataUpdateCoordinator)` zieht beide Seiten via `async_get_clientsession`, parst über `parser.py`, liefert ein konsolidiertes Dict.
- [ ] `sensor.py` neu aufsetzen mit `SensorEntityDescription` pro Metrik:
  - Page-Counter (`state_class=TOTAL_INCREASING`, unit `pages`)
  - Ink-Levels (`state_class=MEASUREMENT`, unit `%`)
  - Status-Text (kein `state_class`)
  - First-print-date als Sensor mit `device_class=DATE`
- [ ] Bug entfernen: das verwaiste `@property device_info` außerhalb der Klasse löschen.

## P1 – Geräteverknüpfung mit IPP

- [ ] `DeviceInfo.identifiers` so wählen, dass dieselbe Device-Registry-Zeile wie die Core-`ipp`-Integration getroffen wird (`("ipp", <printer-uuid>)`).
- [ ] Printer-UUID/Serial entweder aus IPP-Discovery (zeroconf-Schritt) oder aus der Wartungsseite extrahieren.
- [ ] Fallback-Identifier `(DOMAIN, host)` falls keine UUID bekannt ist; `via_device` setzen, wenn möglich.

## P1 – Discovery & UX

- [ ] `async_step_zeroconf` für `_ipp._tcp.local.`; Vorschlag aus dem Discovery-Payload (Host, Name, UUID).
- [ ] Options-Flow: `scan_interval`, Scheme/Port, ggf. UI-Sprache.
- [ ] HACS-Metadaten: `README.md` mit Screenshots/Erklärung, `info.md` für die HACS-Detailansicht, `hacs.json` ggf. ergänzen (`country`, `homeassistant`-Min-Version stimmt schon: 2024.11.0).

## P2 – Diagnose & Robustheit

- [ ] HA-Diagnostics-Plattform (`diagnostics.py`) – liefert Roh-HTML mit redacteten Hostnames/Seriennummern.
- [ ] Fehlende Felder → Sensor `unavailable`, kein Crash.
- [ ] Re-Auth / Reconfigure-Step bei IP-Wechsel.
- [ ] Logging über `_LOGGER = logging.getLogger(__name__)`, sinnvolle Levels.

## P2 – Erweiterbare Modellunterstützung

- [ ] Layout-Erkennung über `<title>` (`ET-2750 Series`, `XP-…`, `WF-…`).
- [ ] Fixtures pro Modell unter `docs/<model>/` ablegen.
- [ ] Branching in `parser.py` statt Modul-Duplikate.

## Done

_(noch nichts implementiert; Repo ist Scaffold)_
