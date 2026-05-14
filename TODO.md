# TODO – Epson Ecotank Stats

Living document. Update immediately when status changes. Mirrors the real
implementation state of the repo.

## Status quo (Stand: Mai 2026)

P0 ist abgeschlossen. Die Integration ist als Config-Entry-basierter HACS-Component lauffähig (Setup über UI, Polling via `DataUpdateCoordinator`, Sensoren über `SensorEntityDescription`). Parser ist gegen die Fixtures unter `docs/` durch eine Pytest-Suite abgesichert (`.venv/bin/python -m pytest tests/` – 8 Tests grün).

Aktueller Code unter `custom_components/epson_ecotank_stats/`:
- `manifest.json` mit korrekter Domain, `config_flow`, `integration_type="device"`, `iot_class="local_polling"`, BS4 als Requirement.
- `const.py` mit allen Schlüsseln, Pfaden, Defaults.
- `parser.py` (rein, getestet) – strukturelles Parsen über Fieldset-Position, locale-unabhängig; Tinten via `<img height>` mit `INK_FULL_HEIGHT_PX = 50` als Referenz.
- `coordinator.py` – fetched beide Seiten parallel, setzt UI-Sprache einmalig auf Englisch (`SEL_LANGA=1`) als Best-Effort.
- `config_flow.py` – User-Step (Host/Name/Scheme/Port) mit Live-Validierung; OptionsFlow für Scan-Intervall (Min. 60 s); Unique-ID = Drucker-Serial (Fallback Host).
- `__init__.py` – `async_setup_entry`/`async_unload_entry`, Sensor-Plattform, Reload-Listener bei Options-Änderung.
- `sensor.py` – Totals, Funktionssensoren (default disabled), Tinten K/C/M/Y, Status, Epson-Connect, First-Print-Date, Firmware. Verbindet sich per `DeviceInfo.identifiers={("ipp", serial), (DOMAIN, ...)}` mit dem IPP-Gerät.
- `translations/en.json`.
- `tests/test_parser.py` – Fixture-basierte Tests, hierfür reicht `pytest + beautifulsoup4` (kein HA notwendig).

> Hinweis: `manifest.json` verwendet die Platzhalter-URL `https://github.com/wseifert/ha_epson_ecotank_stats`. Ggf. auf das echte GitHub-Repo umstellen, bevor releast wird.

## P0 – Bootstrap auf HA-Standard bringen ✅

- [x] `manifest.json` reparieren: korrekte Domain + Pflichtfelder.
- [x] `const.py` mit Domain, Pfaden, Defaults, Sensor-Keys.
- [x] `__init__.py` mit `async_setup_entry`/`async_unload_entry` + Sensor-Plattform.
- [x] `config_flow.py` (User-Step + Validierung + OptionsFlow).
- [x] `translations/en.json` für Config-Flow + Sensoren.

## P0 – Parser auf Basis der Fixtures ✅

- [x] `parse_maintenance` (totals, Größen-Matrix, Funktion, Sprache, Erstdruckdatum).
- [x] `parse_product_status` (Status, Tinten %, Paper-Source, Firmware, Serial, MAC, Epson Connect).
- [x] Strukturelles Parsen über Fieldset-Reihenfolge **plus** automatischer Sprachwechsel auf Englisch durch den Coordinator (Best-Effort, Fehler werden geloggt aber nicht propagiert).
- [x] Pytest-Suite (`tests/test_parser.py`).

## P0 – Coordinator & Sensoren ✅

- [x] `EpsonStatsCoordinator` mit Parallel-Fetch, Executor-Parsing, Timeout-Handling.
- [x] `sensor.py` als `SensorEntityDescription`-getriebene Generic-Entity.
- [x] Verwaistes `@property device_info` aus dem alten Stub entfernt.

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

- P0 komplett (Bootstrap, Parser inkl. Tests, Coordinator, Sensoren, i18n).
