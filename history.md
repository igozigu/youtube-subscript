# 📜 프로젝트 개발 및 대화 히스토리 (History)

## 📌 1. 프로젝트 시작 및 요구사항 분석

- **프로젝트 명**: YouTube 채널/재생목록 대본 추출기 (`youtube-subscript`)
- **작업 경로**: `c:\Users\hjkim\Downloads\Git_Repo\youtube-subscript`
- **GitHub 리포지토리**: [igozigu/youtube-subscript](https://github.com/igozigu/youtube-subscript)
- **주요 목표**:
  - YouTube 채널 및 재생목록 URL을 자동 판별하여 영상 목록 수집
  - 영상별 대본(자막)을 순수 텍스트로 정제하여 일괄 추출
  - 1-클릭 데스크톱 팝업 창(GUI App)으로 복잡한 서버 기동 없이 간편 구동
  - ZIP, Markdown, JSON 형식의 결과 파일 생성 및 자동 저장 폴더 열기
  - YouTube 봇 감지/차단(429) 대응 및 `cookies.txt` 우회 지원

---

## 🛠 2. 시스템 환경 분석

- **OS**: Windows 11 (PowerShell)
- **Python**: 3.14.6
- **GUI Framework**: CustomTkinter
- **GitHub CLI**: `gh` (계정: `igozigu` 연동)
- **실행 방식**: `실행하기.bat` 더블 클릭 (1-Click Popup GUI)

---

## 🚀 3. 단계별 구현 및 개선 과정

### 1단계: 초기 백엔드 및 모듈 구축
- `url_parser.py`: 채널 및 재생목록 URL 정규식 자동 판별
- `video_lister.py`: `yt-dlp --flat-playlist --dump-json` 메타데이터 수집
- `transcript_fetcher.py`: `youtube-transcript-api` + `yt-dlp` 자동자막 fallback
- `text_cleaner.py`: WEBVTT 헤더, 타임스탬프, HTML 태그, 비텍스트 태그 정제
- `exporter.py`: ZIP, Markdown, JSON 파일 생성
- `models.py`: 데이터 모델 스키마

### 2단계: 단위 테스트 및 검증
- `test_url_parser.py`, `test_transcript_fetcher.py`, `test_exporter.py` 총 18개 단위 테스트 작성 및 100% 통과.

### 3단계: 팝업 프로그램 (GUI App) 구현
- 복잡한 터미널/웹서버 구동 대신 **데스크톱 팝업 프로그램(`gui_app.py`)** 구현.
- CustomTkinter 기반 모던 윈도우 UI 적용:
  - URL 입력 및 영상 목록 실시간 비동기 로딩
  - 쇼츠/라이브 필터링 및 `cookies.txt` 브라우저 파일 선택 지원
  - 전체 선택 / 선택 해제 / 최근 N개 선택 도구
  - 실시간 프로그레스 바 및 영상별 상태 라벨(대기/추출중/완료/자막없음/실패)
  - 출력 포맷 옵션(모두 생성 / ZIP / MD / JSON)
  - 작업 완료 시 결과 요약 안내 및 `저장 폴더 열기` 기능

### 4단계: 1-클릭 실행 파일 (`실행하기.bat`) 제공
- 사용자가 더블 클릭 한 번으로 가상환경 자동 구성 및 `pythonw gui_app.py`를 호출하여 검은 콘솔창 없이 즉시 프로그램 창이 뜨도록 구현.

### 5단계: [WinError 2] 프로세스 실행 오류 해결 및 네이티브 라이브러리 전환
- **원인**: 윈도우 환경에서 외부 `yt-dlp.exe` 바이너리 호출(`create_subprocess_exec`) 시 시스템 PATH 부재로 `[WinError 2] 지정된 파일을 찾을 수 없습니다` 오류 발생.
- **조치**:
  - `video_lister.py`와 `transcript_fetcher.py`를 파이썬 내장 라이브러리인 `yt_dlp.YoutubeDL` API 및 `asyncio.to_thread`를 직접 사용하도록 전면 리팩토링.
  - 단일 영상, 쇼츠, 재생목록 파라미터가 포함된 watch URL(`&list=...`)에 대한 자동 폴백 지원.
  - 외부 바이너리 종속성 완전 제거로 모든 윈도우 환경에서 안정적으로 동작하도록 개선.

### 6단계: 검은 cmd 콘솔 창 깜빡임 없는 완전 무음 런처(`실행하기.vbs`) 추가
- Windows WScript 셸을 활용한 `실행하기.vbs` 및 `run.vbs` 추가 (창 플래그 `SW_HIDE=0` 적용).
- 더블 클릭 시 검은 cmd 창이 0.1초도 나타나지 않고 곧바로 프로그램 팝업 창만 뜨도록 개선.

### 7단계: 불필요한 하위 폴더 제거 및 직관적인 파일 직접 저장
- 영상 추출 시 매번 생성되던 UUID 하위 폴더(`output/{job_id}/`)를 제거.
- 모든 영상 대본(`{업로드일}_{영상제목}.txt`) 및 통합 문서(`.md`, `.json`, `.zip`)가 `output/` 폴더 바로 아래에 깔끔하게 직접 생성되도록 개선.

### 8단계: 다른 PC 이동 시 1-클릭 자동 환경 구축 및 포터블 지원 강화
- **타 PC 이동 시 실행 가능성 검증**:
  - `backend/venv`가 없는 다른 PC에 리포지토리를 복사/클론해도 `실행하기.vbs` 또는 `실행하기.bat` 실행 시 자동으로 Python(`python` 또는 `py`)을 탐색하여 가상환경 생성 및 의존성 라이브러리를 자동 설치 후 앱을 기동하도록 개선.
  - Python이 설치되지 않은 환경에서는 다운로드 안내 및 공식 다운로드 페이지 링크를 팝업하도록 예외 처리.
  - 외부 바이너리 종속성(ffmpeg/yt-dlp exe 등) 없이 순수 Python 라이브러리 기반으로 완벽한 포터블 독립 실행 환경 완성.

---

## 📊 4. 현재 프로젝트 최종 구조

```
youtube-subscript/
├── 실행하기.vbs              # ⭐ 검은 창 없는 완전 무음 1-클릭 실행 파일
├── 실행하기.bat              # 배치 실행 파일
├── run.vbs / run.bat        # 영문 실행 파일
├── gui_app.py               # 데스크톱 팝업 GUI 프로그램
├── backend/
│   ├── requirements.txt     # 백엔드 의존성 (customtkinter 포함)
│   ├── venv/                # Python 가상환경
│   ├── app/
│   │   ├── main.py          # FastAPI 엔트리포인트
│   │   ├── url_parser.py    # URL 판별
│   │   ├── video_lister.py  # yt-dlp 목록 수집
│   │   ├── transcript_fetcher.py # 자막 추출 & 쿠키 지원
│   │   ├── text_cleaner.py  # 자막 정제
│   │   ├── exporter.py      # ZIP / MD / JSON 생성
│   │   ├── job_manager.py   # 작업 관리
│   │   └── models.py        # Pydantic 모델
│   └── tests/
│       ├── test_url_parser.py
│       ├── test_transcript_fetcher.py
│       └── test_exporter.py
├── frontend/                # (선택적) 웹 UI 리액트 앱
├── output/                  # 추출된 파일 저장소 (.gitignore 대상)
├── .env.example
├── .gitignore
├── README.md
├── history.md               # (본 문서)
└── walkthrough.md           # 프로젝트 명세서
```

---

## 🎯 5. 최종 검증 결과

1. **단위 테스트**: `python -m pytest tests/ -v` → **18 passed** (100% 통과)
2. **GUI App 검증**: `python -c "import gui_app"` → **정상 로드 확인**
3. **GitHub 동기화**: [igozigu/youtube-subscript](https://github.com/igozigu/youtube-subscript) 리포지토리에 푸시 완료
