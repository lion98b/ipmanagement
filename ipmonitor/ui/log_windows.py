\
import os
import tkinter as tk
from tkinter import scrolledtext

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.ui import context

def open_log_window():
    root = context.root
    if root is None:
        return

    win = tk.Toplevel(root)
    win.title("Log completo")
    win.geometry("920x520")

    txt = scrolledtext.ScrolledText(win, state="disabled")
    txt.pack(expand=True, fill="both")

    def refresh():
        try:
            if not win.winfo_exists():
                return
            if not os.path.exists(G.LOG_FILE):
                content = "(log non trovato)"
            else:
                with open(G.LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            txt.config(state="normal")
            txt.delete(1.0, tk.END)
            txt.insert(tk.END, content)
            txt.config(state="disabled")
        except Exception:
            pass
        win.after(2000, refresh)

    refresh()

def open_device_log(name: str):
    info = state.devices.get(name)
    if not info:
        return
    ip = info["ip"]

    root = context.root
    if root is None:
        return

    win = tk.Toplevel(root)
    win.title(f"Log - {name} [{ip}]")
    win.geometry("920x520")

    txt = scrolledtext.ScrolledText(win, state="disabled")
    txt.pack(expand=True, fill="both")

    def refresh():
        try:
            if not win.winfo_exists():
                return
            if not os.path.exists(G.LOG_FILE):
                lines = ["(log non trovato)\n"]
            else:
                with open(G.LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [l for l in f if f"{name} [{ip}]" in l]
            txt.config(state="normal")
            txt.delete(1.0, tk.END)
            txt.insert(tk.END, "".join(lines))
            txt.config(state="disabled")
        except Exception:
            pass
        win.after(2000, refresh)

    refresh()
