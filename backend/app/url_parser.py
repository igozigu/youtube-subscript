import re
from urllib.parse import urlparse, parse_qs
from typing import Literal, Optional


def normalize_url(url: str) -> str:
    return url.strip()


def extract_playlist_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "list" in qs:
        return qs["list"][0]
    return None


def detect_url_type(url: str) -> Literal["channel", "playlist", "video", "invalid"]:
    """
    YouTube URL 형태를 분석하여 'channel', 'playlist', 'video', 'invalid' 중 하나를 반환한다.
    """
    url = normalize_url(url)
    if not url:
        return "invalid"

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    if not ("youtube.com" in netloc or "youtu.be" in netloc):
        return "invalid"

    # 재생목록 파라미터가 포함된 경우
    if extract_playlist_id(url):
        return "playlist"

    path = parsed.path
    if (
        path.startswith("/@")
        or path.startswith("/channel/")
        or path.startswith("/c/")
        or path.startswith("/user/")
    ):
        return "channel"

    # 단일 영상 또는 쇼츠
    if (
        path.startswith("/watch")
        or path.startswith("/shorts/")
        or "youtu.be" in netloc
        or path.startswith("/live/")
    ):
        return "video"

    return "invalid"
