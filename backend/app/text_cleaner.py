import re


def clean_transcript(text: str) -> str:
    """
    자막 텍스트를 정제한다.
    - VTT/SRT 헤더 및 메타데이터 제거
    - 타임스탬프 라인 제거
    - HTML 태그 제거
    - [Music], [박수] 등 비텍스트 태그 제거
    - 중복 줄바꿈 정리
    """
    # WEBVTT 헤더 및 Kind/Language 등 메타데이터 라인 제거
    text = re.sub(r"^WEBVTT.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^Kind:.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^Language:.*$", "", text, flags=re.MULTILINE)

    # SRT/VTT 타임스탬프 라인 제거 (00:00:00.000 --> 00:00:05.000)
    text = re.sub(
        r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # SRT 시퀀스 번호 라인 제거 (줄 시작이 숫자만인 라인)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)

    # 인라인 타임스탬프 제거 [00:00] 또는 <00:00:00.000>
    text = re.sub(r"\[?\d{1,2}:\d{2}(?::\d{2})?\]?", "", text)
    text = re.sub(r"<\d{2}:\d{2}:\d{2}[.,]\d{3}>", "", text)

    # HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)

    # [Music], [박수], [웃음] 등 비텍스트 태그 제거
    text = re.sub(r"\[.*?\]", "", text)

    # 앞뒤 공백 제거 후 빈 줄 정리
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    # 연속 중복 라인 제거 (VTT에서 흔한 패턴)
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    return "\n".join(deduped).strip()


def sanitize_filename(name: str) -> str:
    """OS에서 금지된 특수문자를 안전하게 치환한다."""
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    sanitized = re.sub(r"_{2,}", "_", sanitized)
    return sanitized.strip(" .")


def format_timestamp(seconds: float) -> str:
    """초 단위를 HH:MM:SS 또는 MM:SS 형식으로 변환한다."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
