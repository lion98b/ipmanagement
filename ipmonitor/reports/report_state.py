\
import json
import os

from ipmonitor import app_globals as G
from ipmonitor.core import state

def load_report_state():
    if not os.path.exists(G.REPORT_STATE_FILE):
        save_report_state()
        return
    try:
        with open(G.REPORT_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            state.report_state["last_report_ts"] = float(data.get("last_report_ts", 0) or 0)
            state.report_state["critical_enter_counts"] = dict(data.get("critical_enter_counts", {}) or {})
            state.report_state["last_critical_status"] = dict(data.get("last_critical_status", {}) or {})
            state.report_state["last_report_live_status"] = dict(data.get("last_report_live_status", {}) or {})
            state.report_state["last_report_critical_set"] = list(data.get("last_report_critical_set", []) or [])
    except Exception:
        state.report_state = {
            "last_report_ts": 0,
            "critical_enter_counts": {},
            "last_critical_status": {},
            "last_report_live_status": {},
            "last_report_critical_set": []
        }
        save_report_state()

def save_report_state():
    try:
        with open(G.REPORT_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state.report_state, f, indent=2)
    except Exception:
        pass
