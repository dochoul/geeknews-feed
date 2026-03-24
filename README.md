# GeekNews AI 뉴스 봇

GeekNews RSS 피드에서 AI 관련 뉴스만 골라 **Telegram 그룹**으로 자동 전송하는 봇입니다.

## 주요 기능

- **RSS 수집**: [GeekNews](https://news.hada.io) 피드에서 최신 기사 수집
- **AI 필터링**: Claude API (Haiku)로 AI/ML/LLM 관련 기사만 분류
- **Telegram 전송**: 필터링된 기사를 Telegram 그룹에 자동 전송
- **중복 방지**: `sent_ids.json` 캐시로 같은 기사 재전송 없음
- **자동 실행**: GitHub Actions cron으로 2시간마다 실행
- **외부 의존성 없음**: Python 표준 라이브러리만 사용

---

## 설정 방법

### 1. Telegram 봇 생성

1. Telegram에서 `@BotFather`에게 `/newbot` 입력
2. 봇 이름 설정 후 **Bot Token** 받기
3. Telegram 그룹 생성 후 봇을 멤버로 초대
4. 그룹에서 메시지 전송 후 아래 URL로 **Chat ID** 확인:
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
   그룹 Chat ID는 `-`로 시작하는 음수입니다.

### 2. GitHub Secrets 등록

레포 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|------|-----|
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com)에서 발급한 API 키 |
| `TELEGRAM_BOT_TOKEN` | BotFather에서 받은 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 그룹 Chat ID (음수) |

### 3. 실행

- **자동**: 2시간마다 GitHub Actions가 자동 실행
- **수동**: Actions 탭 → **GeekNews AI 뉴스 봇** → **Run workflow**

---

## 로컬 실행

```bash
# .env 파일 생성
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-100123456789

# 실행
export $(cat .env | xargs)
python3 bot.py

# 전송 없이 테스트만
export DRY_RUN=true
python3 bot.py
```

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | (필수) | Anthropic API 키 |
| `TELEGRAM_BOT_TOKEN` | (필수) | Telegram 봇 토큰 |
| `TELEGRAM_CHAT_ID` | (필수) | Telegram 그룹 Chat ID |
| `MAX_ITEMS_PER_RUN` | `10` | 1회 실행당 최대 분류 기사 수 |
| `DRY_RUN` | `false` | `true` 시 전송 없이 로그만 출력 |
| `SENT_IDS_FILE` | `sent_ids.json` | 전송 기록 파일 경로 |

---

## Telegram 출력 예시

```
🤖 GeekNews AI 뉴스 (2026-03-24 14:00 UTC)

• Nvidia가 Groq을 200억 달러에 인수
  AI 추론 하드웨어 기업 인수로 AI 반도체 경쟁 관련

• ChatGPT 광고 도입 임박: 3가지 수익화 전략
  OpenAI의 ChatGPT 광고 및 AI 서비스 수익화 전략
```

---

## 비용

- **GitHub Actions**: 공개 레포 무료, 비공개도 월 2,000분 무료
- **Claude API (Haiku)**: 기사 1건 분류 ≈ $0.0003 → 하루 12회 × 10건 = 약 **월 $0.04** (50원 미만)
