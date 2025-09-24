# NewsMonitor Setup Guide (Docker & Local)

> 목적: 개인 탭에서 24/7 뉴스 수집·분류·점수화·긴급 알림, 오후 인트라데이 설명, 아침 리캡을 동작시키기 위한 **구체적 세팅 절차**

## 0) 필수 사전 준비
- OS: Windows 10/11, macOS, 또는 Linux
- Python 3.11+ (로컬 실행용) 또는 Docker Desktop (권장)
- 외부 키 발급
  - SEC: 별도 키 없음 (단, `SEC_USER_AGENT`에 회사/연락처 기입)
  - 시세: Finnhub 또는 Polygon 중 1곳
  - FRED: 무료 API 키
  - 번역: Google Cloud 또는 Papago/DeepL 중 1곳

## 1) 폴더 구조
```
project-root/
  server.py
  index.html
  requirements.txt
  docker-compose.yml
  .env            # 실제 키를 채워 넣기 (초기에는 .env.sample 복사)
  secrets/
    gcp-translate.json   # (선택) Google SA 키
  config/
    source_trust.json
    category_event_rules.json
    company_nvidia.json
  schema.sql
```
본 저장소에 샘플 파일을 제공합니다.

## 2) .env 설정
- `.env.sample`을 복사하여 `.env` 생성 후 **키 채우기**
- Windows 경로 주의: `GOOGLE_APPLICATION_CREDENTIALS`는 WSL/Docker 내부 경로(`/secrets/...`)를 사용

## 3) Docker로 실행 (권장)
```bash
# 프로젝트 루트에서
docker compose up -d postgres redis
# DB 준비 여부 확인 후 API 기동
docker compose up -d api
# 로그 보기
docker compose logs -f api
```
- API는 기본 `http://localhost:3000` 노출
- 최초 실행 후, DB 스키마 적용:
```bash
docker exec -it $(docker ps -qf "name=postgres") psql -U ${POSTGRES_USER:-newsmon} -d ${POSTGRES_DB:-newsmon} -c "\i /var/lib/postgresql/data/schema.sql"
```
> 또는 `api` 컨테이너에서 `psql`로 실행해도 됩니다. 간단히는 서버 코드가 부팅 시 `schema.sql`을 실행하도록 추가하세요.

## 4) 로컬 실행 (Windows PowerShell 예시)
```powershell
# 1) 가상환경
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# 3) 환경변수 (.env 사용 권장)
# Windows 경로에 공백이 있을 경우 따옴표로 감싸세요.
$env:APP_PORT="3000"
$env:SEC_USER_AGENT="NewsMonitor (ops@yourco.com)"
$env:FINNHUB_API_KEY="여기에키"
$env:FRED_API_KEY="여기에키"

# 4) PostgreSQL/Redis는 Docker로 띄우면 편합니다.
docker compose up -d postgres redis

# 5) 서버 실행
uvicorn server:app --reload --port 3000
```
> **오류 대처**: `Could not import module "server"` → 실행 위치를 `server.py`가 있는 폴더로 옮긴 뒤 실행하거나, `uvicorn main:app`처럼 모듈명을 올바르게 지정하세요.

## 5) DB 스키마 적용
- `schema.sql`을 사용하여 필수 테이블 생성
```bash
# Docker postgres 컨테이너 안에서
psql -U newsmon -d newsmon -f /var/lib/postgresql/data/schema.sql
```
- 직접 애플리케이션 부팅 시 자동으로 실행하도록 `server.py`에서 `schema.sql` 읽어 `psycopg2`로 실행하는 코드를 추가할 수 있습니다.

## 6) 외부 API 연결 체크
- 시세(분봉)
  - Finnhub: `GET https://finnhub.io/api/v1/stock/candle?symbol=NVDA&resolution=1&from=...&to=...&token=${FINNHUB_API_KEY}`
- FRED(금리)
  - `GET https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=${FRED_API_KEY}&file_type=json`
- SEC
  - 헤더 `User-Agent` 포함 요청으로 8-K/10-Q 엔드포인트 호출

## 7) 서버 엔드포인트 사전 점검
- `GET /feed` → 기본 기사 카드 배열
- `GET /me/feed?...` → 사용자/워치리스트 반영(구현 시)
- `GET /me/intraday_explain?ticker=NVDA&date=YYYY-MM-DD` → 오후 카드
- `GET /me/recap?ticker=NVDA&date=YYYY-MM-DD` → 아침 리캡

### cURL 예시
```bash
curl "http://localhost:3000/feed?limit=5"
curl "http://localhost:3000/me/intraday_explain?ticker=NVDA&date=2025-09-19"
curl "http://localhost:3000/me/recap?ticker=NVDA&date=2025-09-19"
```

## 8) Windows 경로/PowerShell 팁
- 공백 포함 경로는 따옴표 필수: `"C:\Users\...\바탕 화면\news-monitor"`
- `cd` 오류시: `Set-Location -Path "C:\Users\...\바탕 화면\news-monitor"`
- 파이썬 모듈 실행은 **현재 폴더 기준**: `uvicorn server:app`에서 `server.py`가 현재 디렉터리에 있어야 합니다.

## 9) 운영(스케줄러) 적용
- 간단히는 `APScheduler`로 내부 스케줄 잡을 등록:
  - fetch_rss: 매 1~3분
  - cluster_update: 매 2분
  - intraday_explain_job: 15:10~17:00 (KST) 사이 1회
  - daily_recap_job: 매 영업일 07:30 (KST)
- 또는 Celery + Redis를 사용해 워커/비트 분리

## 10) 보안/비용 수칙
- `.env`와 `/secrets`는 Git에 커밋 금지
- 요청량 초과시 요금 급증 방지: 도메인별 레이트리밋/If-None-Match(ETag) 꼭 사용
- robots/ToS 준수, 공식/톱티어 소스 우선

## 11) 1분 점검 체크리스트
- [ ] `docker compose up -d postgres redis` 성공
- [ ] `.env`에 키 채움
- [ ] `docker compose up -d api`로 서버 기동
- [ ] `GET /feed` 200 OK
- [ ] `GET /me/intraday_explain` 200 OK (시세 키 정상)
- [ ] `GET /me/recap` 200 OK
- [ ] 로그에 에러 없음, 중요 메트릭 지표 상승
