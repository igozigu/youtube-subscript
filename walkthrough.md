# YouTube 채널/재생목록 대본 추출기 개발 명세 및 가이드

> 이 문서는 YouTube 채널 및 재생목록에서 대본(자막)을 추출하는 웹 애플리케이션의 개발 명세서입니다. Python(FastAPI) 백엔드와 React(Vite) 프론트엔드로 로컬 구동됩니다.

---

## 1. 프로젝트 개요

**목표**: 사용자가 YouTube **채널 URL** 또는 **재생목록(playlist) URL**을 입력하면, 해당 채널/재생목록에 포함된 **모든 영상의 대본(자막) 텍스트만** 추출하여 다운로드 가능한 형태로 제공하는 웹 애플리케이션.

**핵심 사용자 흐름**:
1. 사용자가 웹 UI에 채널 URL 또는 재생목록 URL을 입력한다.
2. 앱이 해당 URL에 포함된 영상 목록(제목, video_id, 업로드일, 재생시간)을 가져와 화면에 리스트로 보여준다.
3. 사용자가 (a) 전체 선택 (b) 일부 선택 (c) 최근 N개 선택 중 하나를 고른다.
4. 앱이 선택된 영상들의 대본을 순차적으로 추출한다. 진행률(progress bar)과 영상별 상태를 실시간으로 보여준다.
5. 완료 후 각 영상별 텍스트 파일(zip) 또는 전체를 합친 파일(markdown/json)로 다운로드한다.
6. 자막이 없는 영상은 "자막 없음"으로 명시하고 건너뛴다 (에러로 전체 중단시키지 않음).

---

## 2. 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, Uvicorn |
| 영상 목록 수집 | `yt-dlp` (channel/playlist flat 파싱) |
| 대본 추출 | `youtube-transcript-api` (1차), 실패 시 `yt-dlp --write-auto-subs` fallback |
| 비동기 작업 처리 | FastAPI `BackgroundTasks` |
| 프론트엔드 | React 19, Vite |
| 실시간 진행률 | WebSocket (`/ws/jobs/{job_id}`) |
| 저장소 | 로컬 파일시스템 (`data/output/`) |
| 언어 처리 | 한국어(ko), 영어(en) 자막 우선, 다국어 지원 |

---

## 3. 상세 기능 요구사항

### 3.1 입력 처리 (URL 파싱)
- 지원 URL 패턴:
  - `https://www.youtube.com/@handle`
  - `https://www.youtube.com/@handle/videos`
  - `https://www.youtube.com/channel/UCxxxxxx`
  - `https://www.youtube.com/playlist?list=PLxxxxxx`
  - `https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx` (재생목록 내 개별 영상 링크)
- URL 형태만으로 "채널"인지 "재생목록"인지 자동 판별 (`detect_url_type(url) -> "channel" | "playlist" | "invalid"`).
- 잘못된 URL 입력 시 직관적인 한국어 에러 메시지 반환.

### 3.2 영상 목록 수집
- `yt-dlp`를 `--flat-playlist --dump-json` 옵션으로 호출하여 영상 다운로드 없이 메타데이터만 수집 (video_id, title, upload_date, duration).
- 쇼츠(Shorts, 60초 미만)와 라이브 스트림 토글 필터링 지원.

### 3.3 대본 추출 로직
- 1차 시도: `youtube-transcript-api`로 video_id에 대해 자막 요청 (언어 우선순위: 기본 `["ko", "en"]`).
- 2차 시도(1차 실패 시): `yt-dlp --write-auto-subs --skip-download`로 자동 자막(VTT) 받아 파싱.
- 두 방법 모두 실패하면 해당 영상은 "자막 없음"(`NO_SUBTITLE`)으로 표시하고 스킵. 전체 작업은 계속 진행.
- 자막 텍스트 정제: WEBVTT 헤더, 타임스탬프 라인, HTML 태그, 비텍스트 태그([Music] 등), 연속 중복 라인 제거.
- YouTube 봇 감지/차단(429) 대비:
  - exponential backoff 재시도 로직 내장
  - 브라우저 추출 쿠키 파일(`cookies.txt`) 업로드 및 적용 지원

### 3.4 결과 저장 및 다운로드 형식
- 개별 영상 파일명: `data/output/{job_id}/{업로드일}_{영상제목}.txt` (특수문자 sanitize)
- 지원 출력 형식:
  1. **ZIP**: 개별 txt 파일들을 압축한 zip 파일
  2. **Markdown (MD)**: 전체 영상 대본을 하나로 합치고, 제목(`##`), 업로드일, 언어, 원본 URL 메타정보 포함
  3. **JSON**: `video_id`, `title`, `upload_date`, `language`, `status`, `transcript`, `url` 필드를 포함한 정형 데이터

### 3.5 실시간 진행률 표시 (UX)
- 전체 영상 수 대비 처리 완료 수 및 진행률(%) 바 표시.
- 각 영상 처리 상태 구분: 대기중(⏳), 처리중(🔄), 완료(✅), 자막없음(⚠️), 실패(❌).
- WebSocket을 통해 백엔드에서 프론트엔드로 실시간 push.

---

## 4. 디렉터리 구조

```
youtube-subscript/
├── backend/
│   ├── requirements.txt         # Python 의존성
│   ├── venv/                    # 가상환경
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트 & API 라우트
│   │   ├── url_parser.py        # URL 타입 판별
│   │   ├── video_lister.py      # yt-dlp 기반 영상 목록 수집
│   │   ├── transcript_fetcher.py # 대본 추출 (API + yt-dlp fallback + 쿠키)
│   │   ├── text_cleaner.py      # 자막 텍스트 정제
│   │   ├── exporter.py          # ZIP / Markdown / JSON 내보내기
│   │   ├── job_manager.py       # 작업 관리 & WebSocket 알림
│   │   └── models.py            # Pydantic 스키마
│   └── tests/
│       ├── test_url_parser.py
│       ├── test_transcript_fetcher.py
│       └── test_exporter.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js           # 프록시 설정 (/api, /ws -> localhost:8000)
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # 메인 애플리케이션
│       ├── App.css              # 모던 UI 스타일
│       ├── api/client.js        # API 및 WebSocket 클라이언트
│       └── components/
│           ├── UrlInput.jsx     # URL 입력 & 쿠키 업로드
│           ├── VideoList.jsx    # 영상 목록 & 선택 UI
│           ├── ProgressPanel.jsx # 실시간 진행률 패널
│           └── DownloadOptions.jsx # 다운로드 옵션 및 통계
├── data/
│   └── output/                  # 대본 결과물 저장 경로
├── .env.example
├── .gitignore
├── README.md
├── history.md                   # 개발 진행 이력
└── walkthrough.md               # (본 문서)
```

---

## 5. API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/resolve` | YouTube URL 입력 → 채널/재생목록 판별 및 영상 목록 반환 |
| POST | `/api/jobs` | 선택된 영상 리스트 + 설정으로 대본 추출 작업 생성 (`job_id` 반환) |
| GET | `/api/jobs/{job_id}` | 작업 상태 및 영상별 처리 결과 조회 |
| WS | `/ws/jobs/{job_id}` | 실시간 진행률 WebSocket 스트림 |
| GET | `/api/jobs/{job_id}/download?format=zip\|md\|json` | 완료된 결과 파일 다운로드 |
| POST | `/api/cookies` | YouTube 인증 우회용 `cookies.txt` 업로드 |
| DELETE | `/api/cookies` | 등록된 쿠키 파일 삭제 |
| GET | `/api/health` | 서버 상태 헬스체크 |

---

## 6. 실행 방법

### 백엔드 실행
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속.

---

## 7. 완료 기준 (Definition of Done)

- [x] 채널 URL과 재생목록 URL 모두 정상 판별 및 영상 목록 조회
- [x] 자막이 있는 영상은 정제된 순수 텍스트 대본 추출
- [x] 자막이 없는 영상은 "자막 없음" 표시 후 계속 진행
- [x] 진행률과 개별 영상 상태 실시간 UI 표시
- [x] ZIP / Markdown / JSON 3가지 형식 다운로드 제공
- [x] Rate limit / 봇 감지 대응 (재시도 + cookies.txt 업로드 UI)
- [x] 단위 테스트 전체 통과 (18/18)
- [x] 로컬 개발 환경에서 즉시 실행 가능
