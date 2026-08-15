import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app.transcript_fetcher import fetch_transcript


class MockSnippet:
    """youtube-transcript-api의 FetchedTranscriptSnippet 모사"""
    def __init__(self, text: str):
        self.text = text


@pytest.mark.asyncio
async def test_normal_subtitles():
    """yt-dlp 다이렉트 자막 또는 API를 통한 정상 추출"""
    with patch(
        "app.transcript_fetcher._fetch_subtitles_via_ytdlp_sync",
        return_value=("Hello world\nTest", "en"),
    ):
        text, lang = await fetch_transcript("test_id", ["en"])
        assert text is not None
        assert "Hello world" in text
        assert lang == "en"


@pytest.mark.asyncio
async def test_auto_generated_subtitles():
    """자동 생성 자막 정상 추출"""
    with patch(
        "app.transcript_fetcher._fetch_subtitles_via_ytdlp_sync",
        return_value=("자동 생성 자막입니다", "ko"),
    ):
        text, lang = await fetch_transcript("auto_sub_id", ["ko", "en"])
        assert text is not None
        assert "자동 생성 자막입니다" in text
        assert lang == "ko"


@pytest.mark.asyncio
async def test_no_subtitles():
    """자막이 전혀 없는 경우 → (None, None) 반환"""
    from youtube_transcript_api._errors import TranscriptsDisabled

    mock_api = MagicMock()
    mock_api.fetch.side_effect = TranscriptsDisabled("test_id")

    with (
        patch("app.transcript_fetcher._fetch_subtitles_via_ytdlp_sync", return_value=(None, None)),
        patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api),
    ):
        text, lang = await fetch_transcript("no_subs_id", ["en"])
        assert text is None
        assert lang is None


@pytest.mark.asyncio
async def test_fallback_to_api():
    """1차 yt-dlp 실패 시 2차 youtube-transcript-api fallback"""
    mock_api = MagicMock()
    mock_api.fetch.return_value = [MockSnippet("API Fallback 자막")]

    with (
        patch("app.transcript_fetcher._fetch_subtitles_via_ytdlp_sync", return_value=(None, None)),
        patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api),
    ):
        text, lang = await fetch_transcript("fallback_id", ["ko"])
        assert text is not None
        assert "API Fallback 자막" in text
