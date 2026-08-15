import re
from urllib.parse import urlparse, parse_qs
from typing import Literal, Optional

def normalize_url(url: str) -> str:
    return url.strip()

def extract_playlist_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'list' in qs:
        return qs['list'][0]
    return None

def detect_url_type(url: str) -> Literal['channel', 'playlist', 'invalid']:
    url = normalize_url(url)
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    
    if not ('youtube.com' in netloc or 'youtu.be' in netloc):
        return 'invalid'
        
    if extract_playlist_id(url):
        return 'playlist'
        
    path = parsed.path
    if path.startswith('/@'):
        return 'channel'
    if path.startswith('/channel/'):
        return 'channel'
    if path.startswith('/c/'):
        return 'channel'
    if path.startswith('/user/'):
        return 'channel'
        
    return 'invalid'
