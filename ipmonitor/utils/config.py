\
import os

from ipmonitor import app_globals as G

def _bool_to_str(v: bool) -> str:
    return "true" if v else "false"

def _str_to_bool(s: str) -> bool:
    return str(s).strip().lower() == "true"

def _csv_to_list(s: str):
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def load_settings():
    if not os.path.exists(G.SETTINGS_FILE):
        save_settings()
        return

    rec_tmp = None
    table_cols_tmp = None

    with open(G.SETTINGS_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "=" not in line:
                continue
            k, v = line.strip().split("=", 1)
            v = v.strip()

            try:
                if k == "config_file":
                    G.CONFIG_FILE = v or G.DEFAULT_CONFIG_FILE
                elif k == "log_file":
                    G.LOG_FILE = v or G.DEFAULT_LOG_FILE

                elif k == "interval":
                    G.MONITOR_INTERVAL = max(1, int(v))
                elif k == "threshold":
                    G.FAILURE_THRESHOLD = min(1.0, max(0.0, int(v) / 100))
                elif k == "window_minutes":
                    G.WINDOW_SECONDS = max(60, int(v) * 60)

                elif k == "log_retention_days":
                    G.LOG_RETENTION_DAYS = max(0, int(v))
                elif k == "log_max_size_mb":
                    G.LOG_MAX_SIZE_MB = max(0, int(v))

                elif k == "mail_type":
                    G.MAIL_TYPE = v if v in ("standard", "ses") else "standard"
                elif k == "mail_enabled":
                    G.MAIL_ENABLED = _str_to_bool(v)
                elif k == "mail_smtp_host":
                    G.MAIL_SMTP_HOST = v
                elif k == "mail_smtp_port":
                    G.MAIL_SMTP_PORT = int(v)
                elif k == "mail_use_tls":
                    G.MAIL_USE_TLS = _str_to_bool(v)
                elif k == "mail_use_ssl":
                    G.MAIL_USE_SSL = _str_to_bool(v)

                elif k == "mail_smtp_user":
                    G.MAIL_SMTP_USER = v
                elif k == "mail_smtp_password":
                    G.MAIL_SMTP_PASSWORD = v
                elif k == "mail_from":
                    G.MAIL_FROM = v

                elif k == "mail_recipients":
                    rec_tmp = v

                elif k == "mail_subject_prefix":
                    G.MAIL_SUBJECT_PREFIX = v

                elif k == "mail_auto_report":
                    G.MAIL_AUTO_REPORT = _str_to_bool(v)
                elif k == "mail_report_interval_min":
                    G.MAIL_REPORT_INTERVAL_MIN = max(1, int(v))

                elif k == "report_include_table":
                    G.REPORT_INCLUDE_DEVICE_TABLE = _str_to_bool(v)

                elif k == "report_attach_csv":
                    G.REPORT_ATTACH_CSV = _str_to_bool(v)
                elif k == "report_format_html":
                    G.REPORT_FORMAT_HTML = _str_to_bool(v)
                elif k == "report_format_plain":
                    G.REPORT_FORMAT_PLAIN = _str_to_bool(v)

                elif k == "report_table_columns":
                    table_cols_tmp = v

            except Exception:
                pass

    if rec_tmp is not None:
        G.MAIL_RECIPIENTS_LIST = _csv_to_list(rec_tmp)

    if table_cols_tmp is not None:
        cols = _csv_to_list(table_cols_tmp)
        valid = {k for k, _ in G.REPORT_COLUMNS_CATALOG}
        cols = [c for c in cols if c in valid]
        if cols:
            G.REPORT_TABLE_COLUMNS = cols

    if not G.REPORT_FORMAT_HTML and not G.REPORT_FORMAT_PLAIN:
        G.REPORT_FORMAT_PLAIN = True

    if not G.REPORT_TABLE_COLUMNS:
        G.REPORT_TABLE_COLUMNS = ["name", "ip", "live", "fail_pct"]

def save_settings():
    with open(G.SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(f"config_file={G.CONFIG_FILE}\n")
        f.write(f"log_file={G.LOG_FILE}\n")

        f.write(f"interval={G.MONITOR_INTERVAL}\n")
        f.write(f"threshold={int(G.FAILURE_THRESHOLD * 100)}\n")
        f.write(f"window_minutes={G.WINDOW_SECONDS // 60}\n")

        f.write(f"log_retention_days={G.LOG_RETENTION_DAYS}\n")
        f.write(f"log_max_size_mb={G.LOG_MAX_SIZE_MB}\n")

        f.write(f"mail_type={G.MAIL_TYPE}\n")
        f.write(f"mail_enabled={_bool_to_str(G.MAIL_ENABLED)}\n")
        f.write(f"mail_smtp_host={G.MAIL_SMTP_HOST}\n")
        f.write(f"mail_smtp_port={G.MAIL_SMTP_PORT}\n")
        f.write(f"mail_use_tls={_bool_to_str(G.MAIL_USE_TLS)}\n")
        f.write(f"mail_use_ssl={_bool_to_str(G.MAIL_USE_SSL)}\n")

        f.write(f"mail_smtp_user={G.MAIL_SMTP_USER}\n")
        f.write(f"mail_smtp_password={G.MAIL_SMTP_PASSWORD}\n")
        f.write(f"mail_from={G.MAIL_FROM}\n")

        f.write("mail_recipients=" + ",".join(G.MAIL_RECIPIENTS_LIST) + "\n")
        f.write(f"mail_subject_prefix={G.MAIL_SUBJECT_PREFIX}\n")

        f.write(f"mail_auto_report={_bool_to_str(G.MAIL_AUTO_REPORT)}\n")
        f.write(f"mail_report_interval_min={G.MAIL_REPORT_INTERVAL_MIN}\n")

        f.write(f"report_include_table={_bool_to_str(G.REPORT_INCLUDE_DEVICE_TABLE)}\n")
        f.write(f"report_table_columns={','.join(G.REPORT_TABLE_COLUMNS)}\n")

        f.write(f"report_attach_csv={_bool_to_str(G.REPORT_ATTACH_CSV)}\n")
        f.write(f"report_format_html={_bool_to_str(G.REPORT_FORMAT_HTML)}\n")
        f.write(f"report_format_plain={_bool_to_str(G.REPORT_FORMAT_PLAIN)}\n")
