\
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.core.devices import load_devices, rebuild_groups_from_devices, save_devices
from ipmonitor.core.monitor import start_monitoring_thread, compute_failure_rate
from ipmonitor.reports.report_state import load_report_state, save_report_state
from ipmonitor.reports.report_builder import build_snapshot_for_names, build_report_text_and_html, build_report_csv_bytes
from ipmonitor.reports.mailer import send_email_report, explain_mail_error
from ipmonitor.utils.config import load_settings
from ipmonitor.utils.logger import configure_logger, prune_log_file, logger
from ipmonitor.ui import context
from ipmonitor.ui.settings_window import open_settings
from ipmonitor.ui.device_dialogs import (
    open_groups_manager, open_add_or_edit_device, open_bulk_change_group, export_csv_visible
)
from ipmonitor.ui.log_windows import open_log_window, open_device_log
from ipmonitor.ui.critical_window import open_critical_window
from ipmonitor.ui.graphs import open_uptime_graph_multi_with_selector

# ===================== SORTING =====================
def safe_int_from_percent(s: str):
    if not s or s == "-":
        return -1
    try:
        return int(s.replace("%", "").strip())
    except Exception:
        return -1

def safe_int_from_ms(s: str):
    if not s or s == "-":
        return -1
    try:
        return int(s.replace("ms", "").replace(" ", "").strip())
    except Exception:
        return -1

def sort_key_for_item(values, col_name: str):
    name = values[0]
    if col_name == "Nome":
        return name.lower()
    if col_name == "IP":
        return values[1]
    if col_name == "Gruppo":
        return values[2].lower()
    if col_name == "Stato":
        order = {"UP": 0, "UNKNOWN": 1, "DOWN": 2}
        return order.get(values[3], 99)
    if col_name == "Fail% (1h)":
        return safe_int_from_percent(values[4])
    if col_name == "Ultimo ping":
        with state.state_lock:
            ts = (state.last_state.get(name) or {}).get("ts")
        return ts or 0
    if col_name == "RTT":
        return safe_int_from_ms(values[6])
    return values

def sort_tree(col_name: str, reverse: bool, toggle: bool = True):
    if toggle:
        if state.current_sort_col == col_name:
            reverse = not state.current_sort_reverse
        else:
            reverse = False

    state.current_sort_col = col_name
    state.current_sort_reverse = reverse

    tree = context.tree
    if tree is None:
        return

    try:
        items = [(iid, tree.item(iid, "values")) for iid in tree.get_children("")]
        items.sort(key=lambda x: sort_key_for_item(x[1], col_name), reverse=reverse)
        for idx, (iid, _) in enumerate(items):
            tree.move(iid, "", idx)
    except Exception:
        pass

def setup_sort_headers():
    tree = context.tree
    if tree is None:
        return
    for col in context.columns:
        tree.heading(col, text=col, command=lambda c=col: sort_tree(c, False, toggle=True))

# ===================== FILTER =====================
def device_matches_filter(name: str):
    if state.selected_group_filter == "Tutti":
        return True
    info = state.devices.get(name, {})
    return (info.get("group") or "Default") == state.selected_group_filter

def refresh_groups_ui():
    vals = ["Tutti"] + sorted(state.groups)
    context.group_filter_cb["values"] = vals
    if state.selected_group_filter not in vals:
        set_group_filter("Tutti")
    else:
        context.group_filter_cb.set(state.selected_group_filter)

def set_group_filter(value: str):
    state.selected_group_filter = value
    if context.group_filter_cb is not None:
        context.group_filter_cb.set(value)
    update_tree()

def on_group_filter_changed(event=None):
    set_group_filter(context.group_filter_cb.get() or "Tutti")

# ===================== SELECTION HELPERS =====================
def get_selected_device_names():
    tree = context.tree
    if tree is None:
        return []
    try:
        sels = tree.selection()
    except Exception:
        return []
    if not sels:
        return []
    names = []
    for item_id in sels:
        vals = tree.item(item_id, "values")
        if vals:
            names.append(vals[0])
    return names

def get_visible_device_names_from_tree():
    tree = context.tree
    if tree is None:
        return []
    names = []
    try:
        for iid in tree.get_children(""):
            vals = tree.item(iid, "values")
            if vals:
                names.append(vals[0])
    except Exception:
        pass
    return names

# ===================== UI: TREEVIEW LIVE =====================
def update_tree():
    tree = context.tree
    if tree is None:
        return

    selected_names = set(get_selected_device_names())

    try:
        tree.delete(*tree.get_children())
    except Exception:
        return

    with state.state_lock:
        items = [(n, info) for n, info in state.devices.items() if device_matches_filter(n)]
        ls = dict(state.last_state)

    name_to_iid = {}

    for name, info in items:
        ip = info.get("ip", "?")
        grp = info.get("group", "Default")

        st = ls.get(name, {"ts": None, "ok": None, "rtt": None})
        ok = st.get("ok", None)
        ts = st.get("ts", None)
        rtt = st.get("rtt", None)

        rate, _, _ = compute_failure_rate(name)
        rate_str = "-" if rate is None else f"{int(rate*100)}%"

        if ok is True:
            status = "UP"
            tag = "up"
            rtt_str = "-" if rtt is None else f"{int(rtt*1000)} ms"
        elif ok is False:
            status = "DOWN"
            tag = "down"
            rtt_str = "-"
        else:
            status = "UNKNOWN"
            tag = "unknown"
            rtt_str = "-"

        if rate is not None and rate > G.FAILURE_THRESHOLD:
            tag = "critical"

        iid = tree.insert("", tk.END, values=(name, ip, grp, status, rate_str, "-" if not ts else time.strftime("%H:%M:%S", time.localtime(ts)), rtt_str), tags=(tag,))
        name_to_iid[name] = iid

    if state.current_sort_col is not None:
        sort_tree(state.current_sort_col, state.current_sort_reverse, toggle=False)

    try:
        tree.selection_remove(tree.selection())
        for n in selected_names:
            iid = name_to_iid.get(n)
            if iid:
                tree.selection_add(iid)
        for n in selected_names:
            iid = name_to_iid.get(n)
            if iid:
                tree.see(iid)
                break
    except Exception:
        pass

def schedule_tree_refresh():
    update_tree()
    context.root.after(2000, schedule_tree_refresh)

# ===================== ACTIONS =====================
def reload_devices_from_config():
    new_devices = load_devices()
    with state.state_lock:
        state.devices = new_devices
        rebuild_groups_from_devices()
        for d in state.devices:
            state.results.setdefault(d, [])
            state.last_state.setdefault(d, {"ts": None, "ok": None, "rtt": None})
            state.report_state["last_critical_status"].setdefault(d, False)
            state.report_state["last_report_live_status"].setdefault(d, "UNKNOWN")
            state.report_state["critical_enter_counts"].setdefault(d, 0)
    refresh_groups_ui()
    update_tree()
    save_report_state()

def start_monitoring():
    with state.state_lock:
        if not state.devices:
            messagebox.showerror("Errore", "Nessun dispositivo configurato")
            return
    if state.monitoring_active:
        messagebox.showinfo("Info", "Monitoraggio già avviato")
        return
    start_monitoring_thread(save_report_state)
    messagebox.showinfo("Avvio", "Monitoraggio avviato")

def add_device():
    open_add_or_edit_device(context.root, "add", refresh_groups_ui, update_tree)

def edit_selected_device():
    names = get_selected_device_names()
    if not names:
        messagebox.showinfo("Info", "Seleziona un dispositivo.")
        return
    if len(names) > 1:
        messagebox.showinfo("Info", "Per la modifica singola seleziona solo un dispositivo.")
        return
    name = names[0]
    with state.state_lock:
        info = state.devices.get(name, {"ip": "", "group": "Default"})
    open_add_or_edit_device(context.root, "edit", refresh_groups_ui, update_tree, name_default=name, ip_default=info.get("ip", ""), group_default=info.get("group", "Default"))

def delete_selected_device():
    names = get_selected_device_names()
    if not names:
        messagebox.showinfo("Info", "Seleziona uno o più dispositivi (CTRL/SHIFT).")
        return
    if not messagebox.askyesno("Conferma", f"Eliminare {len(names)} dispositivo/i selezionato/i?"):
        return
    with state.state_lock:
        for name in names:
            state.devices.pop(name, None)
            state.results.pop(name, None)
            state.last_state.pop(name, None)
            state.report_state["last_critical_status"].pop(name, None)
            state.report_state["last_report_live_status"].pop(name, None)
            state.report_state["critical_enter_counts"].pop(name, None)
        save_devices()
    rebuild_groups_from_devices()
    refresh_groups_ui()
    update_tree()
    save_report_state()

def on_double_click_open_log(_event):
    names = get_selected_device_names()
    if names:
        open_device_log(names[0])

# --- Mail actions (UI decides the "view") ---
def send_report_all(manual: bool = True):
    try:
        with state.state_lock:
            all_names = list(state.devices.keys())
        snapshot = build_snapshot_for_names(all_names)
        plain, html, critical_now = build_report_text_and_html(snapshot)
        subject = f"{G.MAIL_SUBJECT_PREFIX} Report stato dispositivi (TUTTI)"
        csv_bytes = build_report_csv_bytes(snapshot) if G.REPORT_ATTACH_CSV else None
        csv_filename = f"ip_monitor_report_ALL_{time.strftime('%Y%m%d_%H%M%S')}.csv" if G.REPORT_ATTACH_CSV else None

        send_email_report(subject, plain, html, csv_bytes, csv_filename)

        state.report_state["last_report_ts"] = time.time()
        state.report_state["last_report_live_status"] = {r["name"]: r["live"] for r in snapshot}
        state.report_state["last_report_critical_set"] = list(sorted(critical_now, key=lambda s: s.lower()))
        state.report_state["critical_enter_counts"] = {}
        save_report_state()

        logger.info("Report mail (tutti) inviato con successo.")
        if manual:
            messagebox.showinfo("OK", "Report (tutti) inviato via email.")
    except Exception as e:
        logger.warning(f"Invio report mail fallito: {e}")
        if manual:
            messagebox.showerror("Errore mail", explain_mail_error(e))

def send_report_view(manual: bool = True):
    try:
        visible_names = get_visible_device_names_from_tree()
        if not visible_names:
            messagebox.showinfo("Info", "Nessun dispositivo visibile nella vista corrente.")
            return

        snapshot = build_snapshot_for_names(visible_names)
        plain, html, _ = build_report_text_and_html(snapshot)
        subject = f"{G.MAIL_SUBJECT_PREFIX} Report vista (Filtro: {state.selected_group_filter})"
        csv_bytes = build_report_csv_bytes(snapshot) if G.REPORT_ATTACH_CSV else None
        csv_filename = f"ip_monitor_report_VIEW_{time.strftime('%Y%m%d_%H%M%S')}.csv" if G.REPORT_ATTACH_CSV else None

        send_email_report(subject, plain, html, csv_bytes, csv_filename)
        logger.info("Report mail (vista) inviato con successo.")
        if manual:
            messagebox.showinfo("OK", "Report (vista corrente) inviato via email.")
    except Exception as e:
        logger.warning(f"Invio report mail (vista) fallito: {e}")
        if manual:
            messagebox.showerror("Errore mail", explain_mail_error(e))

# ===================== AUTO REPORT + LOG PRUNE scheduling =====================
def schedule_auto_report():
    try:
        if state.auto_report_after_id is not None:
            context.root.after_cancel(state.auto_report_after_id)
            state.auto_report_after_id = None
    except Exception:
        state.auto_report_after_id = None

    if not G.MAIL_AUTO_REPORT:
        return

    interval_ms = max(1, int(G.MAIL_REPORT_INTERVAL_MIN)) * 60 * 1000

    def tick():
        try:
            if G.MAIL_AUTO_REPORT and G.MAIL_ENABLED:
                send_report_all(manual=False)
        except Exception:
            pass
        try:
            state.auto_report_after_id = context.root.after(interval_ms, tick)
        except Exception:
            state.auto_report_after_id = None

    state.auto_report_after_id = context.root.after(interval_ms, tick)

def schedule_log_prune():
    try:
        prune_log_file()
    except Exception:
        pass
    try:
        state.log_prune_after_id = context.root.after(G.LOG_PRUNE_EVERY_SEC * 1000, schedule_log_prune)
    except Exception:
        state.log_prune_after_id = None

# ===================== START APP =====================
def start_app():
    root = tk.Tk()
    context.root = root
    root.title("Monitoraggio IP")
    root.geometry("1280x700")

    load_settings()
    configure_logger()
    prune_log_file()
    load_report_state()

    state.devices = load_devices()
    rebuild_groups_from_devices()

    with state.state_lock:
        for d in state.devices:
            state.results.setdefault(d, [])
            state.last_state.setdefault(d, {"ts": None, "ok": None, "rtt": None})
            state.report_state["last_critical_status"].setdefault(d, False)
            state.report_state["last_report_live_status"].setdefault(d, "UNKNOWN")
            state.report_state["critical_enter_counts"].setdefault(d, 0)

    save_report_state()

    top = tk.Frame(root)
    top.pack(fill="x", padx=10, pady=8)

    tk.Button(top, text="Configurazione", command=lambda: open_settings(reload_devices_from_config, schedule_auto_report)).pack(side="left", padx=4)
    tk.Button(top, text="Gruppi", command=lambda: open_groups_manager(root, refresh_groups_ui, update_tree)).pack(side="left", padx=4)

    tk.Button(top, text="Aggiungi", command=add_device).pack(side="left", padx=10)
    tk.Button(top, text="Modifica", command=edit_selected_device).pack(side="left", padx=4)
    tk.Button(top, text="Elimina", command=delete_selected_device).pack(side="left", padx=4)
    tk.Button(top, text="Cambia gruppo selezionati", command=lambda: open_bulk_change_group(root, get_selected_device_names, refresh_groups_ui, update_tree)).pack(side="left", padx=12)

    tk.Button(top, text="Ricarica da config.cfg", command=reload_devices_from_config).pack(side="left", padx=12)

    tk.Button(top, text="Avvia monitoraggio", command=start_monitoring).pack(side="left", padx=12)
    tk.Button(top, text="Dispositivi critici", command=open_critical_window).pack(side="left", padx=4)
    tk.Button(top, text="Log completo", command=open_log_window).pack(side="left", padx=4)

    tk.Button(top, text="Esporta CSV (visibili)", command=lambda: export_csv_visible(root, context.tree, context.columns)).pack(side="right", padx=4)
    tk.Button(top, text="Grafico (selettore)", command=lambda: open_uptime_graph_multi_with_selector(get_selected_device_names, get_visible_device_names_from_tree)).pack(side="right", padx=4)
    tk.Button(top, text="Invia report (vista)", command=lambda: send_report_view(manual=True)).pack(side="right", padx=8)
    tk.Button(top, text="Invia report (tutti)", command=lambda: send_report_all(manual=True)).pack(side="right", padx=8)

    filter_row = tk.Frame(root)
    filter_row.pack(fill="x", padx=12)

    tk.Label(filter_row, text="Filtro gruppo:").pack(side="left")
    group_filter_cb = ttk.Combobox(filter_row, state="readonly", width=25)
    context.group_filter_cb = group_filter_cb
    group_filter_cb.pack(side="left", padx=8)
    group_filter_cb.bind("<<ComboboxSelected>>", on_group_filter_changed)

    info = tk.Label(
        root,
        text="CTRL/SHIFT selezione multipla. Doppio click su device: log del device. Grafico: selettore (critici/selezionati/vista).",
        fg="gray"
    )
    info.pack(anchor="w", padx=12, pady=(6, 0))

    columns = ("Nome", "IP", "Gruppo", "Stato", "Fail% (1h)", "Ultimo ping", "RTT")
    context.columns = columns
    tree = ttk.Treeview(root, columns=columns, show="headings", height=20, selectmode="extended")
    context.tree = tree
    tree.pack(expand=True, fill="both", padx=10, pady=10)

    for c in columns:
        tree.column(c, width=160 if c != "Nome" else 280, anchor="w")

    tree.column("Stato", width=90)
    tree.column("Fail% (1h)", width=110)
    tree.column("Ultimo ping", width=110)
    tree.column("RTT", width=90)

    tree.tag_configure("up", foreground="green")
    tree.tag_configure("down", foreground="red")
    tree.tag_configure("unknown", foreground="gray")
    tree.tag_configure("critical", foreground="red")

    tree.bind("<Double-1>", on_double_click_open_log)

    setup_sort_headers()
    refresh_groups_ui()
    set_group_filter("Tutti")

    schedule_tree_refresh()
    schedule_auto_report()
    schedule_log_prune()

    root.mainloop()
