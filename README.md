# 🔐 CamPass

[![GitHub Release](https://img.shields.io/github/v/release/evandcoleman/campass?style=flat-square)](https://github.com/evandcoleman/campass/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/evandcoleman/campass?style=flat-square)](LICENSE)

PIN-protected camera sharing for [Home Assistant](https://www.home-assistant.io/). Share live camera feeds with family, guests, or service providers — no HA account required.

## Features

- 📱 **iPhone-style PIN pad** — clean, mobile-first unlock screen
- 🔑 **Flexible auth** — 4-digit, 6-digit, or alphanumeric passcodes
- 📷 **Multi-camera support** — select which cameras each person can see
- 🔄 **Multiple shares** — create separate links with different PINs and cameras
- 🔘 **Switch entity** — enable/disable each share instantly (great for automations)
- 🔒 **Secure by default** — JWT cookies, per-share secrets, sharing off on restart

## Use Cases

- Baby monitor access for family
- Pet camera for the dog walker
- Front door cam for a delivery window
- Guest camera access during a stay

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → **Custom repositories**
2. Add `evandcoleman/campass` with category **Integration**
3. Install **CamPass** and restart Home Assistant

### Manual

1. Copy `custom_components/campass` to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Integrations → Add Integration → CamPass**
2. Enter a name (e.g. "Guest"), choose auth type, set a passcode
3. Select which cameras to share
4. Turn on the `switch.campass_<name>` entity to enable sharing

Repeat to create additional shares with different settings.

## Usage

Share the URL with your guest:

```
http://YOUR_HA_ADDRESS:8123/campass/guest/
```

They enter the passcode and see the live camera feed. When you turn off the switch, they see "Camera not available."

### Automations

Use the switch entity to schedule access:

```yaml
automation:
  - alias: "Enable baby cam sharing at bedtime"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.campass_guest

  - alias: "Disable baby cam sharing in morning"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.campass_guest
```

## Security

- Passcodes are validated server-side
- Sessions use signed JWT tokens (httpOnly cookies, 24h expiry)
- Each share has its own cryptographic secret
- Sharing defaults to **off** on every HA restart
- Camera access is restricted to the configured whitelist

## License

MIT © 2026 Evan Coleman
