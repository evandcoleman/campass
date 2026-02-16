"""The CamPass integration."""
import logging
import secrets

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .views import (
    CamPassAuthView,
    CamPassPinView,
    CamPassStatusView,
    CamPassStreamView,
    CamPassViewerView,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the CamPass component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CamPass from a config entry."""
    # Generate JWT secret for this instance if not already present
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    if "jwt_secret" not in hass.data[DOMAIN][entry.entry_id]:
        hass.data[DOMAIN][entry.entry_id]["jwt_secret"] = secrets.token_urlsafe(32)
    
    # Register HTTP views (only once, they handle all slugs)
    if "_views_registered" not in hass.data[DOMAIN]:
        hass.http.register_view(CamPassPinView())
        hass.http.register_view(CamPassViewerView())
        hass.http.register_view(CamPassAuthView())
        hass.http.register_view(CamPassStatusView())
        hass.http.register_view(CamPassStreamView())
        hass.data[DOMAIN]["_views_registered"] = True
        _LOGGER.info("CamPass HTTP views registered")
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok
