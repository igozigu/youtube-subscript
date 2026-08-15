# YouTube 채널/재생목록 대본 추출기

YouTube 채널 또는 재생목록 URL을 입력하면, 해당 영상들의 자막(대본) 텍스트를 추출하여 다운로드 가능한 형태로 제공하는 웹 애플리케이션입니다.

## ✨ 주요 기능

- **채널/재생목록 자동 판별**: URL만 붙여넣으면 채널인지 재생목록인지 자동으로 인식
- **영상 선택**: 전체 선택, 일부 선택, 최근 N개 선택 지원
- **실시간 진행률**: WebSocket을 통한 실시간 처리 상태 표시
- **다양한 출력 형식**: ZIP (개별 txt), Markdown (통합), JSON
- **자동 자막 지원**: 수동 자막 → 자동 생성 자막 → yt-dlp fallback 순서로 시도
- **에러 처리**: 자막 없는 영상은 건너뛰고 계속 진행
- **Rate Limit 대응**: 지수 백오프 재시도 로직 내장

## 🛠 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI |
| 영상 목록 수집 | yt-dlp |
| 대본 추출 | youtube-transcript-api + yt-dlp fallback |
| 프론트엔드 | React (Vite) |
| 실시간 통신 | WebSocket |
| 컨테이너화 | Docker, docker-compose |

## 🚀 실행 방법

### 방법 1: Docker Compose (권장)

```bash
# 환경변수 설정
cp .env.example .env

# 서비스 시작
docker compose up -d

# 브라우저에서 접속
# http://localhost:3000
```

### 방법 2: 로컬 실행 (개발용)

#### 백엔드

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# yt-dlp 설치 (시스템에 없는 경우)
pip install yt-dlp

# 서버 시작
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 프론트엔드

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

브라우저에서 `http://localhost:5173` 접속 (Vite 개발 서버가 API를 백엔드로 프록시합니다)

## 📖 사용법

1. 웹 UI에 YouTube 채널 URL 또는 재생목록 URL을 붙여넣습니다
2. "영상 목록 가져오기" 버튼을 클릭합니다
3. 추출할 영상을 선택합니다 (전체/일부/최근 N개)
4. 출력 형식(ZIP/Markdown/JSON)을 선택합니다
5. "대본 추출 시작" 버튼을 클릭합니다
6. 실시간 진행률을 확인하며 완료를 기다립니다
7. 완료 후 원하는 형식으로 다운로드합니다

## 📋 지원 URL 형식

| URL 패턴 | 유형 |
|---|---|
| `https://www.youtube.com/@handle` | 채널 |
| `https://www.youtube.com/@handle/videos` | 채널 |
| `https://www.youtube.com/channel/UCxxxxxx` | 채널 |
| `https://www.youtube.com/playlist?list=PLxxxxxx` | 재생목록 |
| `https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx` | 재생목록 |

## ⚙️ 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DEFAULT_LANGUAGES` | `ko,en` | 자막 언어 우선순위 |
| `FETCH_DELAY_MS` | `1500` | 영상 간 요청 딜레이 (ms) |
| `MAX_CONCURRENT` | `3` | 최대 동시 처리 수 |
| `COOKIE_FILE_PATH` | - | YouTube 인증 쿠키 파일 경로 |
| `OUTPUT_DIR` | `./data/output` | 결과물 저장 경로 |

## 🧪 테스트

```bash
cd backend
python -m pytest tests/ -v
```

## ⚠️ 알려진 제약사항

- YouTube의 봇 감지 정책에 의해 대량 요청 시 차단될 수 있습니다
  - 쿠키 파일(`cookies.txt`)을 업로드하여 인증을 우회할 수 있습니다
  - 요청 간 딜레이를 늘려 차단 위험을 줄일 수 있습니다
- 자동 생성 자막의 품질은 YouTube의 음성 인식 정확도에 의존합니다
- 비공개 또는 삭제된 영상의 자막은 추출할 수 없습니다

## 📄 라이선스

MIT License
