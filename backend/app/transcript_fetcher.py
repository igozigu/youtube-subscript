import asyncio
import os
import tempfile
from typing import Tuple, Optional, List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    RequestBlocked,
    IpBlocked,
)
from .text_cleaner import clean_transcript


async def fetch_transcript(
    video_id: str, languages: List[str] = ["ko", "en"]
) -> Tuple[Optional[str], Optional[str]]:
    """
    영상의 자막(대본)을 추출한다.
    1차: youtube-transcript-api → 2차: yt-dlp fallback
    반환: (정제된 텍스트, 언어 코드) 또는 (None, None)
    """
    delay_ms = int(os.environ.get("FETCH_DELAY_MS", "1500"))
    cookie_path = os.environ.get("COOKIE_FILE_PATH")

    # ── 1차 시도: youtube-transcript-api ──
    for attempt in range(3):
        try:
            # 쿠키가 있으면 전달하여 봇 감지 우회
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

    # ── 2차 시도: yt-dlp fallback ──
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_template = os.path.join(tmp_dir, f"{video_id}.%(ext)s")
        cmd = [
            "yt-dlp",
            "--write-auto-subs",
            "--skip-download",
            "--sub-langs", ",".join(languages),
            "--sub-format", "vtt",
            "-o", output_template,
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        # yt-dlp에도 쿠키 전달
        if cookie_path and os.path.exists(cookie_path):
            cmd.insert(1, "--cookies")
            cmd.insert(2, cookie_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=60)
        except (asyncio.TimeoutError, Exception):
            return None, None

        for lang in languages:
            filename = os.path.join(tmp_dir, f"{video_id}.{lang}.vtt")
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                cleaned = clean_transcript(raw_text)
                return cleaned, lang

    return None, None
