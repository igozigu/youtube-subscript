import os
import json
import zipfile
import aiofiles
from typing import List, Optional
from .text_cleaner import sanitize_filename
from .models import VideoJobStatus, VideoStatus

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "data/output")


def _find_txt_path(job_dir: str, res: VideoJobStatus) -> Optional[str]:
    """해당 영상의 텍스트 파일 경로를 찾는다."""
    candidates = []
    if res.file_name:
        candidates.append(os.path.join(job_dir, res.file_name))

    safe_title = sanitize_filename(res.title)
    if res.upload_date:
        candidates.append(os.path.join(job_dir, f"{res.upload_date}_{safe_title}.txt"))
    candidates.append(os.path.join(job_dir, f"{safe_title}.txt"))
    candidates.append(os.path.join(job_dir, f"{res.video_id}.txt"))

    for p in candidates:
        if os.path.exists(p):
            return p
    return None


async def export_zip(
    job_id: str, results: List[VideoJobStatus], source_title: str
) -> str:
    """개별 영상 txt 파일을 ZIP으로 압축한다."""
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    zip_path = os.path.join(job_dir, f"{sanitize_filename(source_title)}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for res in results:
            if res.status == VideoStatus.COMPLETED:
                txt_path = _find_txt_path(job_dir, res)
                if txt_path:
                    safe_title = sanitize_filename(res.title)
                    arcname = res.file_name or (
                        f"{res.upload_date}_{safe_title}.txt"
                        if res.upload_date
                        else f"{safe_title}.txt"
                    )
                    zipf.write(txt_path, arcname)

    return zip_path


async def export_markdown(
    job_id: str, results: List[VideoJobStatus], source_title: str
) -> str:
    """전체 대본을 하나의 Markdown 파일로 합친다."""
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    md_path = os.path.join(job_dir, f"{sanitize_filename(source_title)}.md")

    async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
        await f.write(f"# {source_title}\n\n")
        for res in results:
            video_url = f"https://www.youtube.com/watch?v={res.video_id}"
            await f.write(f"## {res.title}\n\n")
            if res.upload_date:
                await f.write(f"- **업로드일**: {res.upload_date}\n")
            if res.language:
                await f.write(f"- **언어**: {res.language}\n")
            await f.write(f"- **원본 URL**: {video_url}\n\n")

            if res.status == VideoStatus.COMPLETED:
                txt_path = _find_txt_path(job_dir, res)
                if txt_path:
                    async with aiofiles.open(
                        txt_path, "r", encoding="utf-8"
                    ) as tf:
                        content = await tf.read()
                    await f.write(f"{content}\n\n---\n\n")
                else:
                    await f.write("*대본 파일 없음*\n\n---\n\n")
            elif res.status == VideoStatus.NO_SUBTITLE:
                await f.write("*자막 없음*\n\n---\n\n")
            elif res.status == VideoStatus.FAILED:
                await f.write(f"*추출 실패*: {res.error or '알 수 없는 오류'}\n\n---\n\n")

    return md_path


async def export_json(
    job_id: str, results: List[VideoJobStatus], source_title: str
) -> str:
    """JSON 형식으로 내보낸다 (video_id, title, upload_date, transcript, language 포함)."""
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    json_path = os.path.join(
        job_dir, f"{sanitize_filename(source_title)}.json"
    )

    export_data = {
        "source_title": source_title,
        "videos": [],
    }

    for res in results:
        transcript_content = None
        if res.status == VideoStatus.COMPLETED:
            txt_path = _find_txt_path(job_dir, res)
            if txt_path:
                with open(txt_path, "r", encoding="utf-8") as tf:
                    transcript_content = tf.read()

        video_entry = {
            "video_id": res.video_id,
            "title": res.title,
            "upload_date": res.upload_date,
            "language": res.language,
            "status": res.status.value,
            "transcript": transcript_content,
            "url": f"https://www.youtube.com/watch?v={res.video_id}",
        }
        export_data["videos"].append(video_entry)

    async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

    return json_path
