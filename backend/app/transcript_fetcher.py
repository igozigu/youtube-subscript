import asyncio
import os
import http.cookiejar
import requests
import yt_dlp
from typing import Tuple, Optional, List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    RequestBlocked,
    IpBlocked,
)
from .text_cleaner import clean_transcript


class YoutubeBlockedError(Exception):
    """YouTube 봇 감지 / IP 차단(429)으로 자막 추출이 제한된 경우 발생하는 예외"""
    pass


def _load_cookie_jar(cookie_path: Optional[str]) -> Optional[http.cookiejar.MozillaCookieJar]:
    """Netscape 형식의 cookies.txt 파일을 CookieJar로 로드한다."""
    if not cookie_path or not os.path.exists(cookie_path):
        return None
    try:
        jar = http.cookiejar.MozillaCookieJar()
        jar.load(cookie_path, ignore_discard=True, ignore_expires=True)
        return jar
    except Exception:
        return None


def _fetch_subtitles_via_ytdlp_sync(
    video_id: str, languages: List[str], cookie_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    yt-dlp의 메타데이터에서 직접 자막 스트림 URL(수동/자동 자막)을 추출하여 다운로드한다.
    쿠키 파일이 설정되어 있으면 인증 쿠키를 첨부하여 다운로드한다.
    """
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "too many requests" in err_str or "bot" in err_str:
            raise YoutubeBlockedError("YouTube 봇 감지(429): 브라우저 쿠키(cookies.txt) 등록이 필요합니다.")
        return None, None

    if not info:
        return None, None

    manual_subs = info.get("subtitles", {}) or {}
    auto_subs = info.get("automatic_captions", {}) or {}

    # 자막 트랙이 전혀 없는 영상인 경우
    if not manual_subs and not auto_subs:
        return None, None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    cookie_jar = _load_cookie_jar(cookie_path)

    has_429_block = False

    def _download_track(formats_list) -> Optional[str]:
        nonlocal has_429_block
        # VTT 포맷 우선 탐색, 없으면 첫 번째 포맷
        url = next(
            (f["url"] for f in formats_list if f.get("ext") == "vtt"),
            formats_list[0]["url"],
        )
        try:
            r = requests.get(url, headers=headers, cookies=cookie_jar, timeout=15)
            if r.status_code == 200 and r.text:
                if "<html>" in r.text and ("429" in r.text or "automated queries" in r.text):
                    has_429_block = True
                    return None
                cleaned = clean_transcript(r.text)
                if cleaned:
                    return cleaned
            elif r.status_code == 429:
                has_429_block = True
        except Exception:
            pass
        return None

    # 1. 요청 언어 순서대로 수동 자막 탐색
    for target_lang in languages:
        if target_lang in manual_subs and manual_subs[target_lang]:
            res_text = _download_track(manual_subs[target_lang])
            if res_text:
                return res_text, target_lang

    # 2. 요청 언어 순서대로 자동 생성 자막 탐색
    for target_lang in languages:
        if target_lang in auto_subs and auto_subs[target_lang]:
            res_text = _download_track(auto_subs[target_lang])
            if res_text:
                return res_text, target_lang

    # 3. 요청 언어 외 사용 가능한 첫 번째 자막 fallback
    all_subs = {**manual_subs, **auto_subs}
    for lang_code, formats in all_subs.items():
        if formats:
            res_text = _download_track(formats)
            if res_text:
                return res_text, lang_code

    # 자막 트랙은 존재하나 429로 다운로드가 차단된 경우 예외 발생
    if has_429_block and not cookie_path:
        raise YoutubeBlockedError("YouTube 봇 감지(429): 브라우저 쿠키(cookies.txt) 등록이 필요합니다.")

    return None, None


async def fetch_transcript(
    video_id: str, languages: List[str] = ["ko", "en"]
) -> Tuple[Optional[str], Optional[str]]:
    """
    영상의 자막(대본)을 추출한다.
    - 자막이 존재하는데 429로 차단된 경우 YoutubeBlockedError 예외 발생
    - 자막이 실제로 없는 경우 (None, None) 반환
    - 정상 추출 시 (정제된 텍스트, 언어 코드) 반환
    """
    cookie_path = os.environ.get("COOKIE_FILE_PATH")

    # 1차 시도: yt-dlp 다이렉트 캡션 스트림 추출
    try:
        cleaned, lang = await asyncio.to_thread(
            _fetch_subtitles_via_ytdlp_sync, video_id, languages, cookie_path
        )
        if cleaned:
            return cleaned, lang
    except YoutubeBlockedError:
        raise
    except Exception:
        pass

    # 2차 시도: youtube-transcript-api
    try:
        if cookie_path and os.path.exists(cookie_path):
            ytt_api = YouTubeTranscriptApi(cookie_path=cookie_path)
        else:
            ytt_api = YouTubeTranscriptApi()

        transcript = await asyncio.to_thread(
            ytt_api.fetch, video_id, languages=languages
        )
        text_parts = [entry.text for entry in transcript]
        raw_text = "\n".join(text_parts)
        cleaned = clean_transcript(raw_text)
        if cleaned:
            return cleaned, languages[0]
    except (RequestBlocked, IpBlocked):
        if not cookie_path:
            raise YoutubeBlockedError("YouTube 봇 감지(429): 브라우저 쿠키(cookies.txt) 등록이 필요합니다.")
    except (TranscriptsDisabled, NoTranscriptFound):
        return None, None
    except Exception:
        pass

    return None, None
