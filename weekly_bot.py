#!/usr/bin/env python3
"""
GeekNews 주간 뉴스 봇
- news.hada.io/weekly 에서 최신 주간 이슈 스크래핑
- Telegram으로 전송 (매주 월요일 KST 09:00)
"""

import os
import json
import logging
import re
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
SENT_WEEKLY_FILE   = os.environ.get("SENT_WEEKLY_FILE", "sent_weekly.json")
DRY_RUN            = os.environ.get("DRY_RUN", "false").lower() == "true"
BASE_URL           = "https://news.hada.io"


# ── HTTP ──────────────────────────────────────────────────────────────────────
def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "GeekNewsWeeklyBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        log.error("URL 접근 실패 (%s): %s", url, e)
        raise SystemExit(1)


# ── 전송 기록 ─────────────────────────────────────────────────────────────────
def load_sent_weekly() -> set:
    p = Path(SENT_WEEKLY_FILE)
    if p.exists():
        return set(json.loads(p.read_text()))
    return set()


def save_sent_weekly(ids: set) -> None:
    Path(SENT_WEEKLY_FILE).write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2)
    )


# ── 파싱 ──────────────────────────────────────────────────────────────────────
def get_latest_weekly_id(html: str) -> str:
    """주간 목록 페이지에서 최신 이슈 ID 추출."""
    m = re.search(r"href=['\"]?/weekly/(\d+)['\"]?", html)
    if not m:
        raise ValueError("최신 주간 이슈 ID를 찾을 수 없음")
    return m.group(1)


def parse_weekly_issue(html: str) -> dict:
    """개별 주간 이슈 페이지에서 제목·날짜·뉴스 목록 추출."""
    # 제목: <h2 class=tacenter>[GN#351] ...
    title_m = re.search(r"<h2[^>]*>\s*(\[GN#\d+\][^<]+)<", html)
    title = title_m.group(1).strip() if title_m else "주간 GeekNews"

    # 날짜 범위: <div class='date center'>2026-03-23 ~ 2026-03-29 ...
    date_m = re.search(r"class=['\"]date[^'\"]*['\"][^>]*>\s*([^<]+)<", html)
    date_range = date_m.group(1).strip() if date_m else ""

    # 뉴스 항목: <li> 중 class='link bold' 링크를 가진 것만
    items = []
    for li_m in re.finditer(r"<li>(.*?)</li>", html, re.DOTALL):
        li = li_m.group(1)
        if "link bold" not in li:
            continue

        # href 먼저인 경우: <a href='...' class='link bold'>
        link_m = re.search(
            r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*class=['\"]link bold['\"][^>]*>\s*([^<]+)\s*<",
            li,
        )
        # class 먼저인 경우: <a class='link bold' href='...'>
        if not link_m:
            link_m = re.search(
                r"<a\b[^>]*class=['\"]link bold['\"][^>]*href=['\"]([^'\"]+)['\"][^>]*>\s*([^<]+)\s*<",
                li,
            )

        if link_m:
            url   = link_m.group(1)
            title_item = link_m.group(2).strip()
            if not url.startswith("http"):
                url = BASE_URL + url
            items.append({"title": title_item, "url": url})

    log.info("파싱 완료: %s — %d개 항목", title, len(items))
    return {"title": title, "date_range": date_range, "items": items}


# ── Telegram 전송 ─────────────────────────────────────────────────────────────
def send_to_telegram(issue_id: str, issue: dict) -> None:
    items = issue["items"]
    if not items:
        log.warning("전송할 항목 없음")
        return

    weekly_url = f"{BASE_URL}/weekly/{issue_id}"
    lines = [
        f"📰 <b>{issue['title']}</b>",
    ]
    if issue["date_range"]:
        lines.append(f"<i>{issue['date_range']}</i>")
    lines.append("")
    lines.append("한 주간 GeekNews에서 엄선한 뉴스를 모아 전해드립니다.")
    lines.append("")
    for it in items:
        lines.append(f'• <a href="{it["url"]}">{it["title"]}</a>')
    lines.append(f'\n🔗 <a href="{weekly_url}">전체 보기</a>')

    text = "\n".join(lines)

    # Telegram 4096자 제한 대응
    if len(text) > 4000:
        text = text[:4000] + f'\n...\n🔗 <a href="{weekly_url}">전체 보기</a>'

    if DRY_RUN:
        log.info("[DRY RUN] 전송 스킵:\n%s", text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.status
    log.info("Telegram 전송 완료 (HTTP %d), %d건", status, len(items))


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    sent = load_sent_weekly()

    weekly_html = fetch_url(f"{BASE_URL}/weekly")
    issue_id = get_latest_weekly_id(weekly_html)
    log.info("최신 주간 이슈 ID: %s", issue_id)

    if issue_id in sent:
        log.info("이미 전송된 이슈: %s", issue_id)
        return

    issue_html = fetch_url(f"{BASE_URL}/weekly/{issue_id}")
    issue = parse_weekly_issue(issue_html)

    send_to_telegram(issue_id, issue)

    sent.add(issue_id)
    save_sent_weekly(sent)
    log.info("완료. 주간 이슈 %s 전송", issue_id)


if __name__ == "__main__":
    main()
