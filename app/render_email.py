# app/render_email.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
from typing import Dict, List

def render_newsletter(app_name: str, sections: List[Dict], today: datetime) -> (str, str):
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("newsletter.html")
    subject = f"[{app_name}] 오늘의 물류 브리핑 ({today.strftime('%m/%d')})"
    html = template.render(subject=subject, app_name=app_name, sections=sections)
    return html, subject
