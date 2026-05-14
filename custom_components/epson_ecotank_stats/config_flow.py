"""Config flow for Epson EcoTank Statistics."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_IPP_UUID,
    CONF_SCAN_INTERVAL,
    CONF_SCHEME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCHEME,
    DOMAIN,
    EPSON_MFG_PREFIX,
    HTTP_TIMEOUT_SECONDS,
    IPP_DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
    PATH_PRODUCT_STATUS,
    ZEROCONF_TXT_MFG,
    ZEROCONF_TXT_MODEL,
    ZEROCONF_TXT_UUID,
)
from .parser import parse_product_status

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default="Epson Printer"): str,
        vol.Optional(CONF_SCHEME, default=DEFAULT_SCHEME): vol.In(["http", "https"]),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
)


def _normalise_uuid(raw: str | None) -> str | None:
    """Strip the ``urn:uuid:`` prefix some printers add to the TXT record."""

    if not raw:
        return None
    value = raw.strip()
    if value.lower().startswith("urn:uuid:"):
        value = value[len("urn:uuid:") :]
    return value.lower() or None


def _txt_get(properties: dict[str, Any], key: str) -> str | None:
    """Return a TXT property as a stripped string or ``None``."""

    value = properties.get(key)
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return None
    text = str(value).strip()
    return text or None


def _lookup_ipp_uuid_by_host(hass: HomeAssistant, host: str) -> str | None:
    """Find an existing IPP device-registry entry whose host matches ``host``.

    The IPP integration creates a device with identifier ``("ipp", <uuid>)``
    and stores the host as part of ``configuration_url``
    (e.g. ``http://1.2.3.4:631``). We try that first.
    """

    registry = dr.async_get(hass)
    needle = host.lower()
    for device in registry.devices.values():
        ipp_id: str | None = None
        for domain, identifier in device.identifiers:
            if domain == IPP_DOMAIN:
                ipp_id = identifier
                break
        if ipp_id is None:
            continue
        config_url = (device.configuration_url or "").lower()
        if needle and needle in config_url:
            return ipp_id
    return None


async def _validate_host(
    hass: HomeAssistant, host: str, scheme: str, port: int
) -> dict[str, Any]:
    """Fetch the product-status page and return identity info on success."""

    session = async_get_clientsession(hass)
    default_port = 80 if scheme == "http" else 443
    netloc = host if port == default_port else f"{host}:{port}"
    url = f"{scheme}://{netloc}{PATH_PRODUCT_STATUS}"
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
    async with session.get(url, timeout=timeout) as resp:
        resp.raise_for_status()
        text = await resp.text(encoding="utf-8", errors="replace")
    return parse_product_status(text)


class EpsonEcoTankStatsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for the Epson EcoTank Statistics integration."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Manual / user-initiated flow
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host: str = user_input[CONF_HOST].strip()
            scheme: str = user_input[CONF_SCHEME]
            port: int = user_input[CONF_PORT]
            try:
                identity = await _validate_host(self.hass, host, scheme, port)
            except aiohttp.ClientResponseError as err:
                _LOGGER.debug("HTTP error from printer: %s", err)
                errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, TimeoutError, OSError) as err:
                _LOGGER.debug("Connection error to printer: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Epson printer")
                errors["base"] = "unknown"
            else:
                # Best effort: locate an existing IPP device for this host so
                # we attach to the same device-registry entry. The IPP
                # integration's identifier is ``("ipp", <printer-uuid>)``.
                ipp_uuid = _lookup_ipp_uuid_by_host(self.hass, host)

                # Use the IPP UUID as our unique_id when available so HA
                # transparently merges entries created via zeroconf and
                # manually. Otherwise fall back to the printer serial or host.
                unique_id = (
                    ipp_uuid
                    or identity.get("serial")
                    or host.lower()
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                title = user_input.get(CONF_NAME) or identity.get("model") or host
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: host,
                        CONF_NAME: title,
                        CONF_SCHEME: scheme,
                        CONF_PORT: port,
                        CONF_IPP_UUID: ipp_uuid,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Zeroconf discovery (auto-kicks-in for IPP-discovered Epson printers)
    # ------------------------------------------------------------------

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a printer announced via ``_ipp[s]._tcp.local.``.

        The matcher in ``manifest.json`` already restricts this to Epson
        manufacturers; we re-check defensively in case the matcher is loose.
        """

        properties = dict(discovery_info.properties or {})
        manufacturer = _txt_get(properties, ZEROCONF_TXT_MFG) or ""
        if not manufacturer.upper().startswith(EPSON_MFG_PREFIX):
            return self.async_abort(reason="not_epson")

        uuid = _normalise_uuid(_txt_get(properties, ZEROCONF_TXT_UUID))
        if uuid is None:
            # Without a stable UUID we cannot safely attach to the IPP device
            # entry, so we skip the auto-flow and let the user add it manually.
            return self.async_abort(reason="no_uuid")

        await self.async_set_unique_id(uuid)
        host = discovery_info.host
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        model = _txt_get(properties, ZEROCONF_TXT_MODEL) or "Epson Printer"

        # Quick reachability + identity check against the embedded web UI.
        try:
            identity = await _validate_host(
                self.hass, host, DEFAULT_SCHEME, DEFAULT_PORT
            )
        except (aiohttp.ClientError, TimeoutError, OSError):
            # Web UI unreachable on http/80 – the IPP service itself may live
            # on a different host or port. Don't pollute the discovery list.
            return self.async_abort(reason="cannot_connect")

        # Prefer the model name from the printer's web UI title; fall back to
        # the zeroconf TXT ``ty`` field.
        title = identity.get("model") or model

        self._discovered = {
            CONF_HOST: host,
            CONF_NAME: title,
            CONF_SCHEME: DEFAULT_SCHEME,
            CONF_PORT: DEFAULT_PORT,
            CONF_IPP_UUID: uuid,
        }
        self.context["title_placeholders"] = {"name": title, "host": host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm adding a discovered Epson printer."""

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered[CONF_NAME],
                data=self._discovered,
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._discovered.get(CONF_NAME, ""),
                "host": self._discovered.get(CONF_HOST, ""),
            },
        )

    # ------------------------------------------------------------------
    # Options flow
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return EpsonEcoTankStatsOptionsFlow(config_entry)


class EpsonEcoTankStatsOptionsFlow(config_entries.OptionsFlow):
    """Options flow exposing the polling interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
