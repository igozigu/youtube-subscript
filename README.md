# 📺 YouTube 채널/재생목록 대본 추출기

YouTube 채널 또는 재생목록 URL을 입력하면, 포함된 영상들의 자막(대본) 텍스트를 자동으로 추출하여 다운로드할 수 있는 웹 애플리케이션입니다.

---

## ✨ 주요 기능

- **채널 / 재생목록 자동 감지**: YouTube URL만 붙여넣으면 채널/재생목록을 자동 판별하여 영상 목록 조회
- **선택적 대본 추출**: 전체 선택, 개별 체크박스 선택, 최근 N개 선택 지원
- **실시간 진행 상황 표시**: WebSocket 기반 실시간 진행률 및 영상별 처리 상태(대기/처리중/완료/자막없음/실패) 확인
- **다양한 다운로드 형식**:
  - **ZIP**: 영상별 개별 `.txt` 파일 (`{업로드일}_{영상제목}.txt`)
  - **Markdown**: 전체 대본을 합친 통합 문서 (제목, 업로드일, 언어, 원본 링크 포함)
  - **JSON**: 구조화된 데이터 (`video_id`, `title`, `upload_date`, `language`, `transcript`, `url`)
- **견고한 대본 추출 파이프라인**:
  - 1차: `youtube-transcript-api` (수동/자동 자막)
  - 2차: `yt-dlp` 자동 생성 자막 fallback
  - 자막 없는 영상은 건너뛰고 전체 작업 지속
- **봇 감지 우회 지원**: YouTube 차단 시 `cookies.txt` 파일 업로드 지원

---

## 🛠 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.11+, FastAPI, Uvicorn |
| 영상 목록 수집 | `yt-dlp` |
| 자막 추출 | `youtube-transcript-api`, `yt-dlp` |
| 프론트엔드 | React 19, Vite |
| 실시간 통신 | WebSocket |

---

## 🚀 빠른 시작 가이드 (실행 방법)

### 1. 백엔드 실행 (Terminal 1)

```powershell
# 백엔드 디렉터리로 이동
cd backend

# 가상환경 활성화 (이미 생성되어 있는 경우)
.\venv\Scripts\activate

# 의존성 설치 (최초 1회)
pip install -r requirements.txt

# 백엔드 서버 구동 (포트 8000)
uvicorn app.main:app --reload --port 8000
```

### 2. 프론트엔드 실행 (Terminal 2)

```powershell
# 프론트엔드 디렉터리로 이동
cd frontend

# 패키지 설치 (최초 1회)
npm install

# 개발 서버 구동 (포트 5173)
npm run dev
```

### 3. 브라우저 접속

웹 브라우저를 열고 **`http://localhost:5173`** 으로 접속합니다.

---

## 📖 사용 방법

1. **링크 입력**: YouTube 채널 URL 또는 재생목록 URL을 입력창에 붙여넣고 **"영상 목록 가져오기"**를 누릅니다.
   - *팁*: 쇼츠(Shorts)나 라이브 방송을 포함하려면 체크박스를 켭니다.
   - *팁*: YouTube 차단이 발생할 경우 하단 `🍪 YouTube 인증 우회 (쿠키 파일 설정)`에서 브라우저에서 추출한 `cookies.txt`를 등록합니다.
2. **영상 선택**: 목록에서 대본을 추출할 영상을 선택합니다 (전체 선택, 최근 N개 선택 등).
3. **설정 및 시작**: 선호 언어(기본: `ko, en`) 및 기본 출력 형식을 확인하고 **"대본 추출 시작"**을 클릭합니다.
4. **진행 확인**: 실시간 프로그레스 바와 영상별 처리 상태를 확인합니다.
5. **결과 다운로드**: 작업 완료 후 **Markdown**, **JSON**, **ZIP** 버튼 중 원하는 형식을 클릭하여 다운로드합니다.

---

## 📋 지원되는 URL 형식

- 채널 핸들: `https://www.youtube.com/@handle`
- 채널 영상 탭: `https://www.youtube.com/@handle/videos`
- 채널 ID: `https://www.youtube.com/channel/UCxxxxxx`
- 재생목록: `https://www.youtube.com/playlist?list=PLxxxxxx`
- 재생목록 내 영상: `https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx`

---

## 🧪 테스트 실행

```powershell
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

---

## 📄 라이선스

MIT License
