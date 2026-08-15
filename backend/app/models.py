from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


class ResolveRequest(BaseModel):
    url: str
    include_shorts: bool = False
    include_live: bool = False


class VideoInfo(BaseModel):
    video_id: str
    title: str
    upload_date: Optional[str] = None
    duration: Optional[int] = None


class ResolveResponse(BaseModel):
    url_type: str
    title: str
    video_count: int
    videos: List[VideoInfo]


class JobCreateRequest(BaseModel):
    video_ids: List[str]
    source_url: str
    source_title: str
    languages: List[str] = ["ko", "en"]
    output_format: str = "zip"


class VideoStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    NO_SUBTITLE = "NO_SUBTITLE"
    FAILED = "FAILED"


class VideoJobStatus(BaseModel):
    video_id: str
    title: str
    status: VideoStatus
    upload_date: Optional[str] = None
    language: Optional[str] = None
    file_name: Optional[str] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int
    results: List[VideoJobStatus]


class JobCreateResponse(BaseModel):
    job_id: str
