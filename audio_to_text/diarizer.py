"""화자 구분(diarization) — pyannote.audio 래퍼 + 세그먼트-화자 매칭.

선택 기능이라 지연 import를 사용한다: --diarize를 쓰지 않는 사용자는
pyannote/torch가 없어도 프로그램 전체가 정상 동작해야 한다.

준비가 안 된 경우(미설치/토큰 없음) DiarizationUnavailable에 한국어 안내를
담아 던지고, cli는 안내만 출력한 뒤 화자 구분 없이 계속 진행한다(D-003).

주의: 실제 pyannote 호출 경로는 S4에서 검증한다(현재 미검증 범위).
"""

from __future__ import annotations

import os
from pathlib import Path

from .formatters import Segment

DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"

INSTALL_GUIDE = (
    "화자 구분(--diarize)을 사용하려면 추가 준비가 필요합니다:\n"
    "  1) 추가 패키지 설치:  pip install -r requirements-diarize.txt\n"
    "  2) HuggingFace 계정으로 아래 두 모델 페이지에서 이용 약관 동의:\n"
    "     - https://huggingface.co/pyannote/speaker-diarization-3.1\n"
    "     - https://huggingface.co/pyannote/segmentation-3.0\n"
    "  3) HuggingFace 액세스 토큰을 HF_TOKEN 환경변수 또는 --hf-token 옵션으로 전달\n"
    "화자 구분 없이 텍스트 변환은 계속 진행합니다."
)


class DiarizationUnavailable(Exception):
    """화자 구분을 수행할 수 없는 상태(미설치/토큰 없음). 안내 메시지를 담는다."""


def diarize_file(
    media_path: Path,
    hf_token: str | None = None,
    num_speakers: int | None = None,
) -> list[tuple[float, float, str]]:
    """화자 구분을 실행해 (시작초, 끝초, 화자키) turn 목록을 반환한다.

    - pyannote 미설치 또는 토큰 없음 → DiarizationUnavailable (한국어 안내 포함)
    """
    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        raise DiarizationUnavailable("HuggingFace 토큰이 없습니다.\n" + INSTALL_GUIDE)
    try:
        from pyannote.audio import Pipeline  # 지연 import (무거움)
    except ImportError:
        raise DiarizationUnavailable(
            "pyannote.audio가 설치되어 있지 않습니다.\n" + INSTALL_GUIDE
        ) from None

    # huggingface_hub 1.x가 use_auth_token 인자를 제거해(T-003) 인자 대신
    # 환경변수로 토큰을 전달한다 — pyannote 내부의 모든 허브 호출이 자동 인식한다.
    os.environ["HF_TOKEN"] = token
    pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL)

    # GPU가 있으면 파이프라인을 CUDA로 이동 (긴 파일에서 속도 차이가 큼)
    try:
        import torch

        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
    except Exception:
        pass  # GPU 이동 실패 시 CPU로 진행 (기능상 동일)

    kwargs = {}
    if num_speakers:
        kwargs["num_speakers"] = num_speakers
    diarization = pipeline(str(media_path), **kwargs)

    turns = [
        (float(turn.start), float(turn.end), str(speaker))
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
    return turns


def assign_speakers(
    segments: list[Segment],
    turns: list[tuple[float, float, str]],
) -> None:
    """각 세그먼트에 시간 겹침이 가장 큰 화자를 할당한다(v1: 세그먼트 단위).

    화자 번호는 첫 등장 시각 순서로 "화자 1", "화자 2", … (D-003)
    겹치는 화자가 없는 세그먼트는 라벨 없이 둔다.
    """
    if not turns:
        return

    # 화자 키 → 첫 등장 시각 → "화자 N" 라벨
    first_seen: dict[str, float] = {}
    for start, _end, key in sorted(turns, key=lambda t: t[0]):
        first_seen.setdefault(key, start)
    label_by_key = {
        key: f"화자 {i}"
        for i, key in enumerate(sorted(first_seen, key=first_seen.__getitem__), start=1)
    }

    for seg in segments:
        best_key: str | None = None
        best_overlap = 0.0
        for start, end, key in turns:
            overlap = min(seg.end, end) - max(seg.start, start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_key = key
        if best_key is not None:
            seg.speaker = label_by_key[best_key]
