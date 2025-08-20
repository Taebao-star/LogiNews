# app/rank.py
from datetime import datetime
from typing import List, Dict, Any

def sort_articles(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """조회수 우선, 동률이면 최신순."""
    def key(a):
        views = a.get("view_count") or 0
        ts = a.get("published_at_ts") or 0
        return (-views, -ts)
    return sorted(items, key=key)
