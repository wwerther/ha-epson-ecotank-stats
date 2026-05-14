"""Sensor platform for the Epson EcoTank Statistics integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_IPP_UUID,
    DATA_MAINTENANCE,
    DATA_PRODUCT,
    DOMAIN,
    FUNCTION_KEYS,
    INK_COLORS,
    IPP_DOMAIN,
    KEY_EPSON_CONNECT_STATUS,
    KEY_FIRMWARE,
    KEY_FIRST_PRINT_DATE,
    KEY_INK_LEVELS,
    KEY_MAC_ADDRESS,
    KEY_MODEL,
    KEY_PAGES_BW,
    KEY_PAGES_BY_FUNCTION,
    KEY_PAGES_COLOR,
    KEY_PAGES_DUPLEX,
    KEY_PAGES_SIMPLEX,
    KEY_PAGES_TOTAL,
    KEY_PRINTER_STATUS,
    KEY_SERIAL,
    MANUFACTURER,
)
from .coordinator import EpsonStatsCoordinator

UNIT_PAGES = "pages"


@dataclass(frozen=True, kw_only=True)
class EpsonSensorDescription(SensorEntityDescription):
    """Sensor description that knows how to extract its value from the data dict."""

    value_fn: Callable[[Mapping[str, Any]], Any]


def _maintenance(data: Mapping[str, Any], key: str) -> Any:
    return data.get(DATA_MAINTENANCE, {}).get(key)


def _product(data: Mapping[str, Any], key: str) -> Any:
    return data.get(DATA_PRODUCT, {}).get(key)


def _function_count(data: Mapping[str, Any], key: str) -> Any:
    return data.get(DATA_MAINTENANCE, {}).get(KEY_PAGES_BY_FUNCTION, {}).get(key)


def _ink_level(data: Mapping[str, Any], colour: str) -> Any:
    return data.get(DATA_PRODUCT, {}).get(KEY_INK_LEVELS, {}).get(colour)


PAGE_DESCRIPTIONS: tuple[EpsonSensorDescription, ...] = (
    EpsonSensorDescription(
        key=KEY_PAGES_TOTAL,
        translation_key="pages_total",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _maintenance(d, KEY_PAGES_TOTAL),
    ),
    EpsonSensorDescription(
        key=KEY_PAGES_BW,
        translation_key="pages_bw",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _maintenance(d, KEY_PAGES_BW),
    ),
    EpsonSensorDescription(
        key=KEY_PAGES_COLOR,
        translation_key="pages_color",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _maintenance(d, KEY_PAGES_COLOR),
    ),
    EpsonSensorDescription(
        key=KEY_PAGES_SIMPLEX,
        translation_key="pages_simplex",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _maintenance(d, KEY_PAGES_SIMPLEX),
    ),
    EpsonSensorDescription(
        key=KEY_PAGES_DUPLEX,
        translation_key="pages_duplex",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _maintenance(d, KEY_PAGES_DUPLEX),
    ),
)

FUNCTION_DESCRIPTIONS: tuple[EpsonSensorDescription, ...] = tuple(
    EpsonSensorDescription(
        key=f"function_{name}",
        translation_key=f"function_{name}",
        native_unit_of_measurement=UNIT_PAGES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d, name=name: _function_count(d, name),
    )
    for name in FUNCTION_KEYS
)

INK_DESCRIPTIONS: tuple[EpsonSensorDescription, ...] = tuple(
    EpsonSensorDescription(
        key=f"ink_{colour.lower()}",
        translation_key=f"ink_{colour.lower()}",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, colour=colour: _ink_level(d, colour),
    )
    for colour in INK_COLORS
)

DIAGNOSTIC_DESCRIPTIONS: tuple[EpsonSensorDescription, ...] = (
    EpsonSensorDescription(
        key=KEY_PRINTER_STATUS,
        translation_key="printer_status",
        value_fn=lambda d: _product(d, KEY_PRINTER_STATUS),
    ),
    EpsonSensorDescription(
        key=KEY_EPSON_CONNECT_STATUS,
        translation_key="epson_connect_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _product(d, KEY_EPSON_CONNECT_STATUS),
    ),
    EpsonSensorDescription(
        key=KEY_FIRST_PRINT_DATE,
        translation_key="first_print_date",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _maintenance(d, KEY_FIRST_PRINT_DATE),
    ),
    EpsonSensorDescription(
        key=KEY_FIRMWARE,
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _product(d, KEY_FIRMWARE),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Epson EcoTank sensors from a config entry."""

    coordinator: EpsonStatsCoordinator = hass.data[DOMAIN][entry.entry_id]

    descriptions: tuple[EpsonSensorDescription, ...] = (
        PAGE_DESCRIPTIONS
        + FUNCTION_DESCRIPTIONS
        + INK_DESCRIPTIONS
        + DIAGNOSTIC_DESCRIPTIONS
    )
    async_add_entities(
        EpsonStatsSensor(coordinator, description) for description in descriptions
    )


class EpsonStatsSensor(CoordinatorEntity[EpsonStatsCoordinator], SensorEntity):
    """Generic sensor backed by ``EpsonSensorDescription.value_fn``."""

    entity_description: EpsonSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EpsonStatsCoordinator,
        description: EpsonSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_unique_id}_{description.key}"

    @property
    def _device_unique_id(self) -> str:
        product = self.coordinator.data.get(DATA_PRODUCT, {}) if self.coordinator.data else {}
        ipp_uuid = self.coordinator.entry.data.get(CONF_IPP_UUID)
        if ipp_uuid:
            return ipp_uuid
        serial = product.get(KEY_SERIAL)
        if serial:
            return serial
        return self.coordinator.entry.data[CONF_HOST].lower()

    @property
    def device_info(self) -> DeviceInfo:
        product = self.coordinator.data.get(DATA_PRODUCT, {}) if self.coordinator.data else {}
        serial = product.get(KEY_SERIAL)
        ipp_uuid = self.coordinator.entry.data.get(CONF_IPP_UUID)

        # Reuse the Home Assistant core IPP integration's identifier scheme
        # ``("ipp", <printer-uuid>)``. When both integrations register the
        # same identifier, HA merges them into a single device-registry
        # entry, which is exactly what users want: one printer, both sets of
        # entities. We only fall back to our own identifier when no IPP UUID
        # could be discovered for this entry.
        identifiers: set[tuple[str, str]]
        if ipp_uuid:
            identifiers = {(IPP_DOMAIN, ipp_uuid)}
        else:
            identifiers = {(DOMAIN, self._device_unique_id)}

        connections: set[tuple[str, str]] = set()
        if product.get(KEY_MAC_ADDRESS):
            connections.add(("mac", product[KEY_MAC_ADDRESS]))

        return DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
            model=product.get(KEY_MODEL),
            name=self.coordinator.entry.data.get(CONF_NAME)
            or product.get(KEY_MODEL)
            or self.coordinator.entry.data[CONF_HOST],
            sw_version=product.get(KEY_FIRMWARE),
            serial_number=serial,
            connections=connections,
            configuration_url=f"{self.coordinator.base_url}/",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None
