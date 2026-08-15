import os
import json
import zipfile
import aiofiles
from typing import List
from .text_cleaner import sanitize_filename
from .models import VideoJobStatus, VideoStatus

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "data/output")


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
                txt_path = os.path.join(job_dir, f"{res.video_id}.txt")
                if os.path.exists(txt_path):
                    arcname = f"{sanitize_filename(res.title)}.txt"
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
            if res.status == VideoStatus.COMPLETED:
                txt_path = os.path.join(job_dir, f"{res.video_id}.txt")
                if os.path.exists(txt_path):
                    async with aiofiles.open(
                        txt_path, "r", encoding="utf-8"
                    ) as tf:
                        content = await tf.read()
                    video_url = f"https://www.youtube.com/watch?v={res.video_id}"
                    await f.write(f"## {res.title}\n\n")
                    await f.write(f"> 원본: {video_url}\n\n")
                    await f.write(f"{content}\n\n---\n\n")
            elif res.status == VideoStatus.NO_SUBTITLE:
                await f.write(f"## {res.title}\n\n")
                await f.write("*자막 없음*\n\n---\n\n")

    return md_path


async def export_json(
    job_id: str, results: List[VideoJobStatus], source_title: str
) -> str:
    """JSON 형식으로 내보낸다."""
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
        video_entry = {
            "video_id": res.video_id,
            "title": res.title,
            "status": res.status.value,
            "transcript": None,
            "url": f"https://www.youtube.com/watch?v={res.video_id}",
        }
        if res.status == VideoStatus.COMPLETED:
            txt_path = os.path.join(job_dir, f"{res.video_id}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as tf:
                    video_entry["transcript"] = tf.read()
        export_data["videos"].append(video_entry)

    async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

    return json_path
