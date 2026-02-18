"""Logbook support for CamPass."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN

EVENT_CAMPASS_ACCESS = "campass_access"

MESSAGES = {
    "auth_success": "authenticated to '{share}' share from {ip}",
    "auth_failure": "failed authentication to '{share}' share from {ip}",
    "camera_view": "viewed camera {camera_id} on '{share}' share from {ip}",
}


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe CamPass logbook events."""

    @callback
    def async_describe_campass_event(event: Event):
        """Describe a CamPass access event."""
        data = event.data
        event_type = data.get("type", "unknown")
        share = data.get("share", "unknown")
        ip = data.get("ip", "unknown")
        camera_id = data.get("camera_id", "")

        template = MESSAGES.get(event_type, "performed '{type}' on share '{share}'")
        message = template.format(
            share=share,
            ip=ip,
            camera_id=camera_id,
            type=event_type,
        )

        return {
            LOGBOOK_ENTRY_NAME: "CamPass",
            LOGBOOK_ENTRY_MESSAGE: message,
        }

    async_describe_event(DOMAIN, EVENT_CAMPASS_ACCESS, async_describe_campass_event)
