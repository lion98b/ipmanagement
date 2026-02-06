\
import tkinter as tk
from tkinter import ttk, messagebox

from ipmonitor import app_globals as G
from ipmonitor.utils.config import save_settings
from ipmonitor.utils.logger import configure_logger, prune_log_file
from ipmonitor.core import state
from ipmonitor.reports.report_state import save_report_state
from ipmonitor.ui import context

def _make_scrollable_toplevel(parent, title: str, width=900, height=780):
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry(f"{width}x{height}")

    container = tk.Frame(win)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, highlightthickness=0)
    vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(canvas)
    content_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def _on_configure(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event):
        canvas.itemconfig(content_id, width=event.width)

    content.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    win.bind_all("<MouseWheel>", _on_mousewheel)

    def _on_close():
        try:
            win.unbind_all("<MouseWheel>")
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)
    return win, content

def open_settings(reload_devices_from_config_cb, schedule_auto_report_cb):
    root = context.root
    if root is None:
        return

    win, body = _make_scrollable_toplevel(root, "Configurazione", width=980, height=820)

    frm_paths = tk.LabelFrame(body, text="Percorsi file", padx=10, pady=10)
    frm_paths.pack(fill="x", padx=10, pady=10)

    tk.Label(frm_paths, text="File config dispositivi (config.cfg) - incolla percorso").grid(row=0, column=0, sticky="w")
    cfg_e = tk.Entry(frm_paths, width=78)
    cfg_e.insert(0, G.CONFIG_FILE)
    cfg_e.grid(row=0, column=1, sticky="w", padx=8)

    tk.Label(frm_paths, text="File log - incolla percorso").grid(row=1, column=0, sticky="w", pady=(8, 0))
    log_e = tk.Entry(frm_paths, width=78)
    log_e.insert(0, G.LOG_FILE)
    log_e.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))

    frm_log = tk.LabelFrame(body, text="Retention log", padx=10, pady=10)
    frm_log.pack(fill="x", padx=10, pady=10)

    tk.Label(frm_log, text="Retention giorni (0 = illimitato)").grid(row=0, column=0, sticky="w")
    log_days_e = tk.Entry(frm_log, width=10)
    log_days_e.insert(0, str(G.LOG_RETENTION_DAYS))
    log_days_e.grid(row=0, column=1, sticky="w", padx=8)

    tk.Label(frm_log, text="Dimensione max log (MB) (0 = illimitato)").grid(row=1, column=0, sticky="w", pady=(6, 0))
    log_mb_e = tk.Entry(frm_log, width=10)
    log_mb_e.insert(0, str(G.LOG_MAX_SIZE_MB))
    log_mb_e.grid(row=1, column=1, sticky="w", padx=8, pady=(6, 0))

    def run_prune_now():
        try:
            prune_log_file()
            messagebox.showinfo("OK", "Pruning log completato.")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    tk.Button(frm_log, text="Esegui pruning ora", command=run_prune_now).grid(row=0, column=2, rowspan=2, padx=10)

    frm_mon = tk.LabelFrame(body, text="Monitor", padx=10, pady=10)
    frm_mon.pack(fill="x", padx=10, pady=10)

    tk.Label(frm_mon, text="Intervallo monitor (sec)").grid(row=0, column=0, sticky="w")
    interval_e = tk.Entry(frm_mon, width=10)
    interval_e.insert(0, str(G.MONITOR_INTERVAL))
    interval_e.grid(row=0, column=1, sticky="w", padx=8)

    tk.Label(frm_mon, text="Soglia fallimenti (%)").grid(row=1, column=0, sticky="w", pady=(6, 0))
    threshold_e = tk.Entry(frm_mon, width=10)
    threshold_e.insert(0, str(int(G.FAILURE_THRESHOLD * 100)))
    threshold_e.grid(row=1, column=1, sticky="w", padx=8, pady=(6, 0))

    tk.Label(frm_mon, text="Finestra temporale (min)").grid(row=2, column=0, sticky="w", pady=(6, 0))
    window_e = tk.Entry(frm_mon, width=10)
    window_e.insert(0, str(G.WINDOW_SECONDS // 60))
    window_e.grid(row=2, column=1, sticky="w", padx=8, pady=(6, 0))

    frm_rep = tk.LabelFrame(body, text="Report: cosa inviare", padx=10, pady=10)
    frm_rep.pack(fill="x", padx=10, pady=10)

    var_table = tk.BooleanVar(value=G.REPORT_INCLUDE_DEVICE_TABLE)
    var_attach_csv = tk.BooleanVar(value=G.REPORT_ATTACH_CSV)
    var_fmt_html = tk.BooleanVar(value=G.REPORT_FORMAT_HTML)
    var_fmt_plain = tk.BooleanVar(value=G.REPORT_FORMAT_PLAIN)

    tk.Checkbutton(frm_rep, text="Includi tabella", variable=var_table).grid(row=0, column=0, sticky="w")
    cols_frame = tk.LabelFrame(frm_rep, text="Colonne tabella (e CSV)", padx=8, pady=8)
    cols_frame.grid(row=1, column=0, sticky="we", pady=(6, 6))

    col_vars = {}
    for i, (key, label) in enumerate(G.REPORT_COLUMNS_CATALOG):
        v = tk.BooleanVar(value=(key in G.REPORT_TABLE_COLUMNS))
        col_vars[key] = v
        r = i // 2
        c = i % 2
        tk.Checkbutton(cols_frame, text=label, variable=v).grid(row=r, column=c, sticky="w", padx=6, pady=2)

    tk.Checkbutton(frm_rep, text="Allega CSV", variable=var_attach_csv).grid(row=2, column=0, sticky="w")
    tk.Label(frm_rep, text="Formato:").grid(row=3, column=0, sticky="w", pady=(8, 0))
    tk.Checkbutton(frm_rep, text="HTML", variable=var_fmt_html).grid(row=3, column=1, sticky="w", pady=(8, 0))
    tk.Checkbutton(frm_rep, text="Plain text", variable=var_fmt_plain).grid(row=4, column=1, sticky="w")

    frm_mail = tk.LabelFrame(body, text="Email", padx=10, pady=10)
    frm_mail.pack(fill="x", padx=10, pady=10)

    mail_enabled_var = tk.BooleanVar(value=G.MAIL_ENABLED)
    mail_auto_var = tk.BooleanVar(value=G.MAIL_AUTO_REPORT)
    tls_var = tk.BooleanVar(value=G.MAIL_USE_TLS)
    ssl_var = tk.BooleanVar(value=G.MAIL_USE_SSL)

    tk.Checkbutton(frm_mail, text="Abilita invio email", variable=mail_enabled_var).grid(row=0, column=0, sticky="w", columnspan=2)

    tk.Label(frm_mail, text="Tipo email:").grid(row=1, column=0, sticky="w")
    mail_type_var = tk.StringVar(value=G.MAIL_TYPE)
    mail_type_cb = ttk.Combobox(frm_mail, values=["standard", "ses"], state="readonly", textvariable=mail_type_var, width=16)
    mail_type_cb.grid(row=1, column=1, sticky="w", padx=8, pady=2)

    tk.Label(frm_mail, text="SMTP host").grid(row=2, column=0, sticky="w")
    smtp_host_e = tk.Entry(frm_mail, width=45)
    smtp_host_e.insert(0, G.MAIL_SMTP_HOST)
    smtp_host_e.grid(row=2, column=1, sticky="w", padx=8, pady=2)

    tk.Label(frm_mail, text="SMTP porta").grid(row=3, column=0, sticky="w")
    smtp_port_e = tk.Entry(frm_mail, width=10)
    smtp_port_e.insert(0, str(G.MAIL_SMTP_PORT))
    smtp_port_e.grid(row=3, column=1, sticky="w", padx=8, pady=2)

    tk.Checkbutton(frm_mail, text="Usa TLS (STARTTLS)", variable=tls_var).grid(row=4, column=0, sticky="w", columnspan=2, pady=(6, 0))
    tk.Checkbutton(frm_mail, text="Usa SSL (SMTP_SSL)", variable=ssl_var).grid(row=5, column=0, sticky="w", columnspan=2)

    lbl_user = tk.Label(frm_mail, text="")
    ent_user = tk.Entry(frm_mail, width=45)

    lbl_pwd = tk.Label(frm_mail, text="")
    ent_pwd = tk.Entry(frm_mail, width=45, show="*")

    lbl_from = tk.Label(frm_mail, text="From (mittente)")
    ent_from = tk.Entry(frm_mail, width=45)

    lbl_subject = tk.Label(frm_mail, text="Prefisso oggetto")
    ent_subject = tk.Entry(frm_mail, width=45)

    lbl_rec = tk.Label(frm_mail, text="Destinatari")
    lb_rec = tk.Listbox(frm_mail, height=7, width=45)
    rec_add_e = tk.Entry(frm_mail, width=30)

    ent_user.insert(0, G.MAIL_SMTP_USER)
    ent_pwd.insert(0, G.MAIL_SMTP_PASSWORD)
    ent_from.insert(0, G.MAIL_FROM)
    ent_subject.insert(0, G.MAIL_SUBJECT_PREFIX)

    for r in G.MAIL_RECIPIENTS_LIST:
        lb_rec.insert(tk.END, r)

    def refresh_mail_type_ui(*_):
        t = mail_type_var.get()
        for w in [lbl_user, ent_user, lbl_pwd, ent_pwd, lbl_from, ent_from, lbl_subject, ent_subject, lbl_rec, lb_rec, rec_add_e]:
            w.grid_forget()

        if t == "ses":
            lbl_user.config(text="SMTP Username (SES)")
            lbl_pwd.config(text="SMTP Password (SES)")
            lbl_from.config(text="From (mittente verificato)")
        else:
            lbl_user.config(text="Username (account SMTP)")
            lbl_pwd.config(text="Password")
            lbl_from.config(text="From (opzionale, se vuoto usa Username)")

        lbl_user.grid(row=6, column=0, sticky="w", pady=(10, 2))
        ent_user.grid(row=6, column=1, sticky="w", padx=8, pady=(10, 2))
        lbl_pwd.grid(row=7, column=0, sticky="w")
        ent_pwd.grid(row=7, column=1, sticky="w", padx=8, pady=2)

        lbl_from.grid(row=8, column=0, sticky="w", pady=(8, 2))
        ent_from.grid(row=8, column=1, sticky="w", padx=8, pady=(8, 2))

        lbl_subject.grid(row=9, column=0, sticky="w")
        ent_subject.grid(row=9, column=1, sticky="w", padx=8, pady=2)

        lbl_rec.grid(row=10, column=0, sticky="nw", pady=(8, 0))
        lb_rec.grid(row=10, column=1, sticky="w", padx=8, pady=(8, 0))
        rec_add_e.grid(row=11, column=1, sticky="w", padx=8, pady=(6, 0))

    def add_recipient():
        email = rec_add_e.get().strip()
        if not email:
            return
        if "@" not in email or "." not in email:
            messagebox.showerror("Errore", "Email non valida")
            return
        existing = set(lb_rec.get(0, tk.END))
        if email in existing:
            rec_add_e.delete(0, tk.END)
            return
        lb_rec.insert(tk.END, email)
        rec_add_e.delete(0, tk.END)

    def remove_recipient():
        sel = lb_rec.curselection()
        if not sel:
            return
        lb_rec.delete(sel[0])

    btn_rec = tk.Frame(frm_mail)
    btn_rec.grid(row=12, column=1, sticky="w", padx=8, pady=(6, 0))
    tk.Button(btn_rec, text="Aggiungi destinatario", command=add_recipient).pack(side="left", padx=(0, 8))
    tk.Button(btn_rec, text="Rimuovi selezionato", command=remove_recipient).pack(side="left")

    tk.Checkbutton(frm_mail, text="Invio automatico report", variable=mail_auto_var).grid(row=13, column=0, sticky="w", columnspan=2, pady=(12, 0))

    tk.Label(frm_mail, text="Intervallo report (min)").grid(row=14, column=0, sticky="w")
    interval_rep_e = tk.Entry(frm_mail, width=10)
    interval_rep_e.insert(0, str(G.MAIL_REPORT_INTERVAL_MIN))
    interval_rep_e.grid(row=14, column=1, sticky="w", padx=8, pady=2)

    def save_all():
        try:
            new_cfg = cfg_e.get().strip() or G.DEFAULT_CONFIG_FILE
            new_log = log_e.get().strip() or G.DEFAULT_LOG_FILE

            new_log_days = int(log_days_e.get().strip())
            new_log_mb = int(log_mb_e.get().strip())
            if new_log_days < 0 or new_log_mb < 0:
                raise ValueError

            new_interval = int(interval_e.get())
            new_threshold = int(threshold_e.get())
            new_window = int(window_e.get())
            if new_interval < 1:
                raise ValueError
            if not (1 <= new_threshold <= 100):
                raise ValueError
            if new_window < 1:
                raise ValueError

            G.CONFIG_FILE = new_cfg
            G.LOG_FILE = new_log
            G.LOG_RETENTION_DAYS = new_log_days
            G.LOG_MAX_SIZE_MB = new_log_mb

            G.MONITOR_INTERVAL = new_interval
            G.FAILURE_THRESHOLD = new_threshold / 100.0
            G.WINDOW_SECONDS = new_window * 60

            G.REPORT_INCLUDE_DEVICE_TABLE = bool(var_table.get())
            G.REPORT_ATTACH_CSV = bool(var_attach_csv.get())
            G.REPORT_FORMAT_HTML = bool(var_fmt_html.get())
            G.REPORT_FORMAT_PLAIN = bool(var_fmt_plain.get())
            if not G.REPORT_FORMAT_HTML and not G.REPORT_FORMAT_PLAIN:
                G.REPORT_FORMAT_PLAIN = True

            selected_cols = [k for k, _ in G.REPORT_COLUMNS_CATALOG if col_vars[k].get()]
            if not selected_cols:
                selected_cols = ["name", "ip", "live"]
            G.REPORT_TABLE_COLUMNS = selected_cols

            G.MAIL_ENABLED = bool(mail_enabled_var.get())
            G.MAIL_TYPE = mail_type_var.get() if mail_type_var.get() in ("standard", "ses") else "standard"
            G.MAIL_SMTP_HOST = smtp_host_e.get().strip()
            G.MAIL_SMTP_PORT = int(smtp_port_e.get().strip())
            G.MAIL_USE_TLS = bool(tls_var.get())
            G.MAIL_USE_SSL = bool(ssl_var.get())
            G.MAIL_SMTP_USER = ent_user.get().strip()
            G.MAIL_SMTP_PASSWORD = ent_pwd.get()
            G.MAIL_FROM = ent_from.get().strip()
            G.MAIL_SUBJECT_PREFIX = ent_subject.get().strip() or "[IP Monitor]"
            G.MAIL_RECIPIENTS_LIST = list(lb_rec.get(0, tk.END))
            G.MAIL_AUTO_REPORT = bool(mail_auto_var.get())
            G.MAIL_REPORT_INTERVAL_MIN = max(1, int(interval_rep_e.get().strip()))

            save_settings()
            configure_logger()
            prune_log_file()
            reload_devices_from_config_cb()
            schedule_auto_report_cb()

            messagebox.showinfo("Salvato", "Configurazione salvata")
            win.destroy()

        except Exception:
            messagebox.showerror("Errore", "Valori non validi (controlla monitor/log/mail/report).")

    tk.Button(body, text="SALVA", command=save_all).pack(pady=10)

    mail_type_cb.bind("<<ComboboxSelected>>", refresh_mail_type_ui)
    refresh_mail_type_ui()
