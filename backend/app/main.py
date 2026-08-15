from fastapi import (
    FastAPI,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict
import os

from .models import (
    ResolveRequest,
    ResolveResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobStatus,
)
from .url_parser import detect_url_type
from .video_lister import list_videos
from .job_manager import (
    create_job,
    get_job,
    get_job_source_title,
    process_job,
)
from .exporter import export_zip, export_markdown, export_json

app = FastAPI(
    title="YouTube Transcript Extractor",
    description="YouTube 채널/재생목록 대본 추출 API",
    version="1.0.0",
)

# CORS 설정 (개발 환경: 모든 오리진 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 연결 관리
ws_connections: Dict[str, WebSocket] = {}


@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok"}


@app.post("/api/resolve", response_model=ResolveResponse)
async def resolve_url(req: ResolveRequest):
    """URL을 분석하여 영상 목록을 반환한다."""
    url_type = detect_url_type(req.url)
    if url_type == "invalid":
        raise HTTPException(
            status_code=400,
            detail="유효하지 않은 YouTube URL입니다. 채널 또는 재생목록 URL을 입력해주세요.",
        )

    try:
        title, videos = await list_videos(
            req.url, req.include_shorts, req.include_live
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"영상 목록을 가져오는 중 오류가 발생했습니다: {str(e)}",
        )

    return ResolveResponse(
        url_type=url_type,
        title=title,
        video_count=len(videos),
        videos=videos,
    )


@app.post("/api/jobs", response_model=JobCreateResponse)
async def api_create_job(
    req: JobCreateRequest, background_tasks: BackgroundTasks
):
    """대본 추출 작업을 생성한다."""
    if not req.video_ids:
        raise HTTPException(
            status_code=400, detail="추출할 영상을 선택해주세요."
        )

    job_id = create_job(req)
    background_tasks.add_task(process_job, job_id, req, ws_connections)
    return JobCreateResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def api_get_job(job_id: str):
    """작업 상태를 조회한다."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job


@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """실시간 진행률 WebSocket 엔드포인트"""
    await websocket.accept()
    ws_connections[job_id] = websocket
    try:
        while True:
            # 클라이언트로부터의 메시지를 대기 (연결 유지)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.pop(job_id, None)


@app.get("/api/jobs/{job_id}/download")
async def download_job_results(job_id: str, format: str = "zip"):
    """완료된 작업의 결과를 다운로드한다."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=400, detail="작업이 아직 완료되지 않았습니다."
        )

    source_title = get_job_source_title(job_id)

    if format == "zip":
        path = await export_zip(job_id, job.results, source_title)
        media_type = "application/zip"
        filename = f"{source_title}.zip"
    elif format == "md":
        path = await export_markdown(job_id, job.results, source_title)
        media_type = "text/markdown"
        filename = f"{source_title}.md"
    elif format == "json":
        path = await export_json(job_id, job.results, source_title)
        media_type = "application/json"
        filename = f"{source_title}.json"
    else:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 형식입니다. zip, md, json 중 선택해주세요.",
        )

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404, detail="결과 파일을 찾을 수 없습니다."
        )

    return FileResponse(
        path, media_type=media_type, filename=filename
    )
