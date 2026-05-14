# Epson EcoTank Statistics for Home Assistant

🌐 **English** · [Deutsch](README.de.md)

A custom Home Assistant integration that scrapes the embedded web UI of Epson
EcoTank printers and exposes data that **no other integration** (IPP, SNMP,
mDNS) makes available:

- Total page counters (overall, B/W, colour, simplex, duplex)
- Page counters by function (copy, fax, scan, print – B/W and colour)
- Ink tank levels for K / C / M / Y
- Printer status, first-print date, firmware, Epson Connect status

The integration **attaches to the existing IPP-discovered printer device** in
the device registry, so all sensors appear under the printer you already know
instead of creating a duplicate.

> Reference model used during development: **Epson ET-2750 Series**. Other
> Epson families that expose the same `/PRESENTATION/ADVANCED/...` web UI
> should work out of the box.

## Features

- Auto-discovery via zeroconf (`_ipp._tcp.local.` / `_ipps._tcp.local.`) –
  the printer pops up under *Settings → Devices & Services → Discovered* as
  soon as Home Assistant sees an Epson IPP printer on the network.
- Auto-merge with the core IPP integration's device entry. The integration
  reuses the IPP device's identifier (`("ipp", <printer-uuid>)`) verbatim, so
  the sensors land on the same device card.
- Manual setup via host/IP for printers that do not expose IPP discovery.
- Configurable polling interval (default 15 minutes – page counters change
  slowly, the printer's web UI is not designed for high load).
- Locale-agnostic parser (works regardless of the printer's UI language).

## Installation

### Via HACS (recommended)

1. In HACS, open *Integrations* → ⋮ → *Custom repositories*.
2. Add `https://github.com/wwerther/ha-epson-ecotank-stats` as type
   **Integration**.
3. Install **Epson EcoTank Statistics**.
4. Restart Home Assistant.

### Manual

Copy `custom_components/epson_ecotank_stats/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

After a restart, either:

- **Auto-discovery:** A discovered Epson printer appears under
  *Settings → Devices & Services → Discovered*. Click *Configure* and confirm.
- **Manually:** *Settings → Devices & Services → Add integration* → search for
  *Epson EcoTank Statistics* → enter the printer's host or IP.

Polling interval can be adjusted via the *Configure* button on the integration
card (minimum: 60 seconds).

## Sensors

| Sensor | Description |
|--------|-------------|
| `Total pages` | Overall lifetime page count |
| `Black & white pages` / `Color pages` | Lifetime totals per colour mode |
| `Simplex pages` / `Duplex pages` | Lifetime totals per duplex mode |
| `Pages copied / faxed / scanned / printed (B/W / color)` | Per-function counters (disabled by default, enable per entity) |
| `Ink level black / cyan / magenta / yellow` | Tank levels in % |
| `Printer status` | Localised status text from the printer |
| `Epson Connect status` | Registration status (diagnostic) |
| `First print date` | Date of the first print job (diagnostic) |
| `Firmware version` | Printer firmware string (diagnostic, disabled by default) |

## How it works

The integration polls two HTML endpoints on the printer:

| Endpoint | Purpose |
|----------|---------|
| `/PRESENTATION/ADVANCED/INFO_PRTINFO/TOP` | Product status, ink graphics, paper source |
| `/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP` | Maintenance: page counters by mode, size, function |

Page counters are read by **DOM position** inside the
`<fieldset>`/`<legend>` blocks (locale-independent). Ink levels are derived
from the `height` attribute of the `Ink_K/C/M/Y.PNG` bar images and
normalised to 0–100 %. The integration also POSTs `SEL_LANGA=1` once per
session to set the printer's UI to English – purely defensive for label-based
fallbacks.

## Requirements

- Home Assistant 2024.11.0 or newer
- Printer reachable over HTTP (default) or HTTPS on the local network
- The HA core `ipp` integration set up for the same printer (recommended, so
  the sensors get merged into one device card)

## Limitations & Caveats

- The printer's web UI is **unauthenticated**. Use this only on a trusted
  LAN.
- The reference height for ink-level normalisation (`INK_FULL_HEIGHT_PX`) was
  taken from the ET-2750 fixture. For other models the absolute percentage
  may need a small calibration constant – PRs welcome.
- Counters and ink readings change slowly. Polling intervals below 60 s are
  rejected to keep the embedded web UI responsive.

## Development

```bash
# Run parser tests against the captured HTML fixtures
.venv/bin/python -m pytest tests/ -q

# Push code to a Home Assistant OS instance for live testing
./sync_to_ha.sh
```

Captured HTML fixtures live under [`docs/`](docs/) and are the source of
truth for the parser. New firmware layouts should be added there.

See [AGENTS.md](AGENTS.md) for the architectural deep-dive and
[TODO.md](TODO.md) for the roadmap.

## License

Distributed under the MIT License – see [LICENSE](LICENSE).

## Disclaimer

This is an **unofficial** community integration and is not affiliated with or
endorsed by Seiko Epson Corporation. "Epson" and "EcoTank" are trademarks of
their respective owners.
