# GeekNews AI 뉴스 봇 🤖

GeekNews RSS 피드에서 AI 관련 뉴스만 골라 Mattermost 채널로 자동 전송합니다.

- **수집 주기**: 매시간 (GitHub Actions cron)
- **필터링**: Claude API (`claude-haiku`)로 정확한 분류
- **중복 방지**: `sent_ids.json` 캐시로 같은 기사 재전송 없음
- **무료**: 외부 서버 없이 GitHub Actions만으로 동작

---

## 빠른 시작

### 1. 레포지토리 생성 및 파일 올리기

```bash
git clone <이 레포>
cd geeknews-ai-bot
git push
```

### 2. GitHub Secrets 등록

레포 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|------|----|
| `ANTHROPIC_API_KEY` | Anthropic Console에서 발급한 API 키 |
| `MATTERMOST_WEBHOOK_URL` | Mattermost Incoming Webhook URL |

#### Mattermost Webhook 발급 방법
1. Mattermost 채널 → **통합** (Integrations)
2. **Incoming Webhooks → Add Incoming Webhook**
3. 채널 선택 후 저장 → URL 복사

### 3. 첫 실행 테스트

Actions 탭 → **GeekNews AI 뉴스 봇** → **Run workflow**  
`dry_run` 체크 시 Mattermost 전송 없이 로그만 출력

---

## 환경 변수 옵션

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MAX_ITEMS_PER_RUN` | `10` | 1회 실행당 최대 분류 기사 수 (API 비용 조절) |
| `DRY_RUN` | `false` | `true`로 설정 시 전송 없이 로그만 출력 |
| `SENT_IDS_FILE` | `sent_ids.json` | 전송 기록 파일 경로 |

---

## Mattermost 출력 예시

```
### 🤖 GeekNews AI 뉴스 (2025-03-24 09:00 UTC)

- **[Nvidia가 Groq을 200억 달러에 인수](https://news.hada.io/topic?id=25398)**
  _AI 추론 하드웨어 기업 인수로 AI 반도체 경쟁 관련_

- **[ChatGPT 광고 도입 임박: 3가지 수익화 전략](https://news.hada.io/topic?id=25387)**
  _OpenAI의 ChatGPT 광고 및 AI 서비스 수익화 전략_
```

---

## 로컬 실행

```bash
# 의존 라이브러리 없음 (표준 라이브러리만 사용)
export ANTHROPIC_API_KEY="sk-ant-..."
export MATTERMOST_WEBHOOK_URL="https://your-mattermost/hooks/xxx"
export DRY_RUN="true"   # 테스트 시 전송 생략

python src/bot.py
```

---

## Vercel 배포 (선택)

나중에 웹 UI나 API endpoint가 필요하면 `api/` 폴더에 Vercel 함수로 확장 가능.  
현재는 GitHub Actions만으로 충분합니다.

---

## 비용 참고

- **GitHub Actions**: 공개 레포 무료, 비공개도 월 2,000분 무료
- **Claude API (Haiku)**: 기사 1건 분류 ≈ $0.0003 → 하루 24회 × 기사 10건 = 약 $0.07/월
