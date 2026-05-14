"""Constants for the Epson EcoTank Statistics integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "epson_ecotank_stats"
MANUFACTURER: Final = "Epson"

# Embedded web UI paths.
PATH_PRODUCT_STATUS: Final = "/PRESENTATION/ADVANCED/INFO_PRTINFO/TOP"
PATH_MAINTENANCE: Final = "/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP"
# Endpoint to switch the UI language. ``SEL_LANGA=1`` selects English.
PATH_COMMON: Final = "/PRESENTATION/ADVANCED/COMMON/TOP"
LANG_ENGLISH: Final = "1"

# Config / options keys.
CONF_HOST: Final = "host"
CONF_NAME: Final = "name"
CONF_SCHEME: Final = "scheme"
CONF_PORT: Final = "port"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCHEME: Final = "http"
DEFAULT_PORT: Final = 80
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=15)
MIN_SCAN_INTERVAL_SECONDS: Final = 60

HTTP_TIMEOUT_SECONDS: Final = 15

# Reference height (in pixels) of a fully-filled ink bar in the printer's
# product status page. Determined empirically from the ET-2750 fixture; can be
# overridden per-model later if needed.
INK_FULL_HEIGHT_PX: Final = 50

# Data dict keys (top-level) returned by the parser/coordinator.
DATA_MAINTENANCE: Final = "maintenance"
DATA_PRODUCT: Final = "product"

# Maintenance keys.
KEY_FIRST_PRINT_DATE: Final = "first_print_date"
KEY_PAGES_TOTAL: Final = "pages_total"
KEY_PAGES_BW: Final = "pages_bw"
KEY_PAGES_COLOR: Final = "pages_color"
KEY_PAGES_DUPLEX: Final = "pages_duplex"
KEY_PAGES_SIMPLEX: Final = "pages_simplex"
KEY_PAGES_BY_SIZE: Final = "pages_by_size"
KEY_PAGES_BY_FUNCTION: Final = "pages_by_function"
KEY_PAGES_BY_LANGUAGE: Final = "pages_by_language"

# Function counter sub-keys (in DOM order on the maintenance page).
FUNCTION_KEYS: Final = (
    "bw_copy",
    "color_copy",
    "bw_fax",
    "color_fax",
    "bw_scan",
    "color_scan",
    "bw_print",
    "color_print",
    "bw_other",
    "color_other",
)

# Language counter sub-keys.
LANGUAGE_KEYS: Final = (
    "escpr",
    "pcl",
    "postscript_pdf",
    "escpage",
    "other",
)

# Product status keys.
KEY_PRINTER_STATUS: Final = "printer_status"
KEY_INK_LEVELS: Final = "ink_levels"
KEY_PAPER_SOURCE: Final = "paper_source"
KEY_FIRMWARE: Final = "firmware"
KEY_SERIAL: Final = "serial"
KEY_MAC_ADDRESS: Final = "mac_address"
KEY_EPSON_CONNECT_STATUS: Final = "epson_connect_status"
KEY_MODEL: Final = "model"

# Ink colour codes (matching the Ink_*.PNG suffixes used by the printer).
INK_COLORS: Final = ("K", "C", "M", "Y")

# ---------------------------------------------------------------------------
# IPP integration interop
# ---------------------------------------------------------------------------
# Domain string used by the Home Assistant core ``ipp`` integration. We reuse
# its DeviceInfo identifier scheme ``("ipp", <printer-uuid>)`` so our sensors
# show up on the same device entry instead of creating a duplicate.
IPP_DOMAIN: Final = "ipp"

# Stored in ``ConfigEntry.data``: the IPP printer UUID we detected (either via
# zeroconf TXT records or by looking up the device registry). May be ``None``
# if the printer was added manually and no matching IPP device was found.
CONF_IPP_UUID: Final = "ipp_uuid"

# Zeroconf TXT key names. ``UUID`` carries the printer's UUID (sometimes with
# a ``urn:uuid:`` prefix), ``usb_MFG`` is the manufacturer string, ``ty`` is
# the human-readable model, ``adminurl`` points at the embedded web UI.
ZEROCONF_TXT_UUID: Final = "UUID"
ZEROCONF_TXT_MFG: Final = "usb_MFG"
ZEROCONF_TXT_MODEL: Final = "ty"
ZEROCONF_TXT_ADMIN_URL: Final = "adminurl"

# Manufacturer prefix we accept. Epson firmwares typically advertise
# ``EPSON`` exactly, but we match case-insensitively with a startswith().
EPSON_MFG_PREFIX: Final = "EPSON"
