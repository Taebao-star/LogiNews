# LogiNewsBot (Starter Kit)

비개발자도 따라 만들 수 있는 '물류 뉴스 데일리 요약 메일러'의 최소 구현 예제입니다.
**1단계(로컬 미리보기) → 2단계(이메일 발송) → 3단계(Supabase 연동)** 으로 점진적으로 확장하세요.

## 빠른 시작
```bash
# 1) 가상환경(선택)
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 2) 필수 설치
pip install -r requirements.txt

# 3) 설정 파일 복사 후 값 채우기
cp .env.example .env

# 4) 로컬 미리보기 실행
python app/main.py --preview

# 5) 이메일 발송 테스트(선택)
python app/main.py --send
```
이후 Windows 작업 스케줄러, macOS launchd, 또는 GitHub Actions cron으로 매일 아침 실행하세요.

## 구성
- `app/main.py` : 전체 파이프라인(수집 → 요약 → 섹션 → 정렬 → 렌더 → 발송/미리보기)
- `app/crawler.py` : RSS/HTML 크롤링(간단 셀렉터 기반)
- `app/nlp.py` : 요약/섹션 분류(OPENAI_API_KEY 없으면 로컬 간이 요약)
- `app/rank.py` : 조회수 기반 정렬(대체지표 포함)
- `app/render_email.py` : HTML 이메일 렌더(Jinja2)
- `app/emailer.py` : SMTP 메일 발송(선택)
- `config/sources.yaml` : 소스/셀렉터 설정
- `templates/newsletter.html` : 이메일 템플릿
- `sql/schema.sql` : Supabase(Postgres) 스키마 초안

## 주의
- 각 언론사/사이트의 robots.txt 및 이용약관을 지켜주세요.
- 요약문은 **자체 작성**하고 **원문 링크**를 항상 포함하세요.
