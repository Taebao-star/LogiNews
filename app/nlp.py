# app/nlp.py
import os, re
from typing import Dict
from dataclasses import dataclass

USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    from openai import OpenAI
    _client = OpenAI()

@dataclass
class SummaryResult:
    summary: str
    section: str

ALLOWED_SECTIONS = ["국내 물류", "글로벌 동향", "테크·자동화", "정책·규제", "라스트마일·이커머스"]

def naive_summarize(title: str, content: str, max_sent=3) -> str:
    """아주 간단한 로컬 요약: 문장 단위로 앞부분만 2~3문장 취합."""
    text = (title.strip() + "。 " + content.strip()).replace("\n", " ")
    sents = re.split(r"[。.!?！？]\s*", text)
    sents = [s for s in sents if s]
    core = " ".join(sents[:max_sent])
    return (core + " → 현장 적용 포인트: 핵심만 확인하세요.")

def classify_section(title: str, summary: str) -> str:
    t = (title + " " + summary).lower()
    if any(k in t for k in ["korea","대한","국내","물류센터","택배","쿠팡","cj","한진"]):
        return "국내 물류"
    if any(k in t for k in ["policy","법","관세","정부","규제","fta","보조금"]):
        return "정책·규제"
    if any(k in t for k in ["robot","automation","agv","shuttle","wms","ai","vision","테크","자동화","로봇"]):
        return "테크·자동화"
    if any(k in t for k in ["라스트마일","배달","배송","이커머스","commerce","last mile"]):
        return "라스트마일·이커머스"
    return "글로벌 동향"

def summarize_and_classify(title: str, content: str) -> SummaryResult:
    if USE_OPENAI:
        prompt = f"""너는 물류 전문 에디터야. 한국어로 간결하고 친근하게 핵심만 3문장으로 요약해.
        기사 제목: {title}
        본문(요약용): {content[:3000]}
        조건: 1) 과장 금지 2) 숫자는 그대로 3) 마지막 문장은 '업무 인사이트' 1줄로 마무리
        출력:"""
        res = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"한국어로 답변해."},
                      {"role":"user","content":prompt}],
            temperature=0.2,
        )
        summary = res.choices[0].message.content.strip()
    else:
        summary = naive_summarize(title, content)
    section = classify_section(title, summary)
    return SummaryResult(summary=summary, section=section)
