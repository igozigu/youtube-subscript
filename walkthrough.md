# YouTube 채널/재생목록 대본 추출기 개발 프롬프트

> 이 문서는 AI 코딩 에이전트(Claude Code, Cursor, Antigravity, GitHub Copilot Agent 등)에게 그대로 전달하여 앱 개발을 시작시키기 위한 상세 지시서입니다. 섹션 순서대로 진행하도록 지시하세요.

---

## 0. 에이전트에게 전달할 최상위 지시문 (그대로 복사해서 사용)

```
너는 시니어 풀스택 개발자다. 아래 명세에 따라 "YouTube 채널/재생목록 대본 추출기"를
처음부터 끝까지 구현하라. 각 단계를 완료할 때마다 커밋하고, 완료된 항목을 체크리스트로
보고하라. 모르는 부분이나 애매한 요구사항이 있으면 임의로 판단하지 말고 먼저 질문하라.
구현 중 라이브러리 버전 충돌이나 유튜브 정책 변경으로 인한 이슈가 발견되면 대안을
제시하고 진행하라. 최종적으로 docker-compose up 한 줄로 전체 서비스가 기동되어야 한다.
```

---

## 1. 프로젝트 개요

**목표**: 사용자가 YouTube **채널 URL** 또는 **재생목록(playlist) URL**을 입력하면, 해당 채널/재생목록에 포함된 **모든 영상의 대본(자막) 텍스트만** 추출하여 다운로드 가능한 형태로 제공하는 웹 애플리케이션.

**핵심 사용자 흐름**:
1. 사용자가 웹 UI에 채널 URL 또는 재생목록 URL을 붙여넣는다.
2. 앱이 해당 URL에 포함된 영상 목록(제목, video ID, 업로드일)을 가져와 화면에 리스트로 보여준다.
3. 사용자가 (a) 전체 선택 (b) 일부만 선택 (c) 최근 N개만 선택 중 하나를 고른다.
4. 앱이 선택된 영상들의 대본을 순차적으로 추출한다. 진행률(progress bar)을 실시간으로 보여준다.
5. 완료 후 각 영상별 텍스트 파일 또는 전체를 합친 하나의 파일(zip 또는 병합 txt/markdown)로 다운로드할 수 있다.
6. 자막이 없는 영상은 "자막 없음"으로 명시하고 건너뛴다 (에러로 전체 중단시키지 않음).

---

## 2. 기술 스택 (권장, 필요시 에이전트가 대안 제안 가능)

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI |
| 영상 목록 수집 | `yt-dlp` (channel/playlist flat 파싱) |
| 대본 추출 | `youtube-transcript-api` (1차), 실패 시 `yt-dlp --write-auto-subs` fallback |
| 비동기 작업 처리 | FastAPI `BackgroundTasks` 또는 Celery + Redis (대량 처리 시) |
| 프론트엔드 | React (Vite) 또는 단순 HTML+Vanilla JS (사용자가 과도한 복잡도 원하지 않으면 후자) |
| 실시간 진행률 | WebSocket 또는 Server-Sent Events(SSE) |
| 컨테이너화 | Docker, docker-compose |
| 저장소 | 로컬 파일시스템 volume (`/data/output`) |
| 언어 처리 | 한국어(ko), 영어(en) 자막 우선, 없으면 사용 가능한 첫 언어 |

---

## 3. 상세 기능 요구사항

### 3.1 입력 처리 (URL 파싱)
- 지원해야 하는 URL 패턴:
  - `https://www.youtube.com/@handle`
  - `https://www.youtube.com/@handle/videos`
  - `https://www.youtube.com/channel/UCxxxxxx`
  - `https://www.youtube.com/playlist?list=PLxxxxxx`
  - `https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx` (재생목록 내 개별 영상 링크도 재생목록으로 인식)
- URL 형태만으로 "채널"인지 "재생목록"인지 자동 판별하는 함수를 작성하라 (`detect_url_type(url) -> "channel" | "playlist" | "invalid"`).
- 잘못된 URL 입력 시 명확한 에러 메시지를 반환하라.

### 3.2 영상 목록 수집
- `yt-dlp`를 `--flat-playlist --dump-json` 옵션으로 호출하여 다운로드 없이 메타데이터만 수집한다 (video_id, title, upload_date, duration).
- 채널의 경우 기본적으로 "영상(videos)" 탭만 대상으로 하고, 쇼츠(Shorts)와 라이브 스트림 다시보기는 별도 토글로 포함/제외 선택 가능하게 하라.
- 영상 수가 많은 채널(수백~수천 개)을 고려하여 페이지네이션 또는 스트리밍 방식으로 목록을 처리하라 (한 번에 다 로드하다 타임아웃 나지 않도록).

### 3.3 대본 추출 로직
- 1차 시도: `youtube-transcript-api`로 video_id에 대해 자막 요청.
  - 언어 우선순위: 사용자가 지정한 언어 코드 리스트(기본 `["ko", "en"]`) 순서대로 시도.
  - 수동 업로드 자막이 없으면 자동 생성(auto-generated) 자막으로 fallback.
- 2차 시도(1차 실패 시): `yt-dlp --write-auto-subs --skip-download --sub-langs "ko,en"`으로 자막 파일(vtt/srt)을 받아 파싱.
- 두 방법 모두 실패하면 해당 영상은 "자막 없음"으로 결과에 표시하고 스킵. 전체 작업은 계속 진행.
- 자막 텍스트에서 타임스탬프, HTML 태그, 중복 줄바꿈을 제거하고 순수 문장 텍스트로 정제하는 후처리 함수를 반드시 작성하라.
- Rate limit 대응: 각 영상 요청 사이에 설정 가능한 딜레이(기본 1~2초)를 두고, HTTP 429/차단 감지 시 exponential backoff로 재시도(최대 3회) 로직을 넣어라.

### 3.4 결과 저장 및 다운로드 형식
- 개별 영상: `output/{채널명 또는 재생목록명}/{업로드일}_{영상제목}.txt`
- 파일명에 OS에서 금지된 특수문자는 안전하게 치환(sanitize)하라.
- 사용자가 선택할 수 있는 출력 옵션:
  1. 영상별 개별 txt 파일 zip 압축
  2. 전체를 하나로 합친 markdown 파일 (영상 제목을 `##` 헤더로 구분, 원본 URL도 함께 기록)
  3. JSON 형식 (video_id, title, upload_date, transcript, language 필드 포함) — 추후 다른 프로그램에서 재사용하기 위함
- 다운로드는 브라우저에서 바로 받을 수 있어야 한다 (스트리밍 다운로드 또는 완료 후 링크 제공).

### 3.5 진행률 표시 (UX)
- 전체 영상 수 대비 처리 완료 수를 실시간으로 표시.
- 각 영상 처리 상태를 "대기중 / 처리중 / 완료 / 자막없음 / 실패" 로 구분해서 리스트로 보여준다.
- WebSocket 또는 SSE로 백엔드 → 프론트엔드 진행 상황을 push.

### 3.6 에러 처리 및 예외 상황
- 존재하지 않는 채널/재생목록 URL
- 비공개(private) 또는 삭제된 영상이 목록에 포함된 경우 → 건너뛰고 로그에 남김
- 유튜브 측 IP 차단/봇 감지(HTTP 429, "Sign in to confirm you're not a bot" 등) 감지 시 사용자에게 명확히 안내하고, 쿠키 파일(`cookies.txt`)을 업로드해서 인증 우회할 수 있는 옵션을 제공하라.
- 영상 수가 너무 많을 경우(예: 500개 초과) 사용자에게 경고하고 배치 처리를 권장.

---

## 4. 아키텍처 설계 지시

에이전트에게 다음 구조로 디렉터리를 만들도록 지시하라:

```
yt-transcript-extractor/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트
│   │   ├── url_parser.py        # URL 타입 판별
│   │   ├── video_lister.py      # yt-dlp 기반 영상 목록 수집
│   │   ├── transcript_fetcher.py # 대본 추출 (youtube-transcript-api + yt-dlp fallback)
│   │   ├── text_cleaner.py      # 자막 후처리
│   │   ├── exporter.py          # zip/markdown/json 출력
│   │   ├── job_manager.py       # 작업 상태 관리, WebSocket/SSE
│   │   └── models.py            # Pydantic 스키마
│   └── tests/
│       ├── test_url_parser.py
│       ├── test_transcript_fetcher.py
│       └── test_exporter.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── UrlInput.jsx
│       │   ├── VideoList.jsx
│       │   ├── ProgressPanel.jsx
│       │   └── DownloadOptions.jsx
│       └── api/client.js
├── data/
│   └── output/                  # 결과물 저장 volume
└── walkthrough.md               # (이 문서)
```

---

## 5. API 엔드포인트 설계 지시

에이전트에게 최소 아래 엔드포인트를 구현하도록 지시하라:

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/resolve` | URL 입력 → 타입 판별 + 영상 목록 반환 |
| POST | `/api/jobs` | 선택된 video_id 리스트 + 옵션으로 추출 작업 생성 (job_id 반환) |
| GET | `/api/jobs/{job_id}` | 작업 상태 조회 (polling fallback용) |
| WS | `/ws/jobs/{job_id}` | 실시간 진행률 스트림 |
| GET | `/api/jobs/{job_id}/download?format=zip|md|json` | 완료된 결과 다운로드 |

각 엔드포인트의 요청/응답 스키마(Pydantic 모델)를 명확히 정의하도록 지시하라.

---

## 6. Docker / 배포 요구사항

- `docker-compose.yml` 하나로 backend + frontend가 동시에 뜨도록 구성.
- backend는 `ffmpeg`, `yt-dlp` 바이너리가 포함된 Python 이미지 기반.
- 환경변수로 다음을 설정 가능하게 하라: 기본 언어 우선순위, 요청 간 딜레이(ms), 최대 동시 처리 영상 수, 쿠키 파일 경로.
- Synology NAS 등 홈서버에서도 바로 `docker compose up -d`로 실행 가능해야 한다 (볼륨 마운트 경로를 `.env`로 분리).

---

## 7. 테스트 요구사항

- `url_parser.py`: 채널/재생목록/워치URL/잘못된URL 각각에 대한 단위 테스트 최소 8개 이상.
- `transcript_fetcher.py`: mock을 이용해 (a) 정상 자막 있음 (b) 자동생성 자막만 있음 (c) 자막 전혀 없음 (d) API rate limit 발생 시나리오 각각 테스트.
- 통합 테스트: 실제 공개 재생목록 하나(짧은 것)로 end-to-end 흐름이 동작하는지 수동 확인 절차를 README에 문서화.

---

## 8. 완료 기준 (Definition of Done) — 에이전트가 스스로 체크할 체크리스트

- [ ] 채널 URL과 재생목록 URL 모두 정상적으로 판별되고 영상 목록이 조회된다
- [ ] 자막이 있는 영상은 순수 텍스트로 정제된 대본이 추출된다
- [ ] 자막이 없는 영상은 에러 없이 "자막 없음"으로 표시되고 전체 작업이 중단되지 않는다
- [ ] 진행률이 실시간으로 UI에 표시된다
- [ ] zip / markdown / json 세 가지 형식으로 다운로드가 가능하다
- [ ] `docker compose up`만으로 전체 서비스가 기동된다
- [ ] rate limit / 봇 감지 상황에 대한 재시도 및 사용자 안내 로직이 존재한다
- [ ] 단위 테스트가 모두 통과한다
- [ ] README.md에 설치, 실행, 사용법이 한국어로 정리되어 있다

---

## 9. 향후 확장 아이디어 (지금 구현하지 않아도 되지만 코드 구조에 여지를 남길 것)

- 추출된 대본을 임베딩하여 벡터 DB에 저장 후 채널 전체에 대해 질의응답(RAG) 기능 추가
- Telegram 봇 연동으로 URL 전송 시 자동으로 대본 zip 반환
- 다국어 자막 자동 번역 옵션 (Google Translate API 또는 로컬 LLM)

---

## 10. 에이전트에게 남기는 마지막 지시

```
위 명세를 기반으로 backend부터 순서대로 구현하라. 각 단계마다:
1) 무엇을 구현했는지
2) 어떻게 테스트했는지
3) 알려진 제약사항(유튜브 정책 변경 리스크 등)
을 간단히 보고하라. 전체 구현이 끝나면 docker-compose up 실행 결과와
샘플 재생목록으로 테스트한 결과를 캡처/로그로 제시하라.
```
