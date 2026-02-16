"""Config flow for CamPass integration."""
import re
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_PERSISTENT_SESSION, DOMAIN, AUTH_TYPE_PIN4, AUTH_TYPE_PIN6, AUTH_TYPE_ALPHANUMERIC

_LOGGER = logging.getLogger(__name__)

AUTH_TYPES = {
    AUTH_TYPE_PIN4: "4-digit passcode",
    AUTH_TYPE_PIN6: "6-digit passcode",
    AUTH_TYPE_ALPHANUMERIC: "Alphanumeric password",
}


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text


def validate_slug(slug: str) -> bool:
    """Validate slug format."""
    if not slug or len(slug) > 32:
        return False
    return bool(re.match(r'^[a-z0-9\-]+$', slug))


def validate_passcode(passcode: str, auth_type: str) -> bool:
    """Validate passcode based on auth type."""
    if not passcode:
        return False
    if auth_type == AUTH_TYPE_PIN4:
        return bool(re.match(r'^\d{4}$', passcode))
    if auth_type == AUTH_TYPE_PIN6:
        return bool(re.match(r'^\d{6}$', passcode))
    if auth_type == AUTH_TYPE_ALPHANUMERIC:
        return len(passcode) >= 4
    return False


class CamPassConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CamPass."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step - name, auth type, passcode."""
        errors = {}

        if user_input is not None:
            auth_type = user_input["auth_type"]
            passcode = user_input["passcode"]

            if not validate_passcode(passcode, auth_type):
                if auth_type == AUTH_TYPE_PIN4:
                    errors["passcode"] = "invalid_pin4"
                elif auth_type == AUTH_TYPE_PIN6:
                    errors["passcode"] = "invalid_pin6"
                else:
                    errors["passcode"] = "invalid_alphanumeric"

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
                self._data = {
                    "name": user_input["name"],
                    "auth_type": auth_type,
                    "passcode": passcode,
                    "slug": slug,
                    CONF_PERSISTENT_SESSION: user_input.get(CONF_PERSISTENT_SESSION, False),
                }
                return await self.async_step_cameras()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("auth_type", default=AUTH_TYPE_PIN4): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in AUTH_TYPES.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("passcode"): str,
                vol.Optional("slug"): str,
                vol.Optional(CONF_PERSISTENT_SESSION, default=False): bool,
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
                self._data["cameras"] = cameras
                return self.async_create_entry(
                    title=self._data["name"],
                    data=self._data,
                )

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
        return CamPassOptionsFlow()


class CamPassOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for CamPass."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            auth_type = user_input["auth_type"]
            passcode = user_input["passcode"]

            if not validate_passcode(passcode, auth_type):
                if auth_type == AUTH_TYPE_PIN4:
                    errors["passcode"] = "invalid_pin4"
                elif auth_type == AUTH_TYPE_PIN6:
                    errors["passcode"] = "invalid_pin6"
                else:
                    errors["passcode"] = "invalid_alphanumeric"

            slug = user_input.get("slug", self.config_entry.data.get("slug"))
            if not validate_slug(slug):
                errors["slug"] = "invalid_slug"

            if not errors:
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id != self.config_entry.entry_id:
                        if entry.data.get("slug") == slug:
                            errors["slug"] = "slug_taken"
                            break

            cameras = user_input.get("cameras", [])
            if not cameras:
                errors["cameras"] = "no_cameras_selected"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        "name": user_input["name"],
                        "auth_type": auth_type,
                        "passcode": passcode,
                        "slug": slug,
                        "cameras": cameras,
                        CONF_PERSISTENT_SESSION: user_input.get(CONF_PERSISTENT_SESSION, False),
                    },
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "name",
                    default=self.config_entry.data.get("name"),
                ): str,
                vol.Required(
                    "auth_type",
                    default=self.config_entry.data.get("auth_type", AUTH_TYPE_PIN4),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in AUTH_TYPES.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    "passcode",
                    default=self.config_entry.data.get("passcode", self.config_entry.data.get("pin", "")),
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
                vol.Optional(
                    CONF_PERSISTENT_SESSION,
                    default=self.config_entry.data.get(CONF_PERSISTENT_SESSION, False),
                ): bool,
            }),
            errors=errors,
        )
