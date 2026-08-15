import asyncio
import os
import re
import json
import random
import http.cookiejar
import urllib.parse
from typing import Tuple, Optional, List

import requests
import yt_dlp
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


def validate_cookie_file(path: Optional[str]) -> Tuple[bool, str]:
    """Netscape 형식의 cookies.txt 파일을 검증하고 상태 메시지를 반환한다."""
    if not path or not os.path.exists(path):
        return False, "파일이 존재하지 않습니다."
    try:
        jar = http.cookiejar.MozillaCookieJar()
        jar.load(path, ignore_discard=True, ignore_expires=True)
        yt_cookies = [c.name for c in jar if "youtube.com" in c.domain or "google.com" in c.domain]
        if not yt_cookies:
            return False, "YouTube 관련 쿠키가 없습니다. youtube.com에서 추출해주세요."
        has_auth = any(n in yt_cookies for n in ["SID", "LOGIN_INFO", "SSID", "__Secure-3PSID", "VISITOR_INFO1_LIVE"])
        if has_auth:
            return True, f"✅ 유효한 YouTube 인증 쿠키 확인됨 ({len(yt_cookies)}개 항목)"
        return True, f"YouTube 기본 쿠키 확인됨 ({len(yt_cookies)}개 항목)"
    except Exception as e:
        return False, f"쿠키 파일 형식 오류: {e}"


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


def _fetch_from_web_html(
    video_id: str, languages: List[str], cookie_jar: Optional[http.cookiejar.MozillaCookieJar]
) -> Tuple[Optional[str], Optional[str]]:
    """웹페이지 HTML의 ytInitialPlayerResponse로부터 자막 트랙을 파싱하여 다운로드한다."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=headers,
            cookies=cookie_jar,
            timeout=10,
        )
        if r.status_code != 200:
            return None, None

        html = r.text
        match = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?})\s*;\s*(?:var\s+meta|<\/script|\n)", html)
        if not match:
            return None, None

        player_data = json.loads(match.group(1))
        captions = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
        tracks = captions.get("captionTracks", [])
        if not tracks:
            return None, None

        # 1. 요청 언어 우선 탐색
        for target_lang in languages:
            for t in tracks:
                if t.get("languageCode") == target_lang or t.get("vssId", "").endswith(f".{target_lang}"):
                    base_url = t.get("baseUrl")
                    sub_r = requests.get(base_url, headers=headers, cookies=cookie_jar, timeout=10)
                    if sub_r.status_code == 200 and "<html>" not in sub_r.text and len(sub_r.text) > 50:
                        cleaned = clean_transcript(sub_r.text)
                        if cleaned:
                            return cleaned, target_lang

        # 2. 첫 번째 사용 가능 자막 fallback
        first_track = tracks[0]
        base_url = first_track.get("baseUrl")
        lang_code = first_track.get("languageCode", languages[0])
        sub_r = requests.get(base_url, headers=headers, cookies=cookie_jar, timeout=10)
        if sub_r.status_code == 200 and "<html>" not in sub_r.text and len(sub_r.text) > 50:
            cleaned = clean_transcript(sub_r.text)
            if cleaned:
                return cleaned, lang_code

    except Exception:
        pass

    return None, None


def _fetch_subtitles_via_ytdlp_sync(
    video_id: str, languages: List[str], cookie_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    yt-dlp의 메타데이터에서 직접 자막 스트림 URL(수동/자동 자막)을 추출하여 다운로드한다.
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
        if "429" in err_str or "too many requests" in err_str:
            raise YoutubeBlockedError("YouTube 봇 감지(429): 브라우저 쿠키(cookies.txt) 등록이 필요합니다.")
        return None, None

    if not info:
        return None, None

    manual_subs = info.get("subtitles", {}) or {}
    auto_subs = info.get("automatic_captions", {}) or {}

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
        url = next(
            (f["url"] for f in formats_list if f.get("ext") == "vtt"),
            formats_list[0]["url"],
        )
        try:
            r = requests.get(url, headers=headers, cookies=cookie_jar, timeout=12)
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

    # 1. 요청 언어 수동 자막 탐색
    for target_lang in languages:
        if target_lang in manual_subs and manual_subs[target_lang]:
            res_text = _download_track(manual_subs[target_lang])
            if res_text:
                return res_text, target_lang

    # 2. 요청 언어 자동 자막 탐색
    for target_lang in languages:
        if target_lang in auto_subs and auto_subs[target_lang]:
            res_text = _download_track(auto_subs[target_lang])
            if res_text:
                return res_text, target_lang

    # 3. 기타 언어 fallback
    all_subs = {**manual_subs, **auto_subs}
    for lang_code, formats in all_subs.items():
        if formats:
            res_text = _download_track(formats)
            if res_text:
                return res_text, lang_code

    if has_429_block and not cookie_path:
        raise YoutubeBlockedError("YouTube 봇 감지(429): 브라우저 쿠키(cookies.txt) 등록이 필요합니다.")

    return None, None


async def fetch_transcript(
    video_id: str, languages: List[str] = ["ko", "en"]
) -> Tuple[Optional[str], Optional[str]]:
    """
    영상의 자막(대본)을 다단계 파이프라인으로 추출한다.
    - Tier 1: yt-dlp 다이렉트 캡션 추출
    - Tier 2: 웹 HTML ytInitialPlayerResponse 추출
    - Tier 3: youtube-transcript-api
    """
    cookie_path = os.environ.get("COOKIE_FILE_PATH")
    cookie_jar = _load_cookie_jar(cookie_path)

    # ── Tier 1: yt-dlp 다이렉트 캡션 추출 ──
    try:
        cleaned, lang = await asyncio.to_thread(
            _fetch_subtitles_via_ytdlp_sync, video_id, languages, cookie_path
        )
        if cleaned:
            return cleaned, lang
    except YoutubeBlockedError:
        pass
    except Exception:
        pass

    # ── Tier 2: 웹 HTML 플레이어 응답 추출 ──
    try:
        cleaned, lang = await asyncio.to_thread(
            _fetch_from_web_html, video_id, languages, cookie_jar
        )
        if cleaned:
            return cleaned, lang
    except Exception:
        pass

    # ── Tier 3: youtube-transcript-api ──
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
