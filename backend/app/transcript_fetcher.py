import asyncio
import os
import tempfile
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


def _fetch_ytdlp_subs_sync(
    video_id: str, languages: List[str], cookie_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """yt_dlp Python API를 통해 자동생성/수동 자막을 직접 수집한다."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_template = os.path.join(tmp_dir, f"{video_id}.%(ext)s")
        ydl_opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "writesubtitles": True,
            "subtitleslangs": languages,
            "subtitlesformat": "vtt",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        if cookie_path and os.path.exists(cookie_path):
            ydl_opts["cookiefile"] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        except Exception:
            return None, None

        for lang in languages:
            filename = os.path.join(tmp_dir, f"{video_id}.{lang}.vtt")
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                cleaned = clean_transcript(raw_text)
                return cleaned, lang

        # 다른 언어 vtt 파일이 다운로드된 경우
        for fname in os.listdir(tmp_dir):
            if fname.endswith(".vtt"):
                with open(os.path.join(tmp_dir, fname), "r", encoding="utf-8") as f:
                    raw_text = f.read()
                cleaned = clean_transcript(raw_text)
                return cleaned, languages[0]

    return None, None


async def fetch_transcript(
    video_id: str, languages: List[str] = ["ko", "en"]
) -> Tuple[Optional[str], Optional[str]]:
    """
    영상의 자막(대본)을 추출한다.
    1차: youtube-transcript-api → 2차: yt-dlp Python API fallback
    반환: (정제된 텍스트, 언어 코드) 또는 (None, None)
    """
    delay_ms = int(os.environ.get("FETCH_DELAY_MS", "1500"))
    cookie_path = os.environ.get("COOKIE_FILE_PATH")

    # ── 1차 시도: youtube-transcript-api ──
    for attempt in range(3):
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

            await asyncio.sleep(delay_ms / 1000.0)

            # 실제 사용된 언어 감지
            detected_lang = languages[0]
            try:
                transcript_list = await asyncio.to_thread(
                    ytt_api.list, video_id
                )
                for t in transcript_list:
                    if t.language_code in languages:
                        detected_lang = t.language_code
                        break
            except Exception:
                pass

            return cleaned, detected_lang

        except (RequestBlocked, IpBlocked):
            wait_time = (2 ** attempt) * (delay_ms / 1000.0)
            await asyncio.sleep(wait_time)
        except (TranscriptsDisabled, NoTranscriptFound):
            break
        except Exception:
            break

    # ── 2차 시도: yt-dlp Python API fallback ──
    try:
        cleaned, lang = await asyncio.to_thread(
            _fetch_ytdlp_subs_sync, video_id, languages, cookie_path
        )
        if cleaned:
            return cleaned, lang
    except Exception:
        pass

    return None, None
