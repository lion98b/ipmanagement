\
import os
from tkinter import messagebox

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.utils.logger import ensure_parent_dir

def load_devices():
    if not os.path.exists(G.CONFIG_FILE):
        return {}
    d = {}
    try:
        with open(G.CONFIG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                name, rest = line.split("=", 1)
                name = name.strip()
                rest = rest.strip()
                if not name or not rest:
                    continue

                if "|" in rest:
                    ip, grp = rest.split("|", 1)
                    ip = ip.strip()
                    grp = grp.strip() or "Default"
                else:
                    ip = rest.strip()
                    grp = "Default"

                if ip:
                    d[name] = {"ip": ip, "group": grp}
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile leggere config:\n{G.CONFIG_FILE}\n\n{e}")
    return d

def save_devices():
    try:
        ensure_parent_dir(G.CONFIG_FILE)
        with open(G.CONFIG_FILE, "w", encoding="utf-8") as f:
            for name, info in state.devices.items():
                ip = info.get("ip", "").strip()
                grp = (info.get("group") or "Default").strip() or "Default"
                f.write(f"{name}={ip}|{grp}\n")
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile salvare config:\n{G.CONFIG_FILE}\n\n{e}")

def rebuild_groups_from_devices():
    gs = {"Default"}
    for info in state.devices.values():
        g = (info.get("group") or "Default").strip() or "Default"
        gs.add(g)
    state.groups = gs
