\
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import time

from ipmonitor.core import state
from ipmonitor.core.devices import save_devices, rebuild_groups_from_devices
from ipmonitor.reports.report_state import save_report_state

def open_groups_manager(root, refresh_groups_ui, update_tree):
    win = tk.Toplevel(root)
    win.title("Gestione gruppi")
    win.geometry("420x320")

    tk.Label(win, text="Gruppi esistenti").pack(pady=(10, 0))
    lb = tk.Listbox(win, width=45, height=10)
    lb.pack(padx=10, pady=8, expand=True, fill="both")

    def refresh_list():
        lb.delete(0, tk.END)
        for g in sorted(state.groups):
            lb.insert(tk.END, g)

    frm = tk.Frame(win)
    frm.pack(fill="x", padx=10, pady=6)

    tk.Label(frm, text="Nuovo gruppo:").pack(side="left")
    new_e = tk.Entry(frm)
    new_e.pack(side="left", padx=6, fill="x", expand=True)

    def add_group():
        g = new_e.get().strip()
        if not g:
            return
        if g == "Tutti":
            messagebox.showerror("Errore", "Nome gruppo non valido")
            return
        with state.state_lock:
            state.groups.add(g)
        new_e.delete(0, tk.END)
        refresh_groups_ui()
        refresh_list()

    def delete_group():
        sel = lb.curselection()
        if not sel:
            return
        g = lb.get(sel[0])
        if g == "Default":
            messagebox.showinfo("Info", "Il gruppo 'Default' non può essere eliminato.")
            return

        if not messagebox.askyesno("Conferma", f"Eliminare il gruppo '{g}'?\nI dispositivi verranno spostati in 'Default'."):
            return

        with state.state_lock:
            for name, info in state.devices.items():
                if info.get("group") == g:
                    info["group"] = "Default"
            state.groups.discard(g)
            save_devices()

        rebuild_groups_from_devices()
        refresh_groups_ui()
        refresh_list()
        update_tree()

    tk.Button(win, text="AGGIUNGI", command=add_group).pack(pady=4)
    tk.Button(win, text="ELIMINA GRUPPO", command=delete_group).pack(pady=4)

    refresh_list()

def open_add_or_edit_device(root, mode: str, refresh_groups_ui, update_tree, name_default: str = "", ip_default: str = "", group_default: str = "Default"):
    win = tk.Toplevel(root)
    win.title("Aggiungi dispositivo" if mode == "add" else "Modifica dispositivo")
    win.geometry("360x290")

    tk.Label(win, text="Nome dispositivo").pack(pady=(10, 0))
    name_e = tk.Entry(win)
    name_e.pack()
    name_e.insert(0, name_default)

    tk.Label(win, text="IP dispositivo").pack(pady=(10, 0))
    ip_e = tk.Entry(win)
    ip_e.pack()
    ip_e.insert(0, ip_default)

    tk.Label(win, text="Gruppo").pack(pady=(10, 0))
    group_cb = ttk.Combobox(win, values=sorted(state.groups), state="readonly")
    group_cb.pack()
    group_cb.set(group_default if group_default in state.groups else "Default")

    if mode == "edit":
        name_e.config(state="disabled")

    def save_dev():
        name = name_e.get().strip()
        ip = ip_e.get().strip()
        grp = (group_cb.get() or "Default").strip() or "Default"

        if not name or not ip:
            messagebox.showerror("Errore", "Nome e IP obbligatori")
            return
        if grp == "Tutti":
            messagebox.showerror("Errore", "Gruppo non valido")
            return

        with state.state_lock:
            state.groups.add(grp)

            if mode == "add":
                if name in state.devices:
                    messagebox.showerror("Errore", "Esiste già un dispositivo con questo nome")
                    return
                state.devices[name] = {"ip": ip, "group": grp}
                state.results.setdefault(name, [])
                state.last_state.setdefault(name, {"ts": None, "ok": None, "rtt": None})
                state.report_state["last_critical_status"].setdefault(name, False)
                state.report_state["last_report_live_status"].setdefault(name, "UNKNOWN")
            else:
                if name not in state.devices:
                    messagebox.showerror("Errore", "Dispositivo non trovato")
                    return
                state.devices[name]["ip"] = ip
                state.devices[name]["group"] = grp

            save_devices()

        rebuild_groups_from_devices()
        refresh_groups_ui()
        update_tree()
        save_report_state()
        win.destroy()

    tk.Button(win, text="AGGIUNGI" if mode == "add" else "SALVA", command=save_dev).pack(pady=18)

def open_bulk_change_group(root, get_selected_names, refresh_groups_ui, update_tree):
    names = get_selected_names()
    if not names:
        messagebox.showinfo("Info", "Seleziona uno o più dispositivi (CTRL/SHIFT).")
        return

    win = tk.Toplevel(root)
    win.title("Cambia gruppo selezionati")
    win.geometry("360x170")

    tk.Label(win, text=f"Dispositivi selezionati: {len(names)}").pack(pady=(12, 6))
    tk.Label(win, text="Nuovo gruppo:").pack()

    cb = ttk.Combobox(win, values=sorted(state.groups), state="readonly", width=30)
    cb.pack(pady=6)
    cb.set("Default")

    def apply():
        new_g = (cb.get() or "Default").strip() or "Default"
        if new_g == "Tutti":
            messagebox.showerror("Errore", "Gruppo non valido")
            return

        with state.state_lock:
            state.groups.add(new_g)
            for n in names:
                if n in state.devices:
                    state.devices[n]["group"] = new_g
            save_devices()

        rebuild_groups_from_devices()
        refresh_groups_ui()
        update_tree()
        win.destroy()

    tk.Button(win, text="APPLICA", command=apply).pack(pady=12)

def export_csv_visible(root, tree, columns):
    rows = []
    for iid in tree.get_children(""):
        vals = tree.item(iid, "values")
        if vals:
            rows.append(vals)

    if not rows:
        messagebox.showinfo("Info", "Nessun dispositivo da esportare (controlla filtro gruppo).")
        return

    default_name = f"export_monitor_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")],
        initialfile=default_name,
        title="Salva esportazione CSV"
    )
    if not path:
        return

    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(columns)
            for r in rows:
                w.writerow(r)
        messagebox.showinfo("OK", f"Esportazione completata:\n{path}")
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile salvare CSV:\n{e}")
