"""Parser tests using the captured HTML fixtures under ``docs/``.

The integration's package ``__init__.py`` pulls in ``homeassistant`` which is
not (and should not be) a dev-time test dependency. We therefore load the
``parser`` and ``const`` modules directly through ``importlib``, bypassing
``epson_ecotank_stats/__init__.py``.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "custom_components" / "epson_ecotank_stats"


def _load_pkg() -> types.ModuleType:
    pkg_name = "epson_ecotank_stats"
    if pkg_name in sys.modules and getattr(sys.modules[pkg_name], "_test_stub", False):
        return sys.modules[pkg_name]

    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(PKG_DIR)]  # type: ignore[attr-defined]
    pkg._test_stub = True  # type: ignore[attr-defined]
    sys.modules[pkg_name] = pkg

    for sub in ("const", "parser"):
        spec = importlib.util.spec_from_file_location(
            f"{pkg_name}.{sub}", PKG_DIR / f"{sub}.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{pkg_name}.{sub}"] = module
        spec.loader.exec_module(module)
        setattr(pkg, sub, module)
    return pkg


_pkg = _load_pkg()
parser = _pkg.parser  # type: ignore[attr-defined]
C = _pkg.const  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def maintenance_html() -> str:
    return (REPO_ROOT / "docs" / "PRESENTATION_ADVANCED_INFO_MENTINFO_TOP.html").read_text(
        encoding="utf-8"
    )


@pytest.fixture(scope="module")
def product_html() -> str:
    return (REPO_ROOT / "docs" / "PRESENTATION_ADVANCED_INFO_PRTINFO_TOP.html").read_text(
        encoding="utf-8"
    )


def test_parse_maintenance_totals(maintenance_html: str) -> None:
    data = parser.parse_maintenance(maintenance_html)
    assert data[C.KEY_FIRST_PRINT_DATE] == "2021-01-31"
    assert data[C.KEY_PAGES_TOTAL] == 4127
    assert data[C.KEY_PAGES_BW] == 754
    assert data[C.KEY_PAGES_COLOR] == 3373
    assert data[C.KEY_PAGES_DUPLEX] == 1544
    assert data[C.KEY_PAGES_SIMPLEX] == 2583
    assert data[C.KEY_PAGES_BW] + data[C.KEY_PAGES_COLOR] == data[C.KEY_PAGES_TOTAL]
    assert data[C.KEY_PAGES_SIMPLEX] + data[C.KEY_PAGES_DUPLEX] == data[C.KEY_PAGES_TOTAL]


def test_parse_maintenance_size_table(maintenance_html: str) -> None:
    sizes = parser.parse_maintenance(maintenance_html)[C.KEY_PAGES_BY_SIZE]
    assert sizes["a4_letter"] == {
        "simplex_bw": 532,
        "simplex_color": 2044,
        "duplex_bw": 222,
        "duplex_color": 1322,
    }
    assert sizes["a3_ledger"] == {
        "simplex_bw": 0,
        "simplex_color": 0,
        "duplex_bw": 0,
        "duplex_color": 0,
    }
    assert sizes["b4_legal"]["simplex_color"] == 1
    assert sizes["other"]["simplex_color"] == 4


def test_parse_maintenance_function_counts(maintenance_html: str) -> None:
    fn = parser.parse_maintenance(maintenance_html)[C.KEY_PAGES_BY_FUNCTION]
    assert fn == {
        "bw_copy": 74,
        "color_copy": 41,
        "bw_fax": 0,
        "color_fax": 0,
        "bw_scan": 99,
        "color_scan": 104,
        "bw_print": 651,
        "color_print": 3290,
        "bw_other": 29,
        "color_other": 42,
    }


def test_parse_maintenance_language_counts(maintenance_html: str) -> None:
    langs = parser.parse_maintenance(maintenance_html)[C.KEY_PAGES_BY_LANGUAGE]
    assert langs == {
        "escpr": 416,
        "pcl": 0,
        "postscript_pdf": 0,
        "escpage": 0,
        "other": 3711,
    }


def test_parse_product_status_identity(product_html: str) -> None:
    data = parser.parse_product_status(product_html)
    assert data[C.KEY_MODEL] == "ET-2750 Series"
    assert data[C.KEY_PRINTER_STATUS] == "Verfügbar"
    assert data[C.KEY_FIRMWARE] == "07.59.LW14NB"
    assert data[C.KEY_SERIAL] == "X95B006435"
    assert data[C.KEY_MAC_ADDRESS] == "E0:BB:9E:CF:82:A4"
    assert data[C.KEY_EPSON_CONNECT_STATUS] == "Nicht registriert"


def test_parse_product_status_ink_levels(product_html: str) -> None:
    levels = parser.parse_product_status(product_html)[C.KEY_INK_LEVELS]
    assert set(levels.keys()) == {"K", "C", "M", "Y"}
    for percent in levels.values():
        assert 0 <= percent <= 100
    # Heights 41/43 with the default 50 px reference → 82 % / 86 %.
    assert levels["K"] == 82
    assert levels["C"] == 86


def test_parse_product_status_paper_source(product_html: str) -> None:
    data = parser.parse_product_status(product_html)
    assert data[C.KEY_PAPER_SOURCE] == {
        "size": "A4 210 x 297 mm",
        "type": "Normalpapier",
    }


def test_parser_tolerates_garbage() -> None:
    maintenance = parser.parse_maintenance("<html><body>nothing here</body></html>")
    product = parser.parse_product_status("<html><body>nothing</body></html>")
    assert maintenance[C.KEY_PAGES_TOTAL] is None
    assert maintenance[C.KEY_PAGES_BY_SIZE] == {}
    assert product[C.KEY_INK_LEVELS] == {}
    assert product[C.KEY_SERIAL] is None
