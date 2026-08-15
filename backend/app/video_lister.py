import asyncio
import json
import logging
from typing import Tuple, List
from .models import VideoInfo

async def list_videos(url: str, include_shorts: bool, include_live: bool) -> Tuple[str, List[VideoInfo]]:
    cmd = [
        'yt-dlp',
        '--flat-playlist',
        '--dump-json',
        '--ignore-errors',
        '--no-warnings',
        url
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    videos = []
    playlist_title = "Unknown Title"
    
    for line in stdout.decode('utf-8').splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            
            if not include_live and data.get('is_live'):
                continue
                
            duration = data.get('duration')
            if not include_shorts and duration is not None and duration < 60:
                continue
                
            if playlist_title == "Unknown Title":
                playlist_title = data.get('playlist_title') or data.get('channel') or "Unknown Title"
                
            videos.append(VideoInfo(
                video_id=data.get('id', ''),
                title=data.get('title', ''),
                upload_date=data.get('upload_date'),
                duration=duration
            ))
        except json.JSONDecodeError:
            continue
            
    return playlist_title, videos
