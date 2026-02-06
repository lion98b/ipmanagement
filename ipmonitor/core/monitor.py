\
import time
import threading

from ping3 import ping

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.utils.logger import logger

def clean_old_results_locked():
    cutoff = time.time() - G.WINDOW_SECONDS
    for name in list(state.results.keys()):
        state.results[name] = [(t, r) for t, r in state.results[name] if t >= cutoff]

def compute_failure_rate(name: str):
    with state.state_lock:
        data = state.results.get(name, [])
        if not data:
            return None, 0, 0
        fails = sum(1 for _, r in data if r == 0)
        total = len(data)
        return (fails / total), fails, total

def is_critical(name: str):
    rate, _, total = compute_failure_rate(name)
    if rate is None or total == 0:
        return False
    return rate > G.FAILURE_THRESHOLD

def update_critical_transition(name: str):
    try:
        current = is_critical(name)
        prev = bool(state.report_state["last_critical_status"].get(name, False))
        if (not prev) and current:
            state.report_state["critical_enter_counts"][name] = int(state.report_state["critical_enter_counts"].get(name, 0)) + 1
        state.report_state["last_critical_status"][name] = current
    except Exception:
        pass

def monitor_loop(save_report_state_cb):
    state.monitoring_active = True
    while state.monitoring_active:
        with state.state_lock:
            dev_snapshot = [(n, info["ip"]) for n, info in state.devices.items()]

        t0 = time.time()
        for name, ip in dev_snapshot:
            ts = time.time()
            try:
                rtt = ping(ip, timeout=2)
                ok = isinstance(rtt, (int, float)) and rtt > 0
            except Exception:
                rtt = None
                ok = False

            with state.state_lock:
                state.results.setdefault(name, []).append((ts, 1 if ok else 0))
                state.last_state[name] = {"ts": ts, "ok": ok, "rtt": rtt}
                clean_old_results_locked()

            logger.info(f"{name} [{ip}] - {'Ping riuscito' if ok else 'Ping fallito'}")
            update_critical_transition(name)

        # persist report state each loop (as in original)
        try:
            save_report_state_cb()
        except Exception:
            pass

        elapsed = time.time() - t0
        time.sleep(max(0.2, G.MONITOR_INTERVAL - elapsed))

def start_monitoring_thread(save_report_state_cb):
    t = threading.Thread(target=monitor_loop, args=(save_report_state_cb,), daemon=True)
    t.start()
    return t
