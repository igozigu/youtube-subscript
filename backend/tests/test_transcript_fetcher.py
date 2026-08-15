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
    """정상 자막이 있는 경우"""
    mock_api = MagicMock()
    mock_api.fetch.return_value = [MockSnippet("Hello world"), MockSnippet("Test")]

    with patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api):
        text, lang = await fetch_transcript("test_id", ["en"])
        assert text is not None
        assert "Hello world" in text
        assert lang == "en"


@pytest.mark.asyncio
async def test_auto_generated_subtitles():
    """자동 생성 자막만 있는 경우 (정상 추출)"""
    mock_api = MagicMock()
    mock_api.fetch.return_value = [MockSnippet("자동 생성 자막입니다")]

    with patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api):
        text, lang = await fetch_transcript("auto_sub_id", ["ko", "en"])
        assert text is not None
        assert "자동 생성 자막입니다" in text


@pytest.mark.asyncio
async def test_no_subtitles():
    """자막이 전혀 없는 경우 → (None, None) 반환"""
    from youtube_transcript_api._errors import TranscriptsDisabled

    mock_api = MagicMock()
    mock_api.fetch.side_effect = TranscriptsDisabled("test_id")

    with (
        patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api),
        patch("app.transcript_fetcher._fetch_ytdlp_subs_sync", return_value=(None, None)),
    ):
        text, lang = await fetch_transcript("no_subs_id", ["en"])
        assert text is None
        assert lang is None


@pytest.mark.asyncio
async def test_rate_limit_retry():
    """RequestBlocked 발생 시 재시도 로직 확인"""
    from youtube_transcript_api._errors import RequestBlocked

    mock_api = MagicMock()
    mock_api.fetch.side_effect = RequestBlocked("test_id")

    with (
        patch("app.transcript_fetcher.YouTubeTranscriptApi", return_value=mock_api),
        patch("app.transcript_fetcher._fetch_ytdlp_subs_sync", return_value=(None, None)),
        patch("app.transcript_fetcher.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        text, lang = await fetch_transcript("rate_limit_id", ["en"])
        # RequestBlocked → 3번 재시도, 각각 sleep 호출
        assert mock_sleep.call_count >= 3
        assert text is None
