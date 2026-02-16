"""Config flow for CamPass integration."""
import re
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9\-]', '', text)
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Strip leading/trailing hyphens
    text = text.strip('-')
    return text


def validate_slug(slug: str) -> bool:
    """Validate slug format."""
    if not slug:
        return False
    if len(slug) > 32:
        return False
    return bool(re.match(r'^[a-z0-9\-]+$', slug))


def validate_pin(pin: str) -> bool:
    """Validate PIN is exactly 4 digits."""
    return bool(re.match(r'^\d{4}$', pin))


class CamPassConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CamPass."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step - name and PIN."""
        errors = {}

        if user_input is not None:
            # Validate PIN
            if not validate_pin(user_input["pin"]):
                errors["pin"] = "invalid_pin"
            
            # Generate or validate slug
            if user_input.get("slug"):
                slug = user_input["slug"]
                if not validate_slug(slug):
                    errors["slug"] = "invalid_slug"
            else:
                slug = slugify(user_input["name"])
                if not slug:
                    slug = "share"
            
            # Check slug uniqueness
            if not errors:
                for entry in self._async_current_entries():
                    if entry.data.get("slug") == slug:
                        errors["slug"] = "slug_taken"
                        break
            
            if not errors:
                # Store data and move to camera selection
                self._data = {
                    "name": user_input["name"],
                    "pin": user_input["pin"],
                    "slug": slug,
                }
                return await self.async_step_cameras()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("pin"): str,
                vol.Optional("slug"): str,
            }),
            errors=errors,
        )

    async def async_step_cameras(self, user_input: dict[str, Any] | None = None):
        """Handle camera selection step."""
        errors = {}

        if user_input is not None:
            cameras = user_input.get("cameras", [])
            
            if not cameras:
                errors["cameras"] = "no_cameras_selected"
            else:
                # Complete the config entry
                self._data["cameras"] = cameras
                return self.async_create_entry(
                    title=self._data["name"],
                    data=self._data,
                )

        # Get available camera entities
        camera_entities = [
            entity_id
            for entity_id in self.hass.states.async_entity_ids("camera")
        ]

        if not camera_entities:
            return self.async_abort(reason="no_cameras")

        return self.async_show_form(
            step_id="cameras",
            data_schema=vol.Schema({
                vol.Required("cameras"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="camera",
                        multiple=True,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={"name": self._data["name"]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return CamPassOptionsFlow(config_entry)


class CamPassOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for CamPass."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate PIN
            if not validate_pin(user_input["pin"]):
                errors["pin"] = "invalid_pin"
            
            # Validate slug
            slug = user_input.get("slug", self.config_entry.data.get("slug"))
            if not validate_slug(slug):
                errors["slug"] = "invalid_slug"
            
            # Check slug uniqueness (excluding current entry)
            if not errors:
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id != self.config_entry.entry_id:
                        if entry.data.get("slug") == slug:
                            errors["slug"] = "slug_taken"
                            break
            
            # Validate cameras
            cameras = user_input.get("cameras", [])
            if not cameras:
                errors["cameras"] = "no_cameras_selected"
            
            if not errors:
                # Update config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        "name": user_input["name"],
                        "pin": user_input["pin"],
                        "slug": slug,
                        "cameras": cameras,
                    },
                )
                return self.async_create_entry(title="", data={})

        # Get available camera entities
        camera_entities = [
            entity_id
            for entity_id in self.hass.states.async_entity_ids("camera")
        ]

        if not camera_entities:
            return self.async_abort(reason="no_cameras")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "name",
                    default=self.config_entry.data.get("name"),
                ): str,
                vol.Required(
                    "pin",
                    default=self.config_entry.data.get("pin"),
                ): str,
                vol.Required(
                    "slug",
                    default=self.config_entry.data.get("slug"),
                ): str,
                vol.Required(
                    "cameras",
                    default=self.config_entry.data.get("cameras", []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="camera",
                        multiple=True,
                    )
                ),
            }),
            errors=errors,
        )
