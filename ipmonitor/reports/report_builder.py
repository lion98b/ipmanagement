\
import csv
import io
import time

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.core.monitor import compute_failure_rate
from ipmonitor.utils.helpers import now_str, dt_str, esc_html

def build_snapshot_for_names(names):
    with state.state_lock:
        ls = dict(state.last_state)

    rows = []
    for name in sorted(names, key=lambda s: s.lower()):
        info = state.devices.get(name)
        if not info:
            continue
        ip = info.get("ip", "?")
        grp = info.get("group", "Default")

        st = ls.get(name, {"ts": None, "ok": None, "rtt": None})
        ok = st.get("ok", None)
        ts = st.get("ts", None)
        rtt = st.get("rtt", None)

        live = "UP" if ok is True else ("DOWN" if ok is False else "UNKNOWN")
        rate, fails, total = compute_failure_rate(name)
        fail_pct = None if rate is None else int(rate * 100)
        critical = (rate is not None and rate > G.FAILURE_THRESHOLD)

        rtt_ms = None
        if isinstance(rtt, (int, float)) and rtt > 0:
            rtt_ms = int(rtt * 1000)

        rows.append({
            "name": name,
            "ip": ip,
            "group": grp,
            "live": live,
            "last_ping_ts": ts,
            "rtt_ms": rtt_ms,
            "fails": fails,
            "total": total,
            "fail_pct": fail_pct,
            "critical": critical
        })
    return rows

def _col_value_for_row(col_key: str, r: dict, enter_counts: dict):
    if col_key == "name":
        return r["name"]
    if col_key == "ip":
        return r["ip"]
    if col_key == "group":
        return r["group"]
    if col_key == "live":
        return r["live"]
    if col_key == "fail_pct":
        return "-" if r["fail_pct"] is None else f"{r['fail_pct']}%"
    if col_key == "fails_total":
        return "-" if r["fail_pct"] is None else f"{r['fails']}/{r['total']}"
    if col_key == "rtt_ms":
        return "-" if r["rtt_ms"] is None else f"{r['rtt_ms']} ms"
    if col_key == "last_ping":
        return "-" if not r["last_ping_ts"] else now_str(r["last_ping_ts"])
    if col_key == "critical":
        return "SI" if r["critical"] else "NO"
    if col_key == "enter_counts":
        return str(int(enter_counts.get(r["name"], 0) or 0))
    return ""

def build_report_text_and_html(snapshot_rows):
    ts_now = time.time()
    threshold_pct = int(G.FAILURE_THRESHOLD * 100)
    window_min = G.WINDOW_SECONDS // 60
    critical_now = [r["name"] for r in snapshot_rows if r["critical"]]
    enter_counts = state.report_state.get("critical_enter_counts", {}) or {}

    plain = ""
    if G.REPORT_FORMAT_PLAIN:
        lines = []
        lines.append("Report IP Monitor")
        lines.append(f"Generato: {dt_str(ts_now)}")
        lines.append(f"Finestra: ultimi {window_min} minuti")
        lines.append(f"Soglia critico: > {threshold_pct}% fallimenti")
        lines.append("")
        if G.REPORT_INCLUDE_DEVICE_TABLE:
            lines.append("TABELLA DISPOSITIVI:")
            header = " | ".join([lbl for k, lbl in G.REPORT_COLUMNS_CATALOG if k in G.REPORT_TABLE_COLUMNS])
            lines.append(header)
            lines.append("-" * len(header))
            for r in snapshot_rows:
                row = " | ".join(_col_value_for_row(k, r, enter_counts) for k in G.REPORT_TABLE_COLUMNS)
                lines.append(row)
        plain = "\n".join(lines)

    html = ""
    if G.REPORT_FORMAT_HTML:
        html_parts = []
        html_parts.append("<html><body style='font-family:Segoe UI, Arial, sans-serif; font-size:14px;'>")
        html_parts.append("<h2>Report IP Monitor</h2>")
        html_parts.append("<div>")
        html_parts.append(f"<b>Generato:</b> {esc_html(dt_str(ts_now))}<br>")
        html_parts.append(f"<b>Finestra:</b> ultimi {window_min} minuti<br>")
        html_parts.append(f"<b>Soglia critico:</b> &gt; {threshold_pct}% fallimenti<br>")
        html_parts.append("</div><hr>")

        if G.REPORT_INCLUDE_DEVICE_TABLE:
            html_parts.append("<h3>Tabella dispositivi</h3>")
            html_parts.append("<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse; width:100%;'>")
            ths = [lbl for k, lbl in G.REPORT_COLUMNS_CATALOG if k in G.REPORT_TABLE_COLUMNS]
            html_parts.append("<tr style='background:#f3f3f3;'>" + "".join(f"<th>{esc_html(h)}</th>" for h in ths) + "</tr>")

            for r in snapshot_rows:
                row_style = ""
                if r["critical"]:
                    row_style = " style='background:#ffe5e5;'"
                elif r["live"] == "DOWN":
                    row_style = " style='background:#fff3cd;'"
                elif r["live"] == "UP":
                    row_style = " style='background:#e9f7ef;'"

                tds = []
                for k in G.REPORT_TABLE_COLUMNS:
                    val = _col_value_for_row(k, r, enter_counts)
                    tds.append(f"<td>{esc_html(val)}</td>")
                html_parts.append(f"<tr{row_style}>" + "".join(tds) + "</tr>")
            html_parts.append("</table>")

        html_parts.append("</body></html>")
        html = "".join(html_parts)

    return plain, html, critical_now

def build_report_csv_bytes(snapshot_rows):
    enter_counts = state.report_state.get("critical_enter_counts", {}) or {}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    headers = [lbl for k, lbl in G.REPORT_COLUMNS_CATALOG if k in G.REPORT_TABLE_COLUMNS]
    w.writerow(headers)
    for r in snapshot_rows:
        w.writerow([_col_value_for_row(k, r, enter_counts) for k in G.REPORT_TABLE_COLUMNS])
    return buf.getvalue().encode("utf-8")
