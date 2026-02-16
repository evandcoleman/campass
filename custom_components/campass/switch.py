"""Switch platform for CamPass."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CamPass switch from a config entry."""
    async_add_entities([CamPassSwitch(entry)], True)


class CamPassSwitch(SwitchEntity, RestoreEntity):
    """Representation of a CamPass share switch."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.data['slug']}"
        self._attr_name = f"CamPass: {entry.data['name']}"
        self.entity_id = f"switch.campass_{entry.data['slug']}"
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        """Restore last known state on startup."""
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"

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

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {
            "slug": self._entry.data["slug"],
            "cameras": self._entry.data["cameras"],
            "url": f"/campass/{self._entry.data['slug']}/",
        }
