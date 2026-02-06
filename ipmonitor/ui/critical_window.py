\
import tkinter as tk
from tkinter import messagebox

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.core.monitor import compute_failure_rate
from ipmonitor.ui import context
from ipmonitor.core.monitor import is_critical

def _close_critical_window():
    try:
        if state.critical_win and state.critical_after_id:
            state.critical_win.after_cancel(state.critical_after_id)
    except Exception:
        pass
    state.critical_after_id = None
    try:
        if state.critical_win and state.critical_win.winfo_exists():
            state.critical_win.destroy()
    except Exception:
        pass
    state.critical_win = None

def open_critical_window():
    if state.critical_win is not None:
        try:
            if state.critical_win.winfo_exists():
                state.critical_win.lift()
                state.critical_win.focus_force()
                return
        except Exception:
            state.critical_win = None

    root = context.root
    if root is None:
        return

    state.critical_win = tk.Toplevel(root)
    state.critical_win.title("Dispositivi critici (> soglia nell’ultima ora)")
    state.critical_win.geometry("820x420")
    state.critical_win.protocol("WM_DELETE_WINDOW", _close_critical_window)

    lb = tk.Listbox(state.critical_win, width=120)
    lb.pack(expand=True, fill="both", padx=10, pady=10)

    def refresh():
        try:
            if not state.critical_win or not state.critical_win.winfo_exists():
                return

            lb.delete(0, tk.END)

            with state.state_lock:
                names = list(state.devices.keys())

            for n in names:
                # group filter
                if state.selected_group_filter != "Tutti":
                    info = state.devices.get(n, {})
                    if (info.get("group") or "Default") != state.selected_group_filter:
                        continue

                rate, _, _ = compute_failure_rate(n)
                if rate is None:
                    continue
                if rate > G.FAILURE_THRESHOLD:
                    ip = state.devices.get(n, {}).get("ip", "?")
                    grp = state.devices.get(n, {}).get("group", "Default")
                    lb.insert(tk.END, f"{n} [{ip}] ({grp}) → {int(rate*100)}% fallimenti")
        except Exception:
            pass

        try:
            if state.critical_win and state.critical_win.winfo_exists():
                state.critical_after_id = state.critical_win.after(5000, refresh)
        except Exception:
            state.critical_after_id = None

    refresh()
