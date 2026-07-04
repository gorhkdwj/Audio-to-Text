"""세그먼트 목록을 txt / md / srt 문자열로 변환한다.

포맷 규칙 출처: docs/requirements-contract.md
- txt: "[HH:MM:SS] 텍스트" (타임스탬프 생략 시 문단 단위 순수 텍스트)
- md : 제목 + 메타데이터 표 + 문단 본문 (발화 간격 ≥ 2초 기준 병합)
- srt: 표준 자막. v1은 Whisper 세그먼트를 자막 블록으로 그대로 사용
- 인식 결과가 없으면 본문에 "(인식된 음성 없음)"을 명시 (D-003)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

EMPTY_NOTICE = "(인식된 음성 없음)"
PARAGRAPH_GAP_SECONDS = 2.0  # 이 이상 발화가 끊기면 새 문단


@dataclass
class Segment:
    """인식된 발화 한 토막."""

    start: float  # 시작 시각(초)
    end: float  # 끝 시각(초)
    text: str  # 인식된 텍스트
    speaker: str | None = None  # 화자 라벨("화자 1" 등), 화자 구분 시에만


@dataclass
class TranscriptMeta:
    """md 메타데이터 표에 들어가는 정보."""

    source_name: str  # 원본 파일 이름
    duration: float  # 미디어 길이(초)
    model: str  # 사용한 Whisper 모델
    language: str  # 인식 언어
    created_at: datetime  # 생성 시각


def format_timestamp(seconds: float) -> str:
    """초 → "HH:MM:SS" (txt/md용)."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_srt_timestamp(seconds: float) -> str:
    """초 → "HH:MM:SS,mmm" (SRT 규격, 밀리초 포함)."""
    ms_total = int(round(seconds * 1000))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def merge_paragraphs(segments: list[Segment]) -> list[list[Segment]]:
    """발화 간격(≥2초) 또는 화자가 바뀌는 지점에서 문단을 나눈다."""
    paragraphs: list[list[Segment]] = []
    current: list[Segment] = []
    for seg in segments:
        if current and (
            seg.start - current[-1].end >= PARAGRAPH_GAP_SECONDS
            or seg.speaker != current[-1].speaker
        ):
            paragraphs.append(current)
            current = []
        current.append(seg)
    if current:
        paragraphs.append(current)
    return paragraphs


def to_txt(segments: list[Segment], include_timestamps: bool = True) -> str:
    """txt: 기본은 세그먼트마다 "[HH:MM:SS] 텍스트" 한 줄.

    include_timestamps=False면 문단 단위 순수 텍스트.
    화자 구분 시 "화자 1: " 접두.
    """
    if not segments:
        return EMPTY_NOTICE + "\n"
    if include_timestamps:
        lines = []
        for seg in segments:
            prefix = f"[{format_timestamp(seg.start)}]"
            body = seg.text.strip()
            if seg.speaker:
                body = f"{seg.speaker}: {body}"
            lines.append(f"{prefix} {body}")
        return "\n".join(lines) + "\n"
    blocks = []
    for para in merge_paragraphs(segments):
        text = " ".join(s.text.strip() for s in para)
        if para[0].speaker:
            text = f"{para[0].speaker}: {text}"
        blocks.append(text)
    return "\n\n".join(blocks) + "\n"


def to_md(
    segments: list[Segment],
    meta: TranscriptMeta,
    include_timestamps: bool = True,
) -> str:
    """md: 제목(파일명) + 메타데이터 표 + 문단 본문.

    문단은 merge_paragraphs 기준으로 병합, 화자는 "**화자 1:**" 굵게.
    """
    lines = [
        f"# {meta.source_name}",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 원본 | {meta.source_name} |",
        f"| 길이 | {format_timestamp(meta.duration)} |",
        f"| 모델 | {meta.model} |",
        f"| 언어 | {meta.language} |",
        f"| 생성일 | {meta.created_at.strftime('%Y-%m-%d %H:%M:%S')} |",
        "",
    ]
    if not segments:
        lines.append(EMPTY_NOTICE)
        return "\n".join(lines) + "\n"
    for para in merge_paragraphs(segments):
        parts = []
        if include_timestamps:
            parts.append(f"[{format_timestamp(para[0].start)}]")
        if para[0].speaker:
            parts.append(f"**{para[0].speaker}:**")
        parts.append(" ".join(s.text.strip() for s in para))
        lines.append(" ".join(parts))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_srt(segments: list[Segment]) -> str:
    """srt: 표준 자막 형식. 화자 구분 시 텍스트 앞에 "화자 1: " 접두.

    인식 결과가 없으면 0~1초짜리 안내 자막 하나를 넣는다(빈 파일 방지).
    """
    if not segments:
        blocks = [f"1\n00:00:00,000 --> 00:00:01,000\n{EMPTY_NOTICE}"]
    else:
        blocks = []
        for index, seg in enumerate(segments, start=1):
            text = seg.text.strip()
            if seg.speaker:
                text = f"{seg.speaker}: {text}"
            blocks.append(
                f"{index}\n"
                f"{format_srt_timestamp(seg.start)} --> {format_srt_timestamp(seg.end)}\n"
                f"{text}"
            )
    return "\n\n".join(blocks) + "\n"
