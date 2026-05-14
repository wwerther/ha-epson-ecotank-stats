"""The Epson EcoTank Statistics integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_IPP_UUID, DOMAIN, IPP_DOMAIN
from .coordinator import EpsonStatsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


def _find_ipp_identifier(hass: HomeAssistant, host: str) -> str | None:
    """Return the verbatim IPP identifier of a device matching ``host``."""

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
        if needle and needle in (device.configuration_url or "").lower():
            return ipp_id
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Epson EcoTank Statistics from a config entry."""

    # Self-healing: if the user already has the IPP integration set up for the
    # same printer, look up its DeviceInfo identifier verbatim and persist it
    # so our DeviceInfo merges into the same device-registry entry. This also
    # corrects entries created with an outdated (e.g. lowercased) UUID.
    host = entry.data.get(CONF_HOST)
    if host:
        registry_ipp_id = _find_ipp_identifier(hass, host)
        if registry_ipp_id and registry_ipp_id != entry.data.get(CONF_IPP_UUID):
            _LOGGER.debug(
                "Updating ipp_uuid for entry %s from %r to %r (matched IPP device for host %s)",
                entry.entry_id,
                entry.data.get(CONF_IPP_UUID),
                registry_ipp_id,
                host,
            )
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_IPP_UUID: registry_ipp_id},
            )

    coordinator = EpsonStatsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change (e.g. scan interval)."""

    await hass.config_entries.async_reload(entry.entry_id)
