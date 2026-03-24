#!/usr/bin/env python3
"""
GeekNews AI 뉴스 필터 봇
- GeekNews RSS 피드에서 기사 수집
- Claude API로 AI 관련 기사 분류
- Mattermost Webhook으로 전송
"""

import os
import json
import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── 환경 변수 ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
SENT_IDS_FILE       = os.environ.get("SENT_IDS_FILE", "sent_ids.json")
MAX_ITEMS_PER_RUN   = int(os.environ.get("MAX_ITEMS_PER_RUN", "10"))
DRY_RUN             = os.environ.get("DRY_RUN", "false").lower() == "true"

RSS_URL = "https://feeds.feedburner.com/geeknews-feed"

# ── 전송 기록 관리 ──────────────────────────────────────────────────────────
def load_sent_ids() -> set[str]:
    p = Path(SENT_IDS_FILE)
    if p.exists():
        return set(json.loads(p.read_text()))
    return set()

def save_sent_ids(ids: set[str]) -> None:
    Path(SENT_IDS_FILE).write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2))

def item_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]

# ── RSS 파싱 ────────────────────────────────────────────────────────────────
def fetch_rss() -> list[dict]:
    log.info("RSS 피드 가져오는 중: %s", RSS_URL)
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "GeekNewsAIBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        log.error("RSS 피드 접근 실패: %s", e)
        raise SystemExit(1)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://www.w3.org/1999/xhtml",
    }
    root = ET.fromstring(raw)
    items = []
    for entry in root.findall("atom:entry", ns):
        title_el   = entry.find("atom:title", ns)
        link_el    = entry.find("atom:link[@rel='alternate']", ns)
        content_el = entry.find("atom:content", ns)

        title   = title_el.text.strip()   if title_el   is not None else ""
        url     = link_el.get("href", "") if link_el    is not None else ""
        content = content_el.text or ""   if content_el is not None else ""

        # HTML 태그 간단히 제거
        import re
        content_plain = re.sub(r"<[^>]+>", " ", content).strip()
        content_plain = re.sub(r"\s+", " ", content_plain)[:500]

        if title and url:
            items.append({"title": title, "url": url, "summary": content_plain})

    log.info("총 %d개 기사 수집", len(items))
    return items

# ── Claude API 호출 ─────────────────────────────────────────────────────────
def _call_anthropic(prompt: str) -> str:
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["content"][0]["text"].strip()

def is_ai_related(title: str, summary: str) -> tuple[bool, str]:
    """Claude가 AI 관련 여부를 판단. (is_ai, reason) 반환."""
    prompt = f"""다음 기사가 AI·머신러닝·LLM·생성형 AI와 직접 관련된 뉴스인지 판단하세요.

제목: {title}
요약: {summary[:300]}

반드시 아래 JSON 형식으로만 답하세요(다른 텍스트 없이):
{{"ai": true, "reason": "한 줄 이유"}}
또는
{{"ai": false, "reason": "한 줄 이유"}}"""

    try:
        raw = _call_anthropic(prompt)
        # 혹시 JSON 앞뒤 텍스트가 붙으면 제거
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return bool(data.get("ai")), data.get("reason", "")
        return False, "파싱 실패"
    except Exception as e:
        log.warning("Claude 분류 실패 (%s): %s", title[:40], e)
        return False, f"오류: {e}"

# ── Telegram 전송 ──────────────────────────────────────────────────────────
def send_to_telegram(items: list[dict]) -> None:
    if not items:
        log.info("전송할 AI 관련 기사 없음")
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"🤖 <b>GeekNews AI 뉴스 ({now})</b>\n"]
    for it in items:
        lines.append(f'• <a href="{it["url"]}">{it["title"]}</a>')
        if it.get("reason"):
            lines.append(f"  <i>{it['reason']}</i>")

    text = "\n".join(lines)

    if DRY_RUN:
        log.info("[DRY RUN] 전송 스킵. 내용:\n%s", text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.status
    log.info("Telegram 전송 완료 (HTTP %d), %d건", status, len(items))

# ── 메인 ────────────────────────────────────────────────────────────────────
def main() -> None:
    sent_ids  = load_sent_ids()
    all_items = fetch_rss()

    new_items = [it for it in all_items if item_id(it["url"]) not in sent_ids]
    log.info("신규 기사 %d개 (전체 %d개)", len(new_items), len(all_items))

    ai_items: list[dict] = []
    processed = 0

    for it in new_items:
        if processed >= MAX_ITEMS_PER_RUN:
            log.info("이번 실행 처리 한도(%d) 도달", MAX_ITEMS_PER_RUN)
            break

        log.info("분류 중: %s", it["title"][:60])
        is_ai, reason = is_ai_related(it["title"], it["summary"])
        processed += 1

        iid = item_id(it["url"])
        sent_ids.add(iid)

        if is_ai:
            log.info("  ✅ AI 관련: %s", reason)
            ai_items.append({**it, "reason": reason})
        else:
            log.info("  ❌ 무관: %s", reason)

    send_to_telegram(ai_items)
    save_sent_ids(sent_ids)
    log.info("완료. AI 기사 %d건 전송, 누적 ID %d개", len(ai_items), len(sent_ids))

if __name__ == "__main__":
    main()
