"""faster-whisper 래퍼 (모델 로드, GPU DLL 처리, 진행률).

- Windows에서 pip 휠(nvidia-cublas-cu12, nvidia-cudnn-cu12)의 DLL 폴더를
  로더 경로에 등록해 ctranslate2가 CUDA 12 / cuDNN 9를 찾을 수 있게 한다.
- device=auto: CUDA 가능하면 cuda(float16), 아니면 cpu(int8).
- model=auto: cuda면 large-v3, cpu면 medium. (docs/requirements-contract.md)
- GPU 로드 실패 시 한국어 안내와 함께 CPU(int8)로 자동 폴백한다.
"""

from __future__ import annotations

import os
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from .formatters import Segment

AUTO_MODEL_CUDA = "large-v3"
AUTO_MODEL_CPU = "medium"

_dll_dirs_registered = False


def _register_cuda_dll_dirs() -> None:
    """pip으로 설치한 NVIDIA 휠의 DLL 폴더를 Windows 로더 경로에 등록한다.

    os.add_dll_directory()만으로는 부족하다: ctranslate2가 추론 시점에 일반
    LoadLibrary("cublas64_12.dll") 호출로 DLL을 찾는데, 이 검색은 add_dll_directory
    등록 폴더를 보지 않고 PATH를 본다. 그래서 둘 다 등록한다. (T-001)

    Windows가 아니거나 휠이 없으면 조용히 넘어간다(무해).
    """
    global _dll_dirs_registered
    if _dll_dirs_registered or sys.platform != "win32":
        return
    _dll_dirs_registered = True
    purelib = Path(sysconfig.get_paths()["purelib"])
    dll_dirs = [
        dll_dir
        for sub in ("bin", "lib")
        for dll_dir in purelib.glob(f"nvidia/*/{sub}")
        if dll_dir.is_dir()
    ]
    for dll_dir in dll_dirs:
        os.add_dll_directory(str(dll_dir))
    if dll_dirs:
        os.environ["PATH"] = (
            os.pathsep.join(str(d) for d in dll_dirs) + os.pathsep + os.environ.get("PATH", "")
        )


def resolve_device(requested: str) -> tuple[str, str, str | None]:
    """요청한 장치(auto/cuda/cpu)를 실제 (device, compute_type)로 확정한다.

    반환: (device, compute_type, 안내 사유 또는 None)
    안내 사유는 "cuda를 원했지만 cpu로 폴백"처럼 사용자에게 알릴 내용.
    """
    if requested == "cpu":
        return "cpu", "int8", None

    _register_cuda_dll_dirs()
    reason: str | None = None
    try:
        import ctranslate2

        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count == 0:
            reason = "CUDA 장치를 찾지 못했습니다."
    except Exception as exc:  # DLL 로드 실패 포함
        cuda_count = 0
        reason = f"CUDA 확인 중 오류: {exc}"

    if cuda_count > 0:
        return "cuda", "float16", None
    return "cpu", "int8", reason


@dataclass
class LoadedModel:
    """로드된 Whisper 모델과 실제 사용 설정."""

    model: object  # faster_whisper.WhisperModel
    model_name: str  # 실제 로드한 모델 이름 (auto 해석 결과)
    requested_name: str  # 사용자가 요청한 이름 (auto 포함) — 폴백 시 재해석용
    device: str
    compute_type: str


def load_model(model_name: str = "auto", device: str = "auto") -> tuple[LoadedModel, list[str]]:
    """Whisper 모델을 로드한다. GPU 실패 시 CPU(int8)로 자동 폴백.

    반환: (LoadedModel, 사용자에게 보여줄 안내 메시지 목록)
    """
    messages: list[str] = []
    resolved_device, compute_type, reason = resolve_device(device)
    if reason:
        messages.append(f"GPU를 사용할 수 없어 CPU(int8)로 진행합니다. ({reason})")

    name = model_name
    if name == "auto":
        name = AUTO_MODEL_CUDA if resolved_device == "cuda" else AUTO_MODEL_CPU

    from faster_whisper import WhisperModel  # 지연 import (테스트 편의)

    try:
        model = WhisperModel(name, device=resolved_device, compute_type=compute_type)
    except Exception as exc:
        if resolved_device != "cuda":
            raise
        # GPU 로드 실패 → CPU 폴백 (PLAN.md GPU 리스크 대응)
        messages.append(
            f"GPU 모델 로드에 실패해 CPU(int8)로 폴백합니다: {exc}\n"
            "  (cuDNN 9 / cuBLAS DLL 문제일 수 있습니다. requirements.txt의 "
            "nvidia-cudnn-cu12, nvidia-cublas-cu12 설치를 확인하십시오.)"
        )
        resolved_device, compute_type = "cpu", "int8"
        if model_name == "auto":
            name = AUTO_MODEL_CPU
        model = WhisperModel(name, device=resolved_device, compute_type=compute_type)

    loaded = LoadedModel(
        model=model,
        model_name=name,
        requested_name=model_name,
        device=resolved_device,
        compute_type=compute_type,
    )
    return loaded, messages


def transcribe_file(
    loaded: LoadedModel,
    media_path: Path,
    language: str = "ko",
    show_progress: bool = True,
) -> tuple[list[Segment], float, str]:
    """미디어 파일 하나를 인식한다.

    반환: (세그먼트 목록, 미디어 길이(초), 감지된 언어 코드)
    - 동영상도 같은 경로로 처리한다(faster-whisper 내장 PyAV가 디코딩).
    - vad_filter=True로 무음 구간을 걸러낸다.
    """
    lang = None if language == "auto" else language
    segments_iter, info = loaded.model.transcribe(
        str(media_path),
        language=lang,
        vad_filter=True,
    )
    duration = float(info.duration or 0.0)

    segments: list[Segment] = []
    bar = tqdm(
        total=round(duration, 2),
        unit="s",
        desc=media_path.name,
        leave=False,
        disable=not show_progress,
    )
    for seg in segments_iter:
        segments.append(Segment(start=seg.start, end=seg.end, text=seg.text))
        bar.n = min(round(seg.end, 2), bar.total or seg.end)
        bar.refresh()
    if bar.total:
        bar.n = bar.total
        bar.refresh()
    bar.close()

    return segments, duration, info.language or (lang or "auto")
