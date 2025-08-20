# app/emailer.py
import os, smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@example.com")
TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS","").split(",") if e.strip()]

def send_email(subject: str, html: str):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and TO_EMAILS):
        raise RuntimeError("SMTP 설정이 없습니다(.env 확인).")
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("LogiNews", FROM_EMAIL))
    msg["To"] = ", ".join(TO_EMAILS)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(FROM_EMAIL, TO_EMAILS, msg.as_string())
