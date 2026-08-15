import os
import re
import asyncio
import yt_dlp
from typing import Tuple, List, Optional
from .models import VideoInfo


def _extract_videos_sync(
    url: str, include_shorts: bool, include_live: bool
) -> Tuple[str, List[VideoInfo]]:
    """
    Python yt_dlp 라이브러리를 직접 호출하여 영상 메타데이터를 수집한다.
    (외부 yt-dlp.exe 프로세스 의존 없음)
    """
    cookie_path = os.environ.get("COOKIE_FILE_PATH")
    ydl_opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception:
            # list 파라미터가 유효하지 않은 watch URL일 경우 fallback
            if "&list=" in url or "?list=" in url:
                clean_url = re.sub(r"[&?]list=[^&]+", "", url)
                info = ydl.extract_info(clean_url, download=False)
            else:
                raise

        if not info:
            return "YouTube Videos", []

        playlist_title = (
            info.get("title")
            or info.get("channel")
            or info.get("uploader")
            or "YouTube Videos"
        )
        videos = []

        # 재생목록 또는 채널인 경우
        if "entries" in info and info["entries"]:
            raw_entries = [e for e in info["entries"] if e]
            for data in raw_entries:
                if not include_live and data.get("is_live"):
                    continue
                duration = data.get("duration")
                if not include_shorts and duration is not None and duration < 60:
                    continue
                videos.append(
                    VideoInfo(
                        video_id=data.get("id", "") or data.get("url", ""),
                        title=data.get("title", ""),
                        upload_date=data.get("upload_date"),
                        duration=duration,
                    )
                )
        else:
            # 단일 영상인 경우
            duration = info.get("duration")
            videos.append(
                VideoInfo(
                    video_id=info.get("id", ""),
                    title=info.get("title", ""),
                    upload_date=info.get("upload_date"),
                    duration=duration,
                )
            )

        return playlist_title, videos


async def list_videos(
    url: str, include_shorts: bool, include_live: bool
) -> Tuple[str, List[VideoInfo]]:
    """
    비동기로 YouTube 영상 목록을 수집한다.
    """
    return await asyncio.to_thread(
        _extract_videos_sync, url, include_shorts, include_live
    )
