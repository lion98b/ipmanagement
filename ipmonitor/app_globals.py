\
"""
Global settings & defaults for IP Monitor.

This module intentionally keeps "script-style" globals so the refactor can stay
behavior-identical to the original monolith.
"""
# ===================== FILE DEFAULT (override via settings.cfg) =====================
DEFAULT_CONFIG_FILE = "config.cfg"
DEFAULT_LOG_FILE = "ping_monitor.log"
SETTINGS_FILE = "settings.cfg"
REPORT_STATE_FILE = "report_state.json"

# Runtime (set by load_settings)
CONFIG_FILE = DEFAULT_CONFIG_FILE
LOG_FILE = DEFAULT_LOG_FILE

# ===================== DEFAULT SETTINGS =====================
MONITOR_INTERVAL = 10          # seconds
FAILURE_THRESHOLD = 0.5        # 50%
WINDOW_SECONDS = 3600          # 1 hour

# Log retention
LOG_RETENTION_DAYS = 14        # 0 = unlimited
LOG_MAX_SIZE_MB = 20           # 0 = unlimited
LOG_PRUNE_EVERY_SEC = 300      # every 5 min

# ===================== MAIL SETTINGS =====================
MAIL_TYPE = "ses"  # "standard" | "ses"
MAIL_ENABLED = False
MAIL_SMTP_HOST = "email-smtp.eu-central-1.amazonaws.com"
MAIL_SMTP_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False

MAIL_SMTP_USER = ""
MAIL_SMTP_PASSWORD = ""
MAIL_FROM = ""

MAIL_RECIPIENTS_LIST = []
MAIL_SUBJECT_PREFIX = "[IP Monitor]"
MAIL_AUTO_REPORT = False
MAIL_REPORT_INTERVAL_MIN = 60

# ===================== REPORT OPTIONS =====================
REPORT_INCLUDE_LIVE_CHANGES = True
REPORT_INCLUDE_CRITICAL_SUMMARY = True
REPORT_INCLUDE_NEWLY_CRITICAL = True
REPORT_INCLUDE_RECOVERED = True

REPORT_INCLUDE_DEVICE_TABLE = True

REPORT_ATTACH_CSV = True
REPORT_FORMAT_HTML = True
REPORT_FORMAT_PLAIN = True

REPORT_COLUMNS_CATALOG = [
    ("name", "Nome"),
    ("ip", "IP"),
    ("group", "Gruppo"),
    ("live", "LIVE"),
    ("fail_pct", "Fail%"),
    ("fails_total", "Fails/Total"),
    ("rtt_ms", "RTT"),
    ("last_ping", "Ultimo ping"),
    ("critical", "Critico"),
    ("enter_counts", "Ingressi critico"),
]
REPORT_TABLE_COLUMNS = ["name", "ip", "group", "live", "fail_pct", "fails_total", "rtt_ms", "last_ping", "critical", "enter_counts"]
