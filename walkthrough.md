# YouTube 채널/재생목록 대본 추출기 개발 명세 및 가이드

> 이 문서는 YouTube 채널 및 재생목록에서 대본(자막)을 추출하는 **데스크톱 팝업 애플리케이션(`gui_app.py`)** 및 웹 API의 개발 명세서입니다.

---

## 1. 프로젝트 개요

**목표**: 사용자가 YouTube **채널 URL** 또는 **재생목록(playlist) URL**을 입력하면, 해당 채널/재생목록에 포함된 **모든 영상의 대본(자막) 텍스트만** 추출하여 다운로드 가능한 형태로 제공하는 데스크톱 팝업 프로그램.

**실행 방식**:
- `실행하기.bat` 더블 클릭 한 번으로 GUI 팝업 창이 즉시 실행됩니다.

**핵심 사용자 흐름**:
1. 프로그램 창에 채널 URL 또는 재생목록 URL을 입력한다.
2. 앱이 해당 URL에 포함된 영상 목록(제목, video_id, 업로드일, 재생시간)을 가져와 화면에 리스트로 보여준다.
3. 사용자가 (a) 전체 선택 (b) 일부 선택 (c) 최근 N개 선택 중 하나를 고른다.
4. 앱이 선택된 영상들의 대본을 순차적으로 추출한다. 진행률(progress bar)과 영상별 상태를 실시간으로 보여준다.
5. 완료 후 각 영상별 텍스트 파일(zip) 또는 전체를 합친 파일(markdown/json)을 지정 폴더에 생성하고 폴더를 즉시 열어준다.
6. 자막이 없는 영상은 "자막 없음"으로 명시하고 건너뛴다 (에러로 전체 중단시키지 않음).

---

## 2. 기술 스택

| 영역 | 기술 |
|---|---|
| 데스크톱 GUI | CustomTkinter (Python Desktop Popup Window) |
| 영상 목록 수집 | `yt-dlp` (channel/playlist flat 파싱) |
| 대본 추출 | `youtube-transcript-api` (1차), 실패 시 `yt-dlp --write-auto-subs` fallback |
| 저장소 | 로컬 파일시스템 (`data/output/`) |
| 언어 처리 | 한국어(ko), 영어(en) 자막 우선, 다국어 지원 |

---

## 3. 주요 기능 명세

### 3.1 입력 처리 (URL 파싱)
- 지원 URL 패턴:
  - `https://www.youtube.com/@handle`
  - `https://www.youtube.com/@handle/videos`
  - `https://www.youtube.com/channel/UCxxxxxx`
  - `https://www.youtube.com/playlist?list=PLxxxxxx`
  - `https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx`
- URL 형태만으로 "채널"인지 "재생목록"인지 자동 판별 (`detect_url_type(url)`).

### 3.2 대본 추출 및 정제
- 1차: `youtube-transcript-api`
- 2차 fallback: `yt-dlp --write-auto-subs`
- 자막 정제: WEBVTT 헤더, 타임스탬프 라인, HTML 태그, 비텍스트 태그([Music] 등), 연속 중복 라인 제거.
- YouTube 봇 감지/차단(429) 대비:
  - exponential backoff 재시도 로직
  - `cookies.txt` 파일 선택 지원

### 3.3 결과 저장 형식
- 파일명: `data/output/{job_id}/{업로드일}_{영상제목}.txt`
- 출력 포맷:
  1. **ZIP**: 개별 txt 파일들을 압축한 zip 파일
  2. **Markdown (MD)**: 전체 영상 대본 통합 문서 (제목, 업로드일, 언어, 원본 URL 포함)
  3. **JSON**: 구조화된 정형 데이터 (`video_id`, `title`, `upload_date`, `language`, `transcript`, `url`)
  4. **모두 생성**: 3가지 형식을 한 번에 생성

---

## 4. 디렉터리 구조

```
youtube-subscript/
├── 실행하기.bat              # ⭐ 더블 클릭 실행 파일
├── run.bat                  # 영문 실행 파일
├── gui_app.py               # 데스크톱 팝업 GUI 프로그램
├── backend/
│   ├── requirements.txt     # Python 의존성
│   ├── venv/                # 가상환경
│   ├── app/
│   │   ├── main.py          # FastAPI 엔트리포인트 (웹 API)
│   │   ├── url_parser.py    # URL 타입 판별
│   │   ├── video_lister.py  # yt-dlp 영상 목록 수집
│   │   ├── transcript_fetcher.py # 대본 추출 & 쿠키 지원
│   │   ├── text_cleaner.py  # 자막 정제
│   │   ├── exporter.py      # ZIP / MD / JSON 생성
│   │   ├── job_manager.py   # 작업 관리
│   │   └── models.py        # 데이터 모델
│   └── tests/
│       ├── test_url_parser.py
│       ├── test_transcript_fetcher.py
│       └── test_exporter.py
├── frontend/                # (선택적) 웹 UI 리액트 앱
├── data/
│   └── output/              # 결과물 저장 폴더
├── README.md
├── history.md
└── walkthrough.md           # (본 문서)
```
