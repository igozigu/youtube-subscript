import uuid
import asyncio
import os
import aiofiles
from fastapi import WebSocket
from typing import Dict, Optional
from .models import JobCreateRequest, JobStatus, VideoJobStatus, VideoStatus
from .transcript_fetcher import fetch_transcript

# 인메모리 작업 저장소
jobs: Dict[str, JobStatus] = {}
# 작업별 소스 타이틀 저장 (다운로드 시 사용)
job_source_titles: Dict[str, str] = {}


def create_job(request: JobCreateRequest) -> str:
    """새 추출 작업을 생성하고 job_id를 반환한다."""
    job_id = str(uuid.uuid4())
    results = [
        VideoJobStatus(
            video_id=vid,
            title=f"Video {vid}",
            status=VideoStatus.PENDING,
        )
        for vid in request.video_ids
    ]
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="PROCESSING",
        total=len(request.video_ids),
        completed=0,
        results=results,
    )
    job_source_titles[job_id] = request.source_title
    return job_id


def get_job(job_id: str) -> Optional[JobStatus]:
    """작업 상태를 조회한다."""
    return jobs.get(job_id)


def get_job_source_title(job_id: str) -> str:
    """작업의 소스 타이틀을 반환한다."""
    return job_source_titles.get(job_id, "export")


async def process_job(
    job_id: str,
    request: JobCreateRequest,
    websocket_connections: Dict[str, WebSocket],
):
    """선택된 영상들의 대본을 순차적으로 추출한다."""
    job = jobs[job_id]
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
                filepath = os.path.join(job_dir, f"{vid_id}.txt")
                async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                    await f.write(transcript)
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
            # 연결이 끊긴 경우 무시
            ws_dict.pop(job_id, None)
