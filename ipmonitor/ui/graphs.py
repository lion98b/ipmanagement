\
import time
import tkinter as tk
from tkinter import messagebox

from ipmonitor import app_globals as G
from ipmonitor.core import state
from ipmonitor.core.monitor import is_critical
from ipmonitor.ui import context

# Matplotlib (optional)
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

def calc_series_uptime(name: str, buckets: int = 60):
    end = time.time()
    start = end - G.WINDOW_SECONDS
    step = G.WINDOW_SECONDS / buckets

    with state.state_lock:
        data = list(state.results.get(name, []))

    labels, up_pct = [], []
    for i in range(buckets):
        b_start = start + i * step
        b_end = b_start + step
        bucket = [r for t, r in data if b_start <= t < b_end]
        labels.append(time.strftime("%H:%M", time.localtime(b_end)))
        if not bucket:
            up_pct.append(float("nan"))
        else:
            ups = sum(bucket)
            total = len(bucket)
            up_pct.append((ups / total) * 100.0)

    return labels, up_pct

def get_names_for_graph(mode: str, get_selected, get_visible):
    if mode == "solo_selezionati":
        return get_selected()
    if mode == "solo_vista":
        return get_visible()
    if mode == "solo_critici":
        with state.state_lock:
            names = list(state.devices.keys())
        crit = []
        for n in names:
            # group filter
            if state.selected_group_filter != "Tutti":
                info = state.devices.get(n, {})
                if (info.get("group") or "Default") != state.selected_group_filter:
                    continue
            if is_critical(n):
                crit.append(n)
        crit.sort(key=lambda s: s.lower())
        return crit
    return []

def open_uptime_graph_multi_with_selector(get_selected, get_visible):
    if not MATPLOTLIB_OK:
        messagebox.showerror("Grafici non disponibili", "Installa matplotlib:\n  pip install matplotlib")
        return

    root = context.root
    if root is None:
        return

    win = tk.Toplevel(root)
    win.title("Grafico Uptime% (multi) - selettore sorgente")
    win.geometry("1180x660")

    topbar = tk.Frame(win)
    topbar.pack(fill="x", padx=10, pady=8)

    tk.Label(topbar, text="Mostra:").pack(side="left")

    mode_var = tk.StringVar(value="solo_selezionati")
    tk.Radiobutton(topbar, text="Solo selezionati", value="solo_selezionati", variable=mode_var).pack(side="left", padx=10)
    tk.Radiobutton(topbar, text="Solo vista corrente", value="solo_vista", variable=mode_var).pack(side="left", padx=10)
    tk.Radiobutton(topbar, text="Solo critici", value="solo_critici", variable=mode_var).pack(side="left", padx=10)

    count_lbl = tk.Label(topbar, text="", fg="gray")
    count_lbl.pack(side="right")

    fig = Figure(figsize=(11.2, 5.6), dpi=100)
    ax = fig.add_subplot(111)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.get_tk_widget().pack(expand=True, fill="both", padx=10, pady=(0, 10))

    def refresh():
        try:
            if not win.winfo_exists():
                return

            mode = mode_var.get()
            names = get_names_for_graph(mode, get_selected, get_visible)
            if len(names) > 12:
                names = names[:12]

            ax.clear()

            if not names:
                count_lbl.config(text="0 dispositivi")
                ax.set_title("Nessun dispositivo da mostrare (controlla selezione/vista/critici)")
                ax.set_ylim(0, 100)
                ax.set_ylabel("Uptime (%)")
                ax.grid(True)
                canvas.draw()
                win.after(2000, refresh)
                return

            count_lbl.config(text=f"{len(names)} dispositivi (max 12)")

            buckets = 60
            base_labels = None
            x = None

            for name in names:
                labels, up = calc_series_uptime(name, buckets=buckets)
                if base_labels is None:
                    base_labels = labels
                    x = list(range(len(labels)))

                line, = ax.plot(x, up, linewidth=1.8, label=name)
                ax.fill_between(x, up, 0, alpha=0.12, color=line.get_color())

            uptime_threshold = 100 - int(G.FAILURE_THRESHOLD * 100)
            ax.axhline(y=uptime_threshold, linewidth=1.0, linestyle="--", label=f"Soglia uptime {uptime_threshold}%")

            ax.set_ylim(0, 100)
            ax.set_ylabel("Uptime (%)")
            ax.set_xlabel("Tempo (ultimo 60 min)")
            ax.grid(True)

            if base_labels:
                step = max(1, len(base_labels) // 8)
                ax.set_xticks(list(range(0, len(base_labels), step)))
                ax.set_xticklabels(base_labels[0::step], rotation=30, ha="right")

            ax.legend(loc="upper left", fontsize=8)

            title_mode = {
                "solo_selezionati": "Solo selezionati",
                "solo_vista": "Solo vista corrente",
                "solo_critici": "Solo critici"
            }.get(mode, mode)

            ax.set_title(f"Uptime% ultimi {G.WINDOW_SECONDS//60} min — {title_mode}")
            canvas.draw()

        except Exception as e:
            try:
                ax.clear()
                ax.set_title(f"Errore grafico: {e}")
                canvas.draw()
            except Exception:
                pass

        win.after(5000, refresh)

    refresh()
