"""HTTP views for CamPass."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from aiohttp import web
from homeassistant.components.camera import async_get_image
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_SESSION_DURATION, DOMAIN, SESSION_DURATIONS

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


def get_entry_by_slug(hass: HomeAssistant, slug: str):
    """Find a config entry by its slug."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("slug") == slug:
            return entry
    return None


def get_switch_entity_id(entry) -> str:
    """Get the switch entity ID for a config entry."""
    return f"switch.campass_{entry.data['slug']}"


def is_sharing_enabled(hass: HomeAssistant, entry) -> bool:
    """Check if sharing is enabled for a config entry."""
    state = hass.states.get(get_switch_entity_id(entry))
    return state is not None and state.state == "on"


def create_jwt_token(slug: str, secret: str, duration_seconds: int | None = 86400) -> str:
    """Create a JWT token. None duration = no expiration."""
    payload = {"slug": slug}
    if duration_seconds is not None:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt_token(token: str, slug: str, secret: str) -> bool:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("slug") == slug
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


def _get_entry_and_verify(hass, slug, cookie_prefix="campass"):
    """Get config entry and verify JWT. Returns (entry, error_response) tuple."""
    entry = get_entry_by_slug(hass, slug)
    if not entry:
        return None, web.json_response({"error": "Share not found"}, status=404)

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data or "jwt_secret" not in entry_data:
        return None, web.json_response({"error": "Not configured"}, status=500)

    return entry, None


def _verify_cookie(request, slug, entry, hass):
    """Verify the JWT cookie for a request. Returns True if valid."""
    token = request.cookies.get(f"campass_{slug}")
    if not token:
        return False
    secret = hass.data[DOMAIN][entry.entry_id]["jwt_secret"]
    return verify_jwt_token(token, slug, secret)


def _get_camera_entity(hass, camera_id):
    """Get camera entity object from HA's camera component."""
    try:
        component = hass.data.get("camera")
        if component and hasattr(component, "get_entity"):
            return component.get_entity(camera_id)
    except (KeyError, AttributeError):
        pass
    return None


def _serve_html(filename: str, replacements: dict) -> web.Response:
    """Serve an HTML file with template replacements."""
    html = (FRONTEND_DIR / filename).read_text()
    for key, value in replacements.items():
        html = html.replace(f"{{{{{key}}}}}", value)
    return web.Response(text=html, content_type="text/html")


class CamPassRedirectView(HomeAssistantView):
    """Redirect /campass/{slug} to /campass/{slug}/."""

    requires_auth = False
    url = "/campass/{slug}"
    name = "api:campass:redirect"

    async def get(self, request, slug):
        """Redirect to trailing slash URL."""
        raise web.HTTPFound(f"/campass/{slug}/")


class CamPassPinView(HomeAssistantView):
    """Serve the PIN entry page."""

    requires_auth = False
    url = "/campass/{slug}/"
    name = "api:campass:pin"

    async def get(self, request, slug):
        """Serve the PIN entry page."""
        entry = get_entry_by_slug(request.app["hass"], slug)
        if not entry:
            return web.Response(text="Share not found", status=404)

        return _serve_html("pin.html", {
            "SHARE_NAME": entry.data["name"],
            "SLUG": slug,
            "AUTH_TYPE": entry.data.get("auth_type", "pin4"),
        })


class CamPassViewerView(HomeAssistantView):
    """Serve the camera viewer page."""

    requires_auth = False
    url = "/campass/{slug}/viewer"
    name = "api:campass:viewer"

    async def get(self, request, slug):
        """Serve the viewer page."""
        hass = request.app["hass"]
        entry = get_entry_by_slug(hass, slug)
        if not entry:
            return web.Response(text="Share not found", status=404)

        if not _verify_cookie(request, slug, entry, hass):
            # Redirect to PIN page instead of showing raw 401
            raise web.HTTPFound(f"/campass/{slug}/")

        return _serve_html("viewer.html", {
            "SHARE_NAME": entry.data["name"],
            "SLUG": slug,
        })


class CamPassAuthView(HomeAssistantView):
    """Handle PIN authentication."""

    requires_auth = False
    url = "/campass/{slug}/api/auth"
    name = "api:campass:auth"

    async def post(self, request, slug):
        """Authenticate with PIN."""
        hass = request.app["hass"]
        entry, err = _get_entry_and_verify(hass, slug)
        if err:
            return err

        try:
            data = await request.json()
            pin = data.get("pin", "")
        except Exception:
            return web.json_response({"error": "Invalid request"}, status=400)

        stored_passcode = entry.data.get("passcode", entry.data.get("pin", ""))
        if pin == stored_passcode:
            secret = hass.data[DOMAIN][entry.entry_id]["jwt_secret"]
            duration_key = entry.data.get(CONF_SESSION_DURATION, "24h")
            _, duration_seconds = SESSION_DURATIONS.get(duration_key, ("24 hours", 86400))
            token = create_jwt_token(slug, secret, duration_seconds=duration_seconds)

            response = web.json_response({"success": True})
            # Cookie max_age matches JWT duration, or 10 years for never-expires
            max_age = duration_seconds if duration_seconds is not None else 315360000
            response.set_cookie(
                f"campass_{slug}",
                token,
                max_age=max_age,
                httponly=True,
                samesite="Lax",
                secure=request.secure,
            )
            return response

        return web.json_response({"error": "Invalid PIN"}, status=401)


class CamPassStatusView(HomeAssistantView):
    """Return camera availability status."""

    requires_auth = False
    url = "/campass/{slug}/api/status"
    name = "api:campass:status"

    async def get(self, request, slug):
        """Get share status."""
        hass = request.app["hass"]
        entry, err = _get_entry_and_verify(hass, slug)
        if err:
            return err

        if not _verify_cookie(request, slug, entry, hass):
            return web.json_response({"error": "Unauthorized"}, status=401)

        available = is_sharing_enabled(hass, entry)

        cameras = []
        for camera_id in entry.data.get("cameras", []):
            state = hass.states.get(camera_id)
            if state:
                cameras.append({
                    "entity_id": camera_id,
                    "name": state.attributes.get("friendly_name", camera_id),
                })

        return web.json_response({
            "available": available,
            "cameras": cameras,
        })


class CamPassEventsView(HomeAssistantView):
    """Server-Sent Events for real-time status updates."""

    requires_auth = False
    url = "/campass/{slug}/api/events"
    name = "api:campass:events"

    async def get(self, request, slug):
        """Stream status events."""
        hass = request.app["hass"]
        entry, err = _get_entry_and_verify(hass, slug)
        if err:
            return err

        if not _verify_cookie(request, slug, entry, hass):
            return web.Response(text="Unauthorized", status=401)

        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"
        await response.prepare(request)

        available = is_sharing_enabled(hass, entry)
        await response.write(
            f"data: {{\"available\": {str(available).lower()}}}\n\n".encode()
        )

        switch_id = get_switch_entity_id(entry)
        change_event = asyncio.Event()
        state_data = {"available": available}

        def on_state_change(ev):
            new_state = ev.data.get("new_state")
            if new_state:
                state_data["available"] = new_state.state == "on"
                change_event.set()

        unsub = async_track_state_change_event(hass, [switch_id], on_state_change)

        try:
            while True:
                try:
                    await asyncio.wait_for(change_event.wait(), timeout=15.0)
                    change_event.clear()
                    await response.write(
                        f"data: {{\"available\": {str(state_data['available']).lower()}}}\n\n".encode()
                    )
                except asyncio.TimeoutError:
                    await response.write(b": keepalive\n\n")
        except (asyncio.CancelledError, ConnectionResetError, ConnectionError):
            pass
        finally:
            unsub()

        return response


class CamPassStreamInfoView(HomeAssistantView):
    """Return stream URL info for a camera."""

    requires_auth = False
    url = "/campass/{slug}/api/stream-info/{camera_id:.+}"
    name = "api:campass:stream_info"

    async def get(self, request, slug, camera_id):
        """Get stream URL for camera."""
        hass = request.app["hass"]
        entry, err = _get_entry_and_verify(hass, slug)
        if err:
            return err

        if not _verify_cookie(request, slug, entry, hass):
            return web.json_response({"error": "Unauthorized"}, status=401)

        if not is_sharing_enabled(hass, entry):
            return web.json_response({"error": "Sharing is disabled"}, status=403)

        if camera_id not in entry.data.get("cameras", []):
            return web.json_response({"error": "Camera not allowed"}, status=403)

        # Try HLS via HA's stream component
        try:
            camera = _get_camera_entity(hass, camera_id)
            if camera:
                stream = await camera.async_create_stream()
                if stream:
                    stream.add_provider("hls")
                    await stream.start()
                    url = stream.endpoint_url("hls")
                    return web.json_response({"type": "hls", "url": url})
        except Exception as err:
            _LOGGER.debug("HLS stream unavailable for %s: %s", camera_id, err)

        # Fallback to MJPEG
        return web.json_response({
            "type": "mjpeg",
            "url": f"/campass/{slug}/api/stream/{camera_id}",
        })


class CamPassStreamView(HomeAssistantView):
    """Proxy MJPEG camera stream (fallback)."""

    requires_auth = False
    url = "/campass/{slug}/api/stream/{camera_id:.+}"
    name = "api:campass:stream"

    async def get(self, request, slug, camera_id):
        """Proxy camera stream."""
        hass = request.app["hass"]
        entry, err = _get_entry_and_verify(hass, slug)
        if err:
            return web.Response(text="Share not found", status=404)

        if not _verify_cookie(request, slug, entry, hass):
            return web.Response(text="Unauthorized", status=401)

        if not is_sharing_enabled(hass, entry):
            return web.Response(text="Sharing is disabled", status=403)

        if camera_id not in entry.data.get("cameras", []):
            return web.Response(text="Camera not allowed", status=403)

        # Try native MJPEG
        camera = _get_camera_entity(hass, camera_id)
        if camera and hasattr(camera, "handle_async_mjpeg_stream"):
            try:
                return await camera.handle_async_mjpeg_stream(request)
            except Exception as err:
                _LOGGER.warning("Native MJPEG failed for %s: %s", camera_id, err)

        # Fallback: snapshot polling
        response = web.StreamResponse()
        response.content_type = "multipart/x-mixed-replace; boundary=frame"
        await response.prepare(request)

        try:
            while True:
                try:
                    image = await async_get_image(hass, camera_id)
                    await response.write(
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + image.content
                        + b"\r\n"
                    )
                except Exception as err:
                    _LOGGER.error("Snapshot error for %s: %s", camera_id, err)
                    break
                await asyncio.sleep(0.5)
        except (asyncio.CancelledError, ConnectionResetError, ConnectionError):
            pass
        finally:
            await response.write_eof()

        return response
