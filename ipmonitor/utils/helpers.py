\
import time

def now_str(ts: float | None):
    if not ts:
        return "-"
    return time.strftime("%H:%M:%S", time.localtime(ts))

def dt_str(ts: float | None):
    if not ts:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

def esc_html(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
