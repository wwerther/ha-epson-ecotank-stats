"""DataUpdateCoordinator that fetches and parses the printer's status pages."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SCHEME,
    DATA_MAINTENANCE,
    DATA_PRODUCT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCHEME,
    DOMAIN,
    HTTP_TIMEOUT_SECONDS,
    LANG_ENGLISH,
    MIN_SCAN_INTERVAL_SECONDS,
    PATH_COMMON,
    PATH_MAINTENANCE,
    PATH_PRODUCT_STATUS,
)
from .parser import parse_maintenance, parse_product_status

_LOGGER = logging.getLogger(__name__)


class EpsonStatsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the printer's two HTML status pages and exposes parsed data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        scan_interval = self._scan_interval_from_options(entry)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry.data[CONF_HOST]})",
            update_interval=scan_interval,
        )
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._language_set = False

    @staticmethod
    def _scan_interval_from_options(entry: ConfigEntry) -> timedelta:
        seconds = entry.options.get(CONF_SCAN_INTERVAL)
        if not seconds:
            return DEFAULT_SCAN_INTERVAL
        try:
            value = int(seconds)
        except (TypeError, ValueError):
            return DEFAULT_SCAN_INTERVAL
        return timedelta(seconds=max(MIN_SCAN_INTERVAL_SECONDS, value))

    @property
    def base_url(self) -> str:
        scheme = self.entry.data.get(CONF_SCHEME, DEFAULT_SCHEME)
        host = self.entry.data[CONF_HOST]
        port = int(self.entry.data.get(CONF_PORT, DEFAULT_PORT))
        default_port = 80 if scheme == "http" else 443
        if port == default_port:
            return f"{scheme}://{host}"
        return f"{scheme}://{host}:{port}"

    async def _async_update_data(self) -> dict[str, Any]:
        # Best-effort: force the UI language to English once per coordinator
        # lifetime so label-based heuristics (e.g. for Epson Connect) work
        # regardless of the user's prior browser interaction.
        if not self._language_set:
            try:
                await self._set_language_english()
            except Exception as err:  # noqa: BLE001 - non-fatal
                _LOGGER.debug("Could not switch printer UI to English: %s", err)
            else:
                self._language_set = True

        try:
            maintenance_html, product_html = await asyncio.gather(
                self._fetch(PATH_MAINTENANCE),
                self._fetch(PATH_PRODUCT_STATUS),
            )
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error talking to printer: {err}") from err
        except asyncio.TimeoutError as err:
            raise UpdateFailed("Timeout while fetching printer status") from err

        maintenance = await self.hass.async_add_executor_job(
            parse_maintenance, maintenance_html
        )
        product = await self.hass.async_add_executor_job(
            parse_product_status, product_html
        )
        return {DATA_MAINTENANCE: maintenance, DATA_PRODUCT: product}

    async def _fetch(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        async with self._session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.text(encoding="utf-8", errors="replace")

    async def _set_language_english(self) -> None:
        url = f"{self.base_url}{PATH_COMMON}"
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        async with self._session.post(
            url,
            data={"SEL_LANGA": LANG_ENGLISH},
            timeout=timeout,
        ) as resp:
            resp.raise_for_status()
