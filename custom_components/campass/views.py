"""HTTP views for CamPass."""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from aiohttp import web
from homeassistant.components.camera import async_get_image
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

try:
    from homeassistant.components.camera import async_get_stream
except ImportError:
    async_get_stream = None

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_entry_by_slug(hass: HomeAssistant, slug: str):
    """Find a config entry by its slug."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("slug") == slug:
            return entry
    return None


def get_switch_entity(hass: HomeAssistant, entry):
    """Get the switch entity for a config entry."""
    entity_id = f"switch.campass_{entry.data['slug']}"
    state = hass.states.get(entity_id)
    if state:
        return state.state == "on"
    return False


def create_jwt_token(slug: str, secret: str) -> str:
    """Create a JWT token."""
    payload = {
        "slug": slug,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt_token(token: str, slug: str, secret: str) -> bool:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("slug") == slug
    except jwt.ExpiredSignatureError:
        _LOGGER.debug("JWT token expired")
        return False
    except jwt.InvalidTokenError:
        _LOGGER.debug("Invalid JWT token")
        return False


class CamPassRedirectView(HomeAssistantView):
    """Redirect /campass/{slug} to /campass/{slug}/."""

    requires_auth = False
    url = "/campass/{slug}"
    name = "api:campass:redirect"

    async def get(self, request, slug):
        """Redirect to trailing slash URL."""
        raise web.HTTPFound(f"/campass/{slug}/")


class CamPassPinView(HomeAssistantView):
    """View for PIN entry page."""

    requires_auth = False
    url = "/campass/{slug}/"
    name = "api:campass:pin"

    async def get(self, request, slug):
        """Serve the PIN entry page."""
        entry = get_entry_by_slug(request.app["hass"], slug)
        if not entry:
            return web.Response(text="Share not found", status=404)

        html_path = Path(__file__).parent / "frontend" / "pin.html"
        html = html_path.read_text()
        
        # Inject template variables
        html = html.replace("{{SHARE_NAME}}", entry.data["name"])
        html = html.replace("{{SLUG}}", slug)
        html = html.replace("{{AUTH_TYPE}}", entry.data.get("auth_type", "pin4"))
        
        return web.Response(text=html, content_type="text/html")


class CamPassViewerView(HomeAssistantView):
    """View for camera viewer page."""

    requires_auth = False
    url = "/campass/{slug}/viewer"
    name = "api:campass:viewer"

    async def get(self, request, slug):
        """Serve the viewer page."""
        entry = get_entry_by_slug(request.app["hass"], slug)
        if not entry:
            return web.Response(text="Share not found", status=404)

        # Verify JWT token
        cookie_name = f"campass_{slug}"
        token = request.cookies.get(cookie_name)
        secret = request.app["hass"].data[DOMAIN][entry.entry_id]["jwt_secret"]
        
        if not token or not verify_jwt_token(token, slug, secret):
            return web.Response(text="Unauthorized", status=401)

        html_path = Path(__file__).parent / "frontend" / "viewer.html"
        html = html_path.read_text()
        
        # Inject share name
        html = html.replace("{{SHARE_NAME}}", entry.data["name"])
        html = html.replace("{{SLUG}}", slug)
        
        return web.Response(text=html, content_type="text/html")


class CamPassAuthView(HomeAssistantView):
    """View for PIN authentication."""

    requires_auth = False
    url = "/campass/{slug}/api/auth"
    name = "api:campass:auth"

    async def post(self, request, slug):
        """Authenticate with PIN."""
        entry = get_entry_by_slug(request.app["hass"], slug)
        if not entry:
            return web.json_response({"error": "Share not found"}, status=404)

        try:
            data = await request.json()
            pin = data.get("pin", "")
        except Exception:
            return web.json_response({"error": "Invalid request"}, status=400)

        if pin == entry.data.get("passcode", entry.data.get("pin", "")):
            # Create JWT token
            secret = request.app["hass"].data[DOMAIN][entry.entry_id]["jwt_secret"]
            token = create_jwt_token(slug, secret)
            
            # Set cookie
            response = web.json_response({"success": True})
            response.set_cookie(
                f"campass_{slug}",
                token,
                max_age=86400,  # 24 hours
                httponly=True,
                samesite="Lax",
            )
            return response
        else:
            return web.json_response({"error": "Invalid PIN"}, status=401)


class CamPassStatusView(HomeAssistantView):
    """View for status endpoint."""

    requires_auth = False
    url = "/campass/{slug}/api/status"
    name = "api:campass:status"

    async def get(self, request, slug):
        """Get share status."""
        hass = request.app["hass"]
        entry = get_entry_by_slug(hass, slug)
        if not entry:
            return web.json_response({"error": "Share not found"}, status=404)

        # Verify JWT token
        cookie_name = f"campass_{slug}"
        token = request.cookies.get(cookie_name)
        secret = hass.data[DOMAIN][entry.entry_id]["jwt_secret"]
        
        if not token or not verify_jwt_token(token, slug, secret):
            return web.json_response({"error": "Unauthorized"}, status=401)

        # Check if sharing is enabled
        available = get_switch_entity(hass, entry)

        # Get camera info
        cameras = []
        for camera_id in entry.data["cameras"]:
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


class CamPassStreamInfoView(HomeAssistantView):
    """Return HLS stream URL for a camera."""

    requires_auth = False
    url = "/campass/{slug}/api/stream-info/{camera_id:.+}"
    name = "api:campass:stream_info"

    async def get(self, request, slug, camera_id):
        """Get stream URL for camera."""
        hass = request.app["hass"]
        entry = get_entry_by_slug(hass, slug)
        if not entry:
            return web.json_response({"error": "Share not found"}, status=404)

        cookie_name = f"campass_{slug}"
        token = request.cookies.get(cookie_name)
        secret = hass.data[DOMAIN][entry.entry_id]["jwt_secret"]
        if not token or not verify_jwt_token(token, slug, secret):
            return web.json_response({"error": "Unauthorized"}, status=401)

        if not get_switch_entity(hass, entry):
            return web.json_response({"error": "Sharing is disabled"}, status=403)

        if camera_id not in entry.data["cameras"]:
            return web.json_response({"error": "Camera not allowed"}, status=403)

        # Try to get HLS stream URL from HA's stream component
        try:
            camera = _get_camera_entity(hass, camera_id)
            if camera:
                stream = await camera.async_create_stream()
                if stream:
                    stream.add_provider("hls")
                    await stream.start()
                    url = stream.endpoint_url("hls")
                    _LOGGER.debug("HLS stream URL for %s: %s", camera_id, url)
                    return web.json_response({"type": "hls", "url": url})
        except Exception as err:
            _LOGGER.warning("Failed to create HLS stream for %s: %s", camera_id, err)

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
        entry = get_entry_by_slug(hass, slug)
        if not entry:
            return web.Response(text="Share not found", status=404)

        cookie_name = f"campass_{slug}"
        token = request.cookies.get(cookie_name)
        secret = hass.data[DOMAIN][entry.entry_id]["jwt_secret"]
        if not token or not verify_jwt_token(token, slug, secret):
            return web.Response(text="Unauthorized", status=401)

        if not get_switch_entity(hass, entry):
            return web.Response(text="Sharing is disabled", status=403)

        if camera_id not in entry.data["cameras"]:
            return web.Response(text="Camera not allowed", status=403)

        # Try native MJPEG
        camera = _get_camera_entity(hass, camera_id)
        if camera and hasattr(camera, "handle_async_mjpeg_stream"):
            try:
                return await camera.handle_async_mjpeg_stream(request)
            except Exception as err:
                _LOGGER.warning("Native MJPEG failed for %s: %s", camera_id, err)

        # Fallback: snapshot polling at 2fps
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
                    _LOGGER.error("Error fetching image from %s: %s", camera_id, err)
                    break
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        finally:
            await response.write_eof()

        return response


def _get_camera_entity(hass, camera_id):
    """Get camera entity object."""
    try:
        component = hass.data.get("camera")
        if component and hasattr(component, "get_entity"):
            return component.get_entity(camera_id)
    except (KeyError, AttributeError):
        pass
    return None
