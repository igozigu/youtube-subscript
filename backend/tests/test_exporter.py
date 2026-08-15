import pytest
import os
import zipfile
import json
from app.exporter import export_zip, export_markdown, export_json
from app.models import VideoJobStatus, VideoStatus
from app.text_cleaner import sanitize_filename


@pytest.fixture
def mock_results(tmp_path):
    """테스트용 결과 데이터 생성"""
    job_id = "test_job"
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True)

    # 완료된 영상의 txt 파일 생성
    with open(job_dir / "vid1.txt", "w", encoding="utf-8") as f:
        f.write("안녕하세요. 테스트 대본입니다.")

    results = [
        VideoJobStatus(
            video_id="vid1",
            title="테스트 영상 제목",
            status=VideoStatus.COMPLETED,
        ),
        VideoJobStatus(
            video_id="vid2",
            title="자막 없는 영상",
            status=VideoStatus.NO_SUBTITLE,
        ),
        VideoJobStatus(
            video_id="vid3",
            title="실패한 영상",
            status=VideoStatus.FAILED,
            error="Connection error",
        ),
    ]
    return job_id, results, str(tmp_path)


@pytest.mark.asyncio
async def test_export_zip(mock_results, monkeypatch):
    """ZIP 내보내기: 완료된 영상만 포함"""
    job_id, results, tmp_path = mock_results
    monkeypatch.setattr("app.exporter.OUTPUT_DIR", tmp_path)

    zip_path = await export_zip(job_id, results, "테스트 모음")
    assert os.path.exists(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        files = zf.namelist()
        assert len(files) == 1
        assert "테스트 영상 제목.txt" in files


@pytest.mark.asyncio
async def test_export_markdown(mock_results, monkeypatch):
    """Markdown 내보내기: 헤더와 URL 포함 확인"""
    job_id, results, tmp_path = mock_results
    monkeypatch.setattr("app.exporter.OUTPUT_DIR", tmp_path)

    md_path = await export_markdown(job_id, results, "테스트 모음")
    assert os.path.exists(md_path)

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# 테스트 모음" in content
    assert "## 테스트 영상 제목" in content
    assert "안녕하세요. 테스트 대본입니다." in content
    assert "youtube.com/watch?v=vid1" in content
    assert "*자막 없음*" in content


@pytest.mark.asyncio
async def test_export_json(mock_results, monkeypatch):
    """JSON 내보내기: 구조 및 내용 확인"""
    job_id, results, tmp_path = mock_results
    monkeypatch.setattr("app.exporter.OUTPUT_DIR", tmp_path)

    json_path = await export_json(job_id, results, "테스트 모음")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["source_title"] == "테스트 모음"
    assert len(data["videos"]) == 3

    completed = [v for v in data["videos"] if v["transcript"] is not None]
    assert len(completed) == 1
    assert completed[0]["title"] == "테스트 영상 제목"


def test_sanitize_filename():
    """파일명 특수문자 치환 확인"""
    assert sanitize_filename('My <video> : test?') == "My _video_ _ test_"
    assert sanitize_filename('일반적인_파일명') == "일반적인_파일명"
    assert sanitize_filename('file/with\\slashes') == "file_with_slashes"


def test_sanitize_filename_empty():
    """빈 문자열 치환"""
    assert sanitize_filename("") == ""
