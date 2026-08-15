# 📜 프로젝트 개발 및 대화 히스토리 (History)

## 📌 1. 프로젝트 시작 및 요구사항 분석

- **프로젝트 명**: YouTube 채널/재생목록 대본 추출기 (`youtube-subscript`)
- **작업 경로**: `c:\Users\hjkim\Downloads\Git_Repo\youtube-subscript`
- **GitHub 리포지토리**: [igozigu/youtube-subscript](https://github.com/igozigu/youtube-subscript)
- **주요 목표**:
  - YouTube 채널 및 재생목록 URL을 자동 판별하여 영상 목록 수집
  - 영상별 대본(자막)을 순수 텍스트로 정제하여 일괄 추출
  - WebSocket 기반 실시간 진행률 표시
  - ZIP, Markdown, JSON 형식의 다운로드 제공
  - YouTube 봇 감지/차단(429) 대응 및 `cookies.txt` 우회 지원

---

## 🛠 2. 시스템 환경 분석

- **OS**: Windows 11 (PowerShell)
- **Python**: 3.14.6
- **Node.js**: v24.18.0 / npm
- **GitHub CLI**: `gh` (계정: `igozigu` 연동)
- **배포 방식**: 로컬 네이티브 환경 구동 (Python FastAPI + Node React/Vite)

---

## 🚀 3. 단계별 구현 및 개선 과정

### 1단계: 초기 백엔드 및 프론트엔드 기본 골격 구축
1. **백엔드 (FastAPI)**:
   - `url_parser.py`: 채널(@handle, /channel/) 및 재생목록(list=) 정규식 판별
   - `video_lister.py`: `yt-dlp --flat-playlist --dump-json` 메타데이터 파싱
   - `transcript_fetcher.py`: `youtube-transcript-api` (1차) + `yt-dlp` 자동자막 fallback (2차)
   - `text_cleaner.py`: 자막 텍스트에서 타임스탬프, HTML 태그, 비텍스트 태그 정제
   - `job_manager.py`: 비동기 작업 큐 및 WebSocket 진행률 브로드캐스팅
   - `exporter.py`: ZIP, Markdown, JSON 파일 생성 로직
   - `models.py`: Pydantic 스키마 정의
   - `main.py`: REST API 엔드포인트 및 CORS, 헬스체크 구성
2. **프론트엔드 (React + Vite)**:
   - `UrlInput.jsx`: 링크 입력 및 쇼츠/라이브 필터 토글
   - `VideoList.jsx`: 영상 체크박스 선택, 최근 N개 선택, 언어/출력 포맷 설정
   - `ProgressPanel.jsx`: 진행률 바 및 상태(⏳🔄✅⚠️❌) 리스트 표시
   - `DownloadOptions.jsx`: 완료 요약 통계 및 포맷별 다운로드 버튼
   - `client.js`: 백엔드 API 연동 및 WebSocket 통신

### 2단계: 문제 해결 및 버전 호환성 조치
- **yt-dlp / Python 3.14 의존성 이슈**:
  - `requirements.txt`의 하드코딩된 버전 핀을 유연한 버전(`>=`)으로 완화하여 Python 3.14 호환성 확보.
- **youtube-transcript-api (v1.2.4) 예외 클래스 변경**:
  - 구버전의 `TooManyRequests`, `NoTranscriptAvailable`을 최신 라이브러리의 `RequestBlocked`, `IpBlocked`, `TranscriptsDisabled`, `NoTranscriptFound`로 수정.
- **단위 테스트 작성 및 검증**:
  - `test_url_parser.py` (9개 테스트), `test_transcript_fetcher.py` (4개 테스트), `test_exporter.py` (5개 테스트) 총 18개 테스트 전체 통과.

### 3단계: 프론트↔백엔드 연동 버그 수정 및 명세 고도화
1. **데이터 필드 매핑 일치**:
   - 프론트엔드의 camelCase 참조(`id`, `uploadDate`, `items`, `format=markdown`)를 백엔드 응답 스키마(`job_id`, `video_id`, `upload_date`, `results`, `format=md`)와 완벽 일치하도록 수정.
2. **파일명 표준화**:
   - 명세에 따라 `{업로드일}_{영상제목}.txt` 형식으로 파일 저장 및 중복 파일명 충돌 방지 로직 적용.
3. **VTT 자막 파서 강화**:
   - WEBVTT 메타데이터 라인, 타임스탬프(`00:00:00.000 --> ...`), 인라인 태그 및 중복 라인 정리 로직 고도화.
4. **쿠키(`cookies.txt`) 업로드 기능**:
   - 백엔드에 쿠키 파일 업로드/삭제 API(`POST/DELETE /api/cookies`) 추가.
   - `transcript_fetcher.py`에 쿠키 파일 전달 로직 반영.
   - 프론트엔드 `UrlInput.jsx`에 접이식 쿠키 파일 등록 UI 컴포넌트 추가.
5. **JSON 스키마 보강**:
   - `video_id`, `title`, `upload_date`, `language`, `status`, `transcript`, `url` 필드 완비.

### 4단계: Docker 의존성 제거 및 로컬 전용 가이드 개편
- 사용자 요청에 따라 Docker 관련 파일(`docker-compose.yml`, Dockerfile 등) 제거.
- `walkthrough.md`와 `README.md`를 Python 및 Node 로컬 네이티브 실행 환경 기준으로 전면 업데이트.

---

## 📊 4. 현재 프로젝트 최종 구조

```
youtube-subscript/
├── backend/
│   ├── requirements.txt         # 백엔드 의존성
│   ├── venv/                    # Python 가상환경
│   ├── app/
│   │   ├── main.py              # FastAPI 서버 엔트리포인트
│   │   ├── url_parser.py        # URL 판별
│   │   ├── video_lister.py      # yt-dlp 목록 수집
│   │   ├── transcript_fetcher.py # 자막 추출 & 쿠키 지원
│   │   ├── text_cleaner.py      # 자막 정제
│   │   ├── exporter.py          # ZIP / MD / JSON 생성
│   │   ├── job_manager.py       # 작업 관리 & WebSocket
│   │   └── models.py            # Pydantic 모델
│   └── tests/
│       ├── test_url_parser.py
│       ├── test_transcript_fetcher.py
│       └── test_exporter.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js           # 프록시 설정 (8000번 포트)
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       ├── api/client.js        # API 및 WebSocket 클라이언트
│       └── components/
│           ├── UrlInput.jsx     # URL 입력 & 쿠키 관리
│           ├── VideoList.jsx    # 영상 목록 및 선택
│           ├── ProgressPanel.jsx # 실시간 진행률
│           └── DownloadOptions.jsx # 결과 다운로드
├── data/
│   └── output/                  # 추출된 파일 저장소
├── .env.example
├── .gitignore
├── README.md
├── history.md                   # (본 문서)
└── walkthrough.md               # 프로젝트 개발 명세
```

---

## 🎯 5. 최종 검증 결과

1. **단위 테스트**: `python -m pytest tests/ -v` → **18 passed** (100% 통과)
2. **프론트엔드 빌드**: `npm run build` → **정상 빌드 완료** (0 에러)
3. **GitHub 동기화**: [igozigu/youtube-subscript](https://github.com/igozigu/youtube-subscript) 리포지토리에 푸시 완료
