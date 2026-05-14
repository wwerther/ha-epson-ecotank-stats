# AGENTS.md – Epson Ecotank Statistics (HA Custom Component)

This file is the source of truth for AI agents and developers working on this
integration. Keep it up to date as the project evolves and document relevant
decisions here. Always keep `README.md`, `info.md` and `TODO.md` in sync with
user-facing or implementation changes.

All documentation and code (identifiers, comments, log messages) must be in
**English**. User-facing strings must live in `translations/<lang>.json` and
never be hardcoded. Communication with the developer is in **German**.

## Project Goal

Extend an Epson EcoTank printer (initial reference model: ET-2750 Series, but
the implementation should target the family of Epson printers that expose the
same embedded web UI under `/PRESENTATION/ADVANCED/...`) inside Home Assistant
with data that is **not** available via SNMP, IPP or any existing HA
integration:

- Total page count (overall, B/W, color, simplex, duplex)
- Page count broken down by paper size and function (copy / fax / scan / print)
- Ink tank levels (parsed from the bar-image height in the product status page)
- First print date, printer status text
- Optional: Epson Connect status

The integration scrapes two HTML endpoints of the printer's embedded web
server and publishes the values as Home Assistant sensors. Where possible it
should attach to the **existing IPP-discovered device** in the device registry
instead of creating a separate device, so users see the new sensors on the
printer they already know.

## Source Pages on the Printer

Captured samples are committed under `docs/`:

| File | URL on the printer | Contents |
|------|--------------------|----------|
| `docs/PRESENTATION_ADVANCED_INFO_PRTINFO_TOP.html` | `http://<printer>/PRESENTATION/ADVANCED/INFO_PRTINFO/TOP` | Product status, ink tank graphics, paper source |
| `docs/PRESENTATION_ADVANCED_INFO_MENTINFO_TOP.html` | `http://<printer>/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP` | Maintenance: page counters by mode, size and function |

Parsing notes:
- Counters are exposed as `<dt class="key">Label</dt><dd class="value">…<div class="preserve-white-space">NUMBER</div></dd>` pairs. Matching by visible label is fragile because the labels are localised – prefer parsing by DOM position within each `<fieldset>` / `<legend>` block, or force the UI language to a known value before parsing.
- Ink levels are encoded in the `height` attribute of `IMAGE/Ink_*.PNG` images; the colour is identified via the filename suffix (`Ink_K`, `Ink_C`, `Ink_M`, `Ink_Y`) and/or the adjacent `<div class='clrname'>`.
- The printer answers in the language configured via the `SEL_LANGA` form. If we rely on labels, the integration should force a stable language (English) by submitting that form once, otherwise label-based parsing breaks across locales.

## Repository Structure

```
.
├── AGENTS.md
├── README.md                # user-facing docs (HACS preview)
├── TODO.md                  # work-in-progress tracker, keep current
├── hacs.json
├── LICENSE
├── sync_to_ha.sh            # rsync helper to push code to HAOS
├── docs/                    # captured HTML samples used as parser fixtures
└── custom_components/
    └── epson_ecotank_stats/
        ├── __init__.py      # async_setup_entry / unload, coordinator wiring
        ├── manifest.json
        ├── const.py         # DOMAIN, URLs, default scan interval, keys
        ├── config_flow.py   # user + (optional) zeroconf discovery flow
        ├── coordinator.py   # DataUpdateCoordinator that fetches + parses HTML
        ├── parser.py        # pure functions: html (str) -> dict[str, Any]
        ├── sensor.py        # SensorEntity definitions
        └── translations/
            └── en.json
```

> ⚠️ **Domain rule:** the folder under `custom_components/` must be identical
> to the `domain` value in `manifest.json` and to `DOMAIN` in `const.py`. The
> folder is `epson_ecotank_stats`, so `DOMAIN` must be `"epson_ecotank_stats"`.
> The current `manifest.json` still uses `epson_extended` – this has to be
> fixed (see `TODO.md`).

## Technology Stack

- **Language:** Python 3.12+
- **Framework:** Home Assistant custom component (config-entry based, no YAML)
- **HTTP client:** `aiohttp` via `homeassistant.helpers.aiohttp_client.async_get_clientsession` (do **not** create your own `ClientSession`)
- **HTML parser:** `beautifulsoup4` (already in `manifest.json` requirements)
- **Update strategy:** `DataUpdateCoordinator` with a configurable scan interval (default 15 min – page counters change slowly, do not hammer the printer)

## Key Files & Responsibilities (target architecture)

| File | Responsibility |
|------|----------------|
| `const.py` | `DOMAIN`, default scan interval, page paths, sensor keys, `MANUFACTURER = "Epson"`. |
| `manifest.json` | `domain`, `name`, `version`, `requirements` (`beautifulsoup4`), `codeowners`, `documentation`, `issue_tracker`, `integration_type: "device"`, `iot_class: "local_polling"`, `config_flow: true`. |
| `config_flow.py` | User step asking for host/IP (and optional name); validates by fetching one of the status pages. Optional `async_step_zeroconf` for IPP (`_ipp._tcp.local.`) discovery. |
| `coordinator.py` | `EpsonStatsCoordinator(DataUpdateCoordinator)` – fetches both HTML pages and returns a parsed dict. |
| `parser.py` | Pure, side-effect-free parsing functions, unit-testable against the fixtures in `docs/`. |
| `sensor.py` | Declares one `SensorEntity` per metric using `SensorEntityDescription`. |
| `__init__.py` | `async_setup_entry` (create coordinator, forward to platforms) and `async_unload_entry`. |
| `translations/en.json` | All user-facing strings. |
| `sync_to_ha.sh` | rsync helper to push the integration to HAOS for live testing. |

## Device Registry & Integration with the IPP Device

Goal: do not create a duplicate "Epson" device. Two options, in order of
preference:

1. **Attach to the existing IPP device** by reusing one of its `identifiers`
   in `DeviceInfo`. The HA core IPP integration uses
   `("ipp", <unique_id>)` as identifier. If the user provides (or we can
   discover) the same unique id (printer UUID / serial), set the same
   `identifiers` so both integrations contribute entities to the same device.
2. **Fallback:** create our own device with `identifiers={(DOMAIN, host)}`
   and link it via `via_device` if a parent device is known.

Discovery of the IPP unique id can be done via the printer's IPP
`printer-uuid` attribute or via the `serial` advertised in the maintenance
page. Document whichever path is implemented.

## Coding Conventions

- Follow the [Home Assistant Development Guidelines](https://developers.home-assistant.io/docs/development_guidelines/).
- All I/O is `async`; CPU-bound HTML parsing must run in the executor (`hass.async_add_executor_job`) when it grows non-trivial.
- Type hints are mandatory; aim for `mypy --strict` cleanliness on new code.
- Constants belong in `const.py`; avoid magic strings.
- Sensors are declared via `SensorEntityDescription` with `translation_key`,
  `state_class` (`MEASUREMENT` for ink, `TOTAL_INCREASING` for page counters)
  and appropriate `device_class` / `native_unit_of_measurement`
  (e.g. `"pages"` as a custom unit, `PERCENTAGE` for ink levels).
- Never block the event loop. No `requests`, no `time.sleep`.
- Settings the user can change after setup belong in `entry.options`;
  immutable setup data (host) belongs in `entry.data`.
- Runtime state is stored in `hass.data[DOMAIN][entry.entry_id]`.

## Development Workflow (Local VS Code → HAOS)

1. **Edit code** locally in VS Code.
2. **Sync** to HAOS:
   ```bash
   ./sync_to_ha.sh
   ```
   The script rsyncs `custom_components/epson_ecotank_stats/` to
   `HA_TARGET_DIR` (default `/root/homeassistant/custom_components/epson_ecotank_stats`)
   on `root@homeassistant.lan`. Default `SSH_PORT` is `22` (HA Add-on SSH);
   use `22222` for direct HAOS host access.
3. **Reload** the integration in HA (Developer Tools → "Integrationen neu laden",
   or the gear icon on the integration card). Restart only when `manifest.json`
   or new requirements change.
4. **Logs**:
   ```bash
   ssh -p <PORT> root@homeassistant.lan "docker logs homeassistant -f"
   ```

## Testing

- Treat the files under `docs/` as **parser fixtures**. Any change to the
  parser must be backed by an assertion against these fixtures (`pytest`
  preferred). Add new fixtures whenever a new firmware/layout is encountered
  – never delete old ones.
- Network code in `coordinator.py` should be exercised with `aioresponses`
  (or similar) so tests do not require a real printer.

## Important Constraints & Pitfalls

- **Localisation:** The printer renders labels in the configured UI language.
  Force English before parsing, or parse purely structurally.
- **Authentication:** The status pages are unauthenticated on the local LAN.
  We assume the printer is on a trusted network. Document this clearly.
- **Polling cadence:** Counters change rarely. Default ≥ 15 min, allow user
  override via options flow but enforce a sensible minimum (e.g. 60 s).
- **Charset:** Both pages are UTF-8. Always read with
  `await resp.text(encoding="utf-8")` (or pass `errors="replace"`).
- **Robustness:** Numbers may be missing (newer firmware, model differences).
  The parser must tolerate missing fields and return `None` for them; the
  sensor then reports `unavailable` rather than crashing.
- **Port / scheme:** The embedded web UI is usually on port 80 / HTTP. Some
  models expose HTTPS on 443 with a self-signed cert – allow the user to
  configure scheme/port if needed.
- **Permission denied** when syncing via non-root user → use `root@…` and the
  correct port (`22` add-on, `22222` host).
- **Domain mismatch** (folder vs. `manifest.json` vs. `DOMAIN`) makes HA
  silently ignore the integration. Triple-check after renames.

## Adding New Features

### Adding a new scraped field
1. Add a fixture (or extend an existing one) under `docs/` if the field comes
   from a page we do not yet capture.
2. Implement the extraction in `parser.py` against the fixture.
3. Add a key/constant in `const.py`.
4. Add a `SensorEntityDescription` in `sensor.py` and a translation entry.
5. Update `README.md` and `TODO.md`.

### Supporting a new printer model
1. Capture the relevant HTML pages and add them under `docs/<model>/`.
2. If the layout differs, branch in `parser.py` based on a stable marker
   (e.g. `<title>` content) – do not duplicate the whole module.

## Useful Commands

> Replace `<PORT>` with `22` (Add-on SSH) or `22222` (HAOS host SSH).

```bash
# Sync code to HAOS
./sync_to_ha.sh

# Follow HA logs
ssh -p <PORT> root@homeassistant.lan "docker logs homeassistant -f"

# Restart HA Core remotely
ssh -p <PORT> root@homeassistant.lan "ha core restart"

# Quick local check of a printer page
curl -s http://<printer>/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP | head -c 4000
```

## Future Enhancements (Ideas)

- Options flow for scan interval, scheme/port and language override.
- Diagnostics download (HA Diagnostics platform) that includes the raw HTML
  with PII redacted.
- Support for additional Epson model families (XP-…, WF-…) by detecting the
  layout via `<title>`.
- Binary sensor for "printer ready" / error state from the product status page.
- Config-flow re-auth / re-configure step when the host changes.

## References

- [Home Assistant Custom Component Docs](https://developers.home-assistant.io/docs/creating_component_index/)
- [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data)
- [Config Entries & Options Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Device Registry / DeviceInfo](https://developers.home-assistant.io/docs/device_registry_index/)
- [SensorEntityDescription](https://developers.home-assistant.io/docs/core/entity/sensor/)
