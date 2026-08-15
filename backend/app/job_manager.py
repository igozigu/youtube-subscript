import uuid
import asyncio
import os
import aiofiles
from fastapi import WebSocket
from typing import Dict, Optional, List
from .models import JobCreateRequest, JobStatus, VideoJobStatus, VideoStatus, VideoInfo
from .transcript_fetcher import fetch_transcript
from .text_cleaner import sanitize_filename

# 인메모리 작업 저장소
jobs: Dict[str, JobStatus] = {}
# 작업별 메타데이터 (소스 타이틀, 영상 정보)
job_metadata: Dict[str, dict] = {}


def _make_filename(video_id: str, title: str, upload_date: Optional[str]) -> str:
    """
    명세 형식의 파일명을 생성한다: {업로드일}_{영상제목}.txt
    예: 20240101_영상제목.txt
    """
    safe_title = sanitize_filename(title) or video_id
    if upload_date:
        return f"{upload_date}_{safe_title}.txt"
    return f"{safe_title}.txt"


def create_job(request: JobCreateRequest, video_info_map: Optional[Dict[str, VideoInfo]] = None) -> str:
    """새 추출 작업을 생성하고 job_id를 반환한다."""
    job_id = str(uuid.uuid4())

    results = []
    for vid in request.video_ids:
        title = f"Video {vid}"
        upload_date = None
        if video_info_map and vid in video_info_map:
            title = video_info_map[vid].title
            upload_date = video_info_map[vid].upload_date

        results.append(
            VideoJobStatus(
                video_id=vid,
                title=title,
                status=VideoStatus.PENDING,
                upload_date=upload_date,
            )
        )

    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="PROCESSING",
        total=len(request.video_ids),
        completed=0,
        results=results,
    )
    job_metadata[job_id] = {
        "source_title": request.source_title,
        "video_info_map": video_info_map or {},
    }
    return job_id


def get_job(job_id: str) -> Optional[JobStatus]:
    """작업 상태를 조회한다."""
    return jobs.get(job_id)


def get_job_source_title(job_id: str) -> str:
    """작업의 소스 타이틀을 반환한다."""
    meta = job_metadata.get(job_id, {})
    return meta.get("source_title", "export")


async def process_job(
    job_id: str,
    request: JobCreateRequest,
    websocket_connections: Dict[str, WebSocket],
):
    """선택된 영상들의 대본을 순차적으로 추출한다."""
    job = jobs[job_id]
    meta = job_metadata.get(job_id, {})
    video_info_map: Dict[str, VideoInfo] = meta.get("video_info_map", {})

    job_dir = os.path.join(
        os.environ.get("OUTPUT_DIR", "data/output"), job_id
    )
    os.makedirs(job_dir, exist_ok=True)

    for idx, vid_id in enumerate(request.video_ids):
        res = job.results[idx]
        res.status = VideoStatus.PROCESSING
        await _notify_ws(job_id, websocket_connections)

        try:
            transcript, lang = await fetch_transcript(vid_id, request.languages)

            if transcript:
                res.status = VideoStatus.COMPLETED
                res.language = lang

                upload_date = res.upload_date
                if not upload_date and video_info_map and vid_id in video_info_map:
                    upload_date = video_info_map[vid_id].upload_date
                    res.upload_date = upload_date

                filename = _make_filename(vid_id, res.title, upload_date)
                filepath = os.path.join(job_dir, filename)

                # 동일 파일명 충돌 방지
                if os.path.exists(filepath):
                    base, ext = os.path.splitext(filename)
                    filename = f"{base}_{vid_id}{ext}"
                    filepath = os.path.join(job_dir, filename)

                res.file_name = filename

                async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                    await f.write(transcript)

                res.error = None
            else:
                res.status = VideoStatus.NO_SUBTITLE

        except Exception as e:
            res.status = VideoStatus.FAILED
            res.error = str(e)

        job.completed += 1
        await _notify_ws(job_id, websocket_connections)

    job.status = "COMPLETED"
    await _notify_ws(job_id, websocket_connections)


async def _notify_ws(
    job_id: str, ws_dict: Dict[str, WebSocket]
) -> None:
    """WebSocket으로 작업 진행 상황을 전송한다."""
    if job_id in ws_dict:
        ws = ws_dict[job_id]
        job = jobs[job_id]
        try:
            await ws.send_json(job.model_dump())
        except Exception:
            ws_dict.pop(job_id, None)
