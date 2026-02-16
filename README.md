# 🎥 CamPass

**PIN-protected camera sharing for Home Assistant**

CamPass lets you create secure, PIN-protected links to share your Home Assistant cameras with family, friends, pet sitters, or anyone who needs temporary access — without giving them full Home Assistant access.

## ✨ Features

- 📱 **Mobile-first design** — Beautiful, responsive PIN pad and viewer
- 🔐 **PIN authentication** — 4-digit PIN protection for each share
- 🎛️ **Multiple instances** — Create unlimited shares, each with its own PIN and camera selection
- 🎚️ **Toggle control** — Enable/disable sharing instantly with a switch entity
- 📹 **Multi-camera support** — Share one or multiple cameras per link
- 🔗 **Clean URLs** — Friendly URLs like `/campass/emily/` or `/campass/pet-sitter/`
- 🍪 **JWT authentication** — Secure, 24-hour session cookies
- 🎨 **Native HA integration** — Fully integrated with Home Assistant's config flow UI
- 📺 **MJPEG streaming** — Real-time camera feeds with fallback to snapshot polling

## 🚀 Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click the **⋮** menu (top right) → **Custom repositories**
3. Add repository URL: `https://github.com/evandcoleman/campass`
4. Category: **Integration**
5. Click **Add**
6. Search for **CamPass** and click **Download**
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/campass` folder from this repository
2. Copy it to your Home Assistant `custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── campass/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── switch.py
           ├── const.py
           ├── views.py
           ├── strings.json
           ├── translations/
           │   └── en.json
           └── frontend/
               ├── pin.html
               └── viewer.html
   ```
3. Restart Home Assistant

## ⚙️ Configuration

### Creating a Share

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **CamPass**
4. Follow the setup wizard:
   - **Step 1**: Enter a name (e.g., "Emily's Access"), 4-digit PIN, and optional URL slug
   - **Step 2**: Select which cameras to share
5. Click **Submit**

A switch entity will be created: `switch.campass_<slug>`

### Updating a Share

1. Go to the CamPass integration card
2. Click **Configure** on the share you want to update
3. Modify the name, PIN, slug, or camera selection
4. Click **Submit**

### Multiple Shares

You can create as many shares as you need! Each one gets:
- Its own unique URL
- Its own PIN
- Its own camera selection
- Its own switch entity

**Example:**
- `/campass/emily/` — PIN: 1234 — Cameras: Nursery, Living Room
- `/campass/pet-sitter/` — PIN: 5678 — Cameras: Kitchen, Front Door
- `/campass/guest/` — PIN: 9999 — Cameras: Entryway

## 📖 Usage

### Sharing with Someone

1. **Enable the share**: Turn on the switch entity (`switch.campass_<slug>`)
2. **Share the URL**: Send them `http://your-home-assistant:8123/campass/<slug>/`
3. **Share the PIN**: Give them the 4-digit PIN (via text, call, etc.)
4. **Monitor access**: The switch entity shows the URL and camera list as attributes
5. **Disable when done**: Turn off the switch to revoke access

### Viewer Experience

1. Recipient opens the URL
2. They see a beautiful PIN pad (dark gradient, iOS-style)
3. They enter the 4-digit PIN
4. On success, they're redirected to the camera viewer
5. Viewer shows:
   - Share name + live indicator in header
   - Camera selector (if multiple cameras)
   - Full-screen MJPEG stream
   - "Camera Not Available" message if sharing is disabled
6. Session lasts 24 hours (or until the switch is turned off)

### URL Structure

- **PIN pad**: `http://your-ha:8123/campass/<slug>/`
- **Viewer**: `http://your-ha:8123/campass/<slug>/viewer` (requires auth)
- **API endpoints**:
  - `POST /campass/<slug>/api/auth` — PIN validation
  - `GET /campass/<slug>/api/status` — Share status + camera list
  - `GET /campass/<slug>/api/stream/<camera_entity_id>` — MJPEG stream

## 🔒 Security

- **No HA credentials required** — Viewers never see your Home Assistant login
- **PIN authentication** — Each share requires a 4-digit PIN
- **JWT session cookies** — Secure, httpOnly, SameSite=Lax, 24-hour expiry
- **Per-instance secrets** — Each share has its own JWT signing secret
- **Switch control** — Instantly enable/disable sharing (defaults to OFF on restart)
- **Camera whitelisting** — Only selected cameras are accessible via the share
- **No persistence** — Switch state resets to OFF on Home Assistant restart (secure by default)

### Best Practices

- Use unique PINs for each share
- Disable shares when not needed
- Use descriptive names to track who has access
- Consider creating temporary shares for short-term needs (e.g., pet sitter during vacation)
- Change PINs periodically via the options flow

## 📸 Screenshots

### PIN Entry Page
A dark, gradient background with an iOS-style 4-digit PIN pad. Clean, minimal, mobile-optimized.

### Camera Viewer (Single Camera)
Full-screen MJPEG stream with share name header and pulsing "LIVE" indicator.

### Camera Viewer (Multiple Cameras)
Horizontal scrollable camera selector at the top, active camera shown below in full-screen.

### Home Assistant Config
Native config flow integration with two-step setup (name/PIN/slug, then camera selection).

## 🛠️ Technical Details

- **Platforms**: `switch`
- **Dependencies**: `camera`
- **Requirements**: `PyJWT>=2.0.0`
- **Integration Type**: `service`
- **IoT Class**: `local_push`
- **Config Flow**: ✅ Yes
- **Multiple Instances**: ✅ Yes

### Architecture

- Each config entry is a separate share instance
- Switch entity controls sharing on/off
- HTTP views registered once, handle all slugs dynamically
- JWT secrets generated per-instance at setup
- MJPEG streaming with native `handle_async_mjpeg_stream` support + snapshot polling fallback

## 📝 License

MIT License

Copyright (c) 2026 Evan Coleman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 🙏 Credits

Built with ❤️ for the Home Assistant community.

## 🐛 Issues & Contributions

Found a bug or have a feature request? Please open an issue on GitHub!

Contributions are welcome — feel free to submit a pull request.

---

**Enjoy secure camera sharing! 🎥🔐**
