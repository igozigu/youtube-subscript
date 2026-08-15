import pytest
from app.url_parser import detect_url_type, extract_playlist_id

def test_channel_handle():
    assert detect_url_type("https://www.youtube.com/@Fireship") == "channel"

def test_channel_handle_videos():
    assert detect_url_type("https://www.youtube.com/@Fireship/videos") == "channel"

def test_channel_id():
    assert detect_url_type("https://www.youtube.com/channel/UCxxxxxx") == "channel"

def test_playlist_url():
    assert detect_url_type("https://www.youtube.com/playlist?list=PLxxxxxx") == "playlist"
    assert extract_playlist_id("https://www.youtube.com/playlist?list=PLxxxxxx") == "PLxxxxxx"

def test_watch_with_list():
    assert detect_url_type("https://www.youtube.com/watch?v=xxxx&list=PLxxxxxx") == "playlist"

def test_invalid_url_random_site():
    assert detect_url_type("https://example.com") == "invalid"

def test_invalid_url_empty():
    assert detect_url_type("") == "invalid"

def test_invalid_url_youtube_no_path():
    assert detect_url_type("https://www.youtube.com") == "invalid"

def test_edge_case_query_params():
    assert detect_url_type("https://www.youtube.com/@SomeChannel?feature=shared") == "channel"
