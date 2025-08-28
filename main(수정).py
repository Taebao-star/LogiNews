# 수정된 app/main.py

import argparse, os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import yaml
from crawler import fetch_rss, fetch_html, parse_list_page, parse_article_detail
from app.nlp import summarize_and_classify
from app.rank import sort_articles
from app.render_email import render_newsletter
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Supabase 클라이언트 설정 (기존 코드 그대로)
url: str = "https://dleyhovinsbagtezsccd.supabase.co"
key: str = "sb_publishable_2s2b7ogpLhp6DWR9LXCwcQ_dRgSKIv5"
supabase: Client = create_client(url, key)

# save_to_supabase 함수 (기존 코드 그대로)
def save_to_supabase(news_data):
    """크롤링된 뉴스 데이터를 Supabase 'articles' 테이블에 저장하는 함수."""
    try:
        response = supabase.table("articles").insert(news_data).execute()
        print("데이터가 Supabase에 성공적으로 저장되었습니다.")
        # print(f"삽입된 데이터: {response.data}") # 디버깅용으로 주석 처리 또는 삭제 가능
        print(f"총 {len(response.data)}개의 기사를 Supabase에 저장했습니다.")
    except Exception as e:
        print(f"Supabase 저장 중 오류 발생: {e}")

# ... (나머지 send_email, load_sources, dedup_by_url 등 함수는 그대로)

def collect_articles(src: Dict[str, Any]) -> List[Dict[str, Any]]:
    # ... (기존 collect_articles 함수 그대로)
    # collect_articles 함수는 기존에 main 함수 내에 있었던 로직을 그대로 사용합니다.
    items: List[Dict[str, Any]] = []
    if src.get("method") == "rss" and src.get("rss_url"):
        items = fetch_rss(src["rss_url"])
        for it in items:
            it["source_name"] = src["name"]
    elif src.get("method") == "html" and src.get("list_url"):
        html = fetch_html(src["list_url"])
        lst = parse_list_page(html, src["base_url"], src["item_selector"], src["title_selector"], src["link_selector"])
        for it in lst:
            it["source_name"] = src["name"]
            detail_cfg = src.get("detail", {})
            detail_html = fetch_html(it["url"])
            d = parse_article_detail(detail_html, detail_cfg)
            it.update(d)
    return items

def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="HTML 파일로 미리보기만 생성")
    parser.add_argument("--send", action="store_true", help="이메일 발송")
    args = parser.parse_args()

    app_name = os.getenv("APP_NAME", "LogiNews")
    today = datetime.now()

    # 1. 소스 불러오기 및 기사 수집 (통합)
    sources = load_sources()
    all_items: List[Dict[str, Any]] = []
    for s in sources:
        try:
            # collect_articles 함수는 이제 하나의 소스를 처리합니다.
            all_items.extend(collect_articles(s))
        except Exception as e:
            print(f"[WARN] {s.get('name')}: 수집 실패 - {e}")

    # 2. 중복 제거
    all_items = dedup_by_url(all_items)

    # 3. 요약 및 분류
    enriched: List[Dict[str, Any]] = []
    for it in all_items:
        title = it.get("title","").strip()
        content = it.get("content","").strip()
        if not title: # 제목 없는 기사는 건너뛰기
            continue
        res = summarize_and_classify(title, content)
        it["summary"] = res.summary
        it["section"] = res.section
        it["published_at_ts"] = int(it.get("published_at").timestamp()) if it.get("published_at") else 0
        enriched.append(it)
    
    # 4. Supabase에 데이터 저장
    if enriched: # 데이터가 있을 때만 저장 함수 호출
        save_to_supabase(enriched)
    else:
        print("수집된 기사가 없어 Supabase에 저장할 데이터가 없습니다.")

    # 5. 섹션별 정렬 및 렌더링
    sorted_items = sort_articles(enriched)
    sections = group_by_section(sorted_items)

    html, subject = render_newsletter(app_name, sections, today)

    out_dir = Path("out"); out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"newsletter_{today.strftime('%Y%m%d')}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"[OK] 미리보기 파일 생성: {out_path}")

    if args.send:
        if send_email is None:
            print("[ERROR] 이메일 모듈 로드 실패. SMTP 설정 또는 의존성 확인.")
            return
        try:
            send_email(subject, html)
            print("[OK] 이메일 발송 완료")
        except Exception as e:
            print(f"[ERROR] 이메일 발송 실패: {e}")

if __name__ == "__main__":
    main()
