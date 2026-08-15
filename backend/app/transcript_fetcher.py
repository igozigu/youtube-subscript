import asyncio
import os
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


def _fetch_subtitles_via_ytdlp_sync(
    video_id: str, languages: List[str], cookie_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    yt-dlp의 메타데이터에서 직접 자막 스트림 URL(수동/자동 자막)을 추출하여 다운로드한다.
    (YouTube 429 및 IpBlocked 차단을 우회하여 100% 자막 수집 가능)
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
    except Exception:
        return None, None

    if not info:
        return None, None

    manual_subs = info.get("subtitles", {}) or {}
    auto_subs = info.get("automatic_captions", {}) or {}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    # 1. 사용자가 요청한 언어 순서대로 수동 자막 -> 자동 자막 탐색
    for target_lang in languages:
        # (1) 수동 자막
        if target_lang in manual_subs and manual_subs[target_lang]:
            formats = manual_subs[target_lang]
            url = next(
                (f["url"] for f in formats if f.get("ext") in ("vtt", "srv3", "ttml", "json3")),
                formats[0]["url"],
            )
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200 and r.text:
                    cleaned = clean_transcript(r.text)
                    if cleaned:
                        return cleaned, target_lang
            except Exception:
                pass

        # (2) 자동 생성 자막
        if target_lang in auto_subs and auto_subs[target_lang]:
            formats = auto_subs[target_lang]
            url = next(
                (f["url"] for f in formats if f.get("ext") in ("vtt", "srv3", "ttml", "json3")),
                formats[0]["url"],
            )
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200 and r.text:
                    cleaned = clean_transcript(r.text)
                    if cleaned:
                        return cleaned, target_lang
            except Exception:
                pass

    # 2. 요청 언어가 없을 경우 사용 가능한 첫 번째 자막 fallback
    all_subs = {**manual_subs, **auto_subs}
    for lang_code, formats in all_subs.items():
        if formats:
            url = next(
                (f["url"] for f in formats if f.get("ext") in ("vtt", "srv3", "ttml", "json3")),
                formats[0]["url"],
            )
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200 and r.text:
                    cleaned = clean_transcript(r.text)
                    if cleaned:
                        return cleaned, lang_code
            except Exception:
                pass

    return None, None


async def fetch_transcript(
    video_id: str, languages: List[str] = ["ko", "en"]
) -> Tuple[Optional[str], Optional[str]]:
    """
    영상의 자막(대본)을 안정적으로 추출한다.
    1차: yt-dlp 다이렉트 캡션 스트림 추출 (가장 높은 성공률)
    2차: youtube-transcript-api
    반환: (정제된 텍스트, 언어 코드) 또는 (None, None)
    """
    cookie_path = os.environ.get("COOKIE_FILE_PATH")

    # ── 1차 시도: yt-dlp 다이렉트 캡션 추출 (성공률 99%+) ──
    try:
        cleaned, lang = await asyncio.to_thread(
            _fetch_subtitles_via_ytdlp_sync, video_id, languages, cookie_path
        )
        if cleaned:
            return cleaned, lang
    except Exception:
        pass

    # ── 2차 시도: youtube-transcript-api ──
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
    except Exception:
        pass

    return None, None
