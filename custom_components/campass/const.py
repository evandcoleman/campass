"""Constants for the CamPass integration."""

DOMAIN = "campass"

AUTH_TYPE_PIN4 = "pin4"
AUTH_TYPE_PIN6 = "pin6"
AUTH_TYPE_ALPHANUMERIC = "alphanumeric"

CONF_SESSION_DURATION = "session_duration"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"

SESSION_DURATIONS = {
    "1h": ("1 hour", 3600),
    "24h": ("24 hours", 86400),
    "7d": ("7 days", 604800),
    "30d": ("30 days", 2592000),
    "1y": ("1 year", 31536000),
    "never": ("Never expires", None),
}
