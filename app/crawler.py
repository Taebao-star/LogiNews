# app/crawler.py
import httpx
import feedparser
import httpx, certifi, os
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dateutil import parser as dateparser

HEADERS = {"User-Agent": "LogiNewsBot/1.0 (+https://example.com/bot)"}

def fetch_rss(rss_url: str) -> List[Dict[str, Any]]:
    """RSS 피드를 읽어 간단한 기사 리스트로 변환."""
    d = feedparser.parse(rss_url)
    items = []
    for e in d.entries:
        items.append({
            "title": getattr(e, "title", "").strip(),
            "url": getattr(e, "link", "").strip(),
            "published_at": _parse_date(getattr(e, "published", None) or getattr(e, "updated", None)),
            "view_count": None,   # RSS에는 보통 조회수가 없음
            "content": getattr(e, "summary", ""),
        })
    return items

def fetch_html(url: str) -> str:
    r = httpx.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def parse_list_page(html: str, base_url: str, item_sel: str, title_sel: str, link_sel: str) -> List[Dict[str, Any]]:
    """목록 페이지에서 기사 타이틀/링크를 추출."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(item_sel):
        title_el = card.select_one(title_sel)
        link_el = card.select_one(link_sel)
        if not (title_el and link_el and link_el.get("href")):
            continue
        title = title_el.get_text(" ", strip=True)
        href = link_el.get("href")
        if not href.startswith("http"):
            href = base_url.rstrip("/") + "/" + href.lstrip("/")
        results.append({"title": title, "url": href})
    return results

def parse_article_detail(html: str, detail: Dict[str, Any]) -> Dict[str, Any]:
    """상세 페이지에서 본문/날짜/조회수 등을 추출. 셀렉터는 config 기반."""
    soup = BeautifulSoup(html, "lxml")
    content = ""
    if sel := detail.get("content_selector"):
        content = " ".join(p.get_text(" ", strip=True) for p in soup.select(sel))
    published_at = None
    if dsel := detail.get("date_selector"):
        el = soup.select_one(dsel)
        if el:
            if (attr := detail.get("date_attr")) and el.has_attr(attr):
                published_at = _parse_date(el.get(attr))
            else:
                published_at = _parse_date(el.get_text(strip=True))
    view_count = None
    if vsel := detail.get("view_selector") or None:
        el = soup.select_one(vsel)
        if el:
            digits = "".join(ch for ch in el.get_text() if ch.isdigit())
            view_count = int(digits) if digits else None
    return {"content": content, "published_at": published_at, "view_count": view_count}

def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return dateparser.parse(s)
    except Exception:
        return None
HEADERS = {"User-Agent": "LogiNewsBot/1.0 (+https://www.klnews.co.kr)"}

def fetch_html(url: str, timeout=30):
    # 우선 LOGINEWS_CA_BUNDLE 환경변수 우선, 없으면 certifi 번들 사용
    ca_bundle = os.getenv("LOGINEWS_CA_BUNDLE") or certifi.where()
    # 개발용 임시 우회를 사용하려면 아래 주석 해제 (권장 안함)
    # verify = False
    verify = ca_bundle
    r = httpx.get(url, headers=HEADERS, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.text