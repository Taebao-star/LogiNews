# app/main.py
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

def load_sources_from_yaml(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as file:
        sources_data = yaml.safe_load(file)
    return sources_data

#sendgrid
def send_email(subject, content):
    try:
        sg = SendGridAPIClient("여러분의 SendGrid API 키")
        from_email = "mto48184@gmail.com"
        to_emails = "mto48184@gmail.com"

        message = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=content
        )
        response = sg.send(message)
        print(f"이메일 발송 성공. 상태 코드: {response.status_code}")
    except Exception as e:
        print(f"이메일 발송 중 오류 발생: {e}")

#supabase 
url: str = "https://dleyhovinsbagtezsccd.supabase.co"
key: str = "sb_publishable_2s2b7ogpLhp6DWR9LXCwcQ_dRgSKIv5"
supabase: Client = create_client(url, key)

def save_to_supabase(news_data):
    """크롤링된 뉴스 데이터를 Supabase 'articles' 테이블에 저장하는 함수."""
    try:
        # news_data는 [{'title': '제목', 'summary': '요약', 'url': 'URL', ...}, ...] 형태여야 함
        response = supabase.table("articles").insert(news_data).execute()
        print("데이터가 Supabase에 성공적으로 저장되었습니다.")
        print(f"삽입된 데이터: {response.data}")
        print(f"총 {len(response.data)}개의 기사를 Supabase에 저장했습니다.")
    except Exception as e:
        print(f"Supabase 저장 중 오류 발생: {e}")


try:
    from app.emailer import send_email
except Exception:
    send_email = None

def load_sources(cfg_path="config/sources.yaml") -> List[Dict[str, Any]]:
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("sources", [])

def dedup_by_url(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for it in items:
        u = it.get("url")
        if not u or u in seen: 
            continue
        seen.add(u)
        out.append(it)
    return out

def group_by_section(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        sec = it.get("section", "기타")
        groups.setdefault(sec, []).append(it)
    # 섹션 순서
    order = ["국내 물류","글로벌 동향","테크·자동화","정책·규제","라스트마일·이커머스"]
    ordered_sections = []
    for name in order:
        if name in groups:
            ordered_sections.append({"name": name, "items": groups[name]})
    # 기타 섹션 뒤에
    for name, arr in groups.items():
        if name not in order:
            ordered_sections.append({"name": name, "items": arr})
    return ordered_sections

def collect_articles(src: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            # 상세 페이지에서 내용/조회수/발행일 추출(가능 시)
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

    sources = load_sources()
    all_items: List[Dict[str, Any]] = []
    for s in sources:
        try:
            all_items.extend(collect_articles(s))
        except Exception as e:
            print(f"[WARN] {s.get('name')}: 수집 실패 - {e}")

    # 중복 제거
    all_items = dedup_by_url(all_items)

    # 요약/섹션
    enriched: List[Dict[str, Any]] = []
    for it in all_items:
        title = it.get("title","").strip()
        content = it.get("content","").strip()
        res = summarize_and_classify(title, content)
        it["summary"] = res.summary
        it["section"] = res.section
        # 정렬용 타임스탬프
        it["published_at_ts"] = int(it.get("published_at").timestamp()) if it.get("published_at") else 0
        enriched.append(it)

    # 섹션별 정렬(조회수 우선)
    sorted_items = sort_articles(enriched)
    sections = group_by_section(sorted_items)

    # 데이터 저장
    save_to_supabase(sorted_items)

    # 렌더
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

    # 1. YAML 파일에서 소스 목록 불러오기
    sources = load_sources_from_yaml('config/sources.yaml')
    # 모든 기사를 저장할 리스트
    all_articles = []

    # 2. RSS 피드 크롤링
    rss_sources = sources.get("rss", [])
    for rss_source in rss_sources:
        try:
            articles = fetch_rss(rss_source['url'])
            all_articles.extend(articles)
        except Exception as e:
            print(f"RSS 피드 크롤링 중 오류 발생 ({rss_source.get('url')}): {e}")
    # 3. HTML 크롤링 (예시)
    html_sources = sources.get("html", [])
    for html_source in html_sources:
        try:
            articles = fetch_html(html_source['url'])
            all_articles.extend(articles)
        except Exception as e:
            print(f"HTML 크롤링 중 오류 발생 ({html_source.get('url')}): {e}")
                  
    main()
