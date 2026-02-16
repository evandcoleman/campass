"""Switch platform for CamPass."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CamPass switch from a config entry."""
    async_add_entities([CamPassSwitch(entry)], True)


class CamPassSwitch(SwitchEntity):
    """Representation of a CamPass share switch."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.data['slug']}"
        self._attr_name = f"CamPass: {entry.data['name']}"
        self.entity_id = f"switch.campass_{entry.data['slug']}"
        self._is_on = False  # Default to OFF for security

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:camera-lock-open" if self._is_on else "mdi:camera-lock"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self._is_on = True
        self.async_write_ha_state()
        _LOGGER.info(
            "CamPass share '%s' enabled (slug: %s)",
            self._entry.data["name"],
            self._entry.data["slug"],
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()
        _LOGGER.info(
            "CamPass share '%s' disabled (slug: %s)",
            self._entry.data["name"],
            self._entry.data["slug"],
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {
            "slug": self._entry.data["slug"],
            "cameras": self._entry.data["cameras"],
            "url": f"/campass/{self._entry.data['slug']}/",
        }
