\
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from ipmonitor import app_globals as G

def _csv_recipients():
    return [r.strip() for r in (G.MAIL_RECIPIENTS_LIST or []) if r.strip()]

def _friendly_ses_error(e: Exception) -> str | None:
    s = str(e)
    if "ses:SendRawEmail" in s and "Access denied" in s:
        return (
            "AWS SES: Access denied su SendRawEmail.\n\n"
            "Cause tipiche:\n"
            "1) IAM user (SMTP) senza permessi ses:SendRawEmail sulla identity (dominio/email)\n"
            "2) Identity non verificata in eu-central-1\n"
            "3) Account SES in Sandbox (puoi inviare solo a destinatari verificati)\n\n"
            f"Errore ricevuto:\n{s}\n"
        )
    return None

def send_email_report(subject: str, plain_body: str, html_body: str, csv_bytes: bytes | None, csv_filename: str | None):
    if not G.MAIL_ENABLED:
        raise RuntimeError("Mail disabilitata nelle impostazioni")

    recipients = _csv_recipients()
    if not recipients:
        raise RuntimeError("Destinatari vuoti")

    if G.MAIL_TYPE == "ses":
        if not G.MAIL_SMTP_USER or not G.MAIL_SMTP_PASSWORD:
            raise RuntimeError("SES: manca SMTP Username/Password")
        if not G.MAIL_FROM:
            raise RuntimeError("SES: manca From (mittente)")
    else:
        if not G.MAIL_SMTP_USER or not G.MAIL_SMTP_PASSWORD:
            raise RuntimeError("Standard: manca Username/Password")

    from_addr = G.MAIL_FROM.strip() if G.MAIL_FROM.strip() else G.MAIL_SMTP_USER.strip()

    msg = MIMEMultipart("mixed")
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    if G.REPORT_FORMAT_PLAIN and plain_body:
        alt.attach(MIMEText(plain_body, "plain", "utf-8"))
    if G.REPORT_FORMAT_HTML and html_body:
        alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if G.REPORT_ATTACH_CSV and csv_bytes and csv_filename:
        part = MIMEApplication(csv_bytes, Name=csv_filename)
        part["Content-Disposition"] = f'attachment; filename="{csv_filename}"'
        msg.attach(part)

    if G.MAIL_USE_SSL:
        server = smtplib.SMTP_SSL(G.MAIL_SMTP_HOST, G.MAIL_SMTP_PORT, timeout=25)
    else:
        server = smtplib.SMTP(G.MAIL_SMTP_HOST, G.MAIL_SMTP_PORT, timeout=25)

    try:
        if (not G.MAIL_USE_SSL) and G.MAIL_USE_TLS:
            server.starttls()
        server.login(G.MAIL_SMTP_USER, G.MAIL_SMTP_PASSWORD)
        server.sendmail(from_addr, recipients, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass

def explain_mail_error(e: Exception) -> str:
    return _friendly_ses_error(e) or str(e)
