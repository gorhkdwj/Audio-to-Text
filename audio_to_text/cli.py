"""CLI 정의와 전체 파이프라인 오케스트레이션.

사용법: python transcribe.py <파일_또는_폴더> [추가입력 ...] [옵션]

규칙 출처: docs/requirements-contract.md
- 종료 코드: 0 = 전체 성공(건너뜀 포함) / 1 = 하나 이상 파일 실패 / 2 = 인자·입력 오류
- 파일 상태: 성공 / 건너뜀(출력 존재 & --overwrite 없음) / 실패
- --diarize 준비 안 됨 → 안내 후 화자 구분 없이 계속 진행 (D-003)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import __version__, diarizer
from . import transcriber as transcriber_mod
from .diarizer import DiarizationUnavailable
from .files import InputError, collect_inputs, plan_output_paths
from .formatters import TranscriptMeta, to_md, to_srt, to_txt


def _force_utf8_output() -> None:
    """Windows 콘솔(cp949 등)에서 한국어 출력이 깨지지 않게 UTF-8로 통일한다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") != "utf8":
                stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcribe",
        description="동영상/오디오 파일의 음성을 인식해 txt/md/srt 텍스트로 추출합니다.",
    )
    parser.add_argument(
        "inputs", nargs="+", metavar="입력", help="변환할 파일 또는 폴더 (복수 지정 가능)"
    )
    parser.add_argument(
        "--format",
        dest="formats",
        nargs="+",
        choices=("txt", "md", "srt"),
        default=["md"],
        help="출력 형식, 복수 지정 가능 (기본: md)",
    )
    parser.add_argument(
        "--output-dir", default=None, help="출력 폴더 (기본: 입력 파일과 같은 위치)"
    )
    parser.add_argument(
        "--model",
        default="auto",
        help="Whisper 모델 (기본: auto → CUDA면 large-v3, CPU면 medium)",
    )
    parser.add_argument(
        "--language", default="ko", help='음성 언어 (기본: ko, "auto"면 자동 감지)'
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="txt/md에서 [HH:MM:SS] 타임스탬프 생략 (순수 텍스트 모드)",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="화자 구분 활성화 (추가 설치 + HuggingFace 토큰 필요)",
    )
    parser.add_argument("--num-speakers", type=int, default=None, help="화자 수 힌트 (선택)")
    parser.add_argument(
        "--device", choices=("auto", "cuda", "cpu"), default="auto", help="추론 장치 (기본: auto)"
    )
    parser.add_argument(
        "--hf-token", default=None, help="pyannote용 HuggingFace 토큰 (기본: HF_TOKEN 환경변수)"
    )
    parser.add_argument("--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _transcribe_one(
    loaded: transcriber_mod.LoadedModel,
    media: Path,
    language: str,
) -> tuple[list, float, str, "object", transcriber_mod.LoadedModel]:
    """파일 하나를 인식한다. GPU 추론 실패 시 CPU로 한 번 재시도한다.

    반환: (세그먼트, 길이, 언어, 파형, 이후에도 계속 쓸 LoadedModel)
    """
    try:
        segments, duration, lang, waveform = transcriber_mod.transcribe_file(
            loaded, media, language
        )
        return segments, duration, lang, waveform, loaded
    except Exception as exc:
        if loaded.device != "cuda":
            raise
        print(f"[안내] GPU 추론에 실패해 CPU(int8)로 다시 시도합니다: {exc}")
        fallback, messages = transcriber_mod.load_model(loaded.requested_name, "cpu")
        for message in messages:
            print(f"[안내] {message}")
        segments, duration, lang, waveform = transcriber_mod.transcribe_file(
            fallback, media, language
        )
        return segments, duration, lang, waveform, fallback


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    args = build_parser().parse_args(argv)

    # 1) 입력 수집
    try:
        items, warnings = collect_inputs(args.inputs)
    except InputError as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 2
    for warning in warnings:
        print(f"[경고] {warning}")
    if not items:
        print("[오류] 변환할 파일이 없습니다.", file=sys.stderr)
        return 2

    # 2) 출력 경로 계획 (이름 충돌 회피 포함)
    plan, name_warnings = plan_output_paths(items, args.formats, args.output_dir)
    for warning in name_warnings:
        print(f"[경고] {warning}")

    print(f"변환 대상: {len(items)}개 파일 → 형식: {', '.join(args.formats)}")

    # 3) 파일별 처리 (모델은 첫 필요 시점에 한 번만 로드 — 전부 건너뛰면 로드 없음)
    loaded: transcriber_mod.LoadedModel | None = None
    diarize_enabled = args.diarize
    succeeded = skipped = failed = 0

    for item in items:
        media = item.path
        outputs = {fmt: plan[(media, fmt)] for fmt in args.formats}

        # 요청한 모든 출력이 이미 있으면 파일 단위 건너뜀
        if not args.overwrite and all(p.exists() for p in outputs.values()):
            print(f"[건너뜀] 출력이 이미 있습니다 (--overwrite로 덮어쓰기): {media}")
            skipped += 1
            continue

        # 3-1) 모델 지연 로드
        if loaded is None:
            print(f"모델 준비 중… (model={args.model}, device={args.device})")
            loaded, load_messages = transcriber_mod.load_model(args.model, args.device)
            for message in load_messages:
                print(f"[안내] {message}")
            print(
                f"모델 로드 완료: {loaded.model_name} ({loaded.device}, {loaded.compute_type})"
            )

        # 3-2) 음성 인식
        try:
            segments, duration, detected_lang, waveform, loaded = _transcribe_one(
                loaded, media, args.language
            )
        except Exception as exc:
            print(f"[실패] {media}: {exc}", file=sys.stderr)
            failed += 1
            continue

        # 3-3) 화자 구분 (선택; 준비 안 됨 → 안내 후 계속)
        # 인식에 쓴 파형을 그대로 재사용한다 — 경로 전달 시 mp4를 못 연다 (T-005)
        if diarize_enabled and segments:
            try:
                turns = diarizer.diarize_waveform(
                    waveform,
                    sample_rate=transcriber_mod.SAMPLE_RATE,
                    hf_token=args.hf_token,
                    num_speakers=args.num_speakers,
                )
                diarizer.assign_speakers(segments, turns)
            except DiarizationUnavailable as exc:
                print(f"[안내] {exc}")
                diarize_enabled = False  # 같은 안내를 반복하지 않는다
            except Exception as exc:
                print(f"[경고] 화자 구분에 실패해 이 파일은 화자 없이 저장합니다: {exc}")

        # 3-4) 출력 저장
        meta = TranscriptMeta(
            source_name=media.name,
            duration=duration,
            model=loaded.model_name,
            language=detected_lang,
            created_at=datetime.now(),
        )
        include_ts = not args.no_timestamps
        try:
            for fmt, out_path in outputs.items():
                if out_path.exists() and not args.overwrite:
                    print(f"[건너뜀] 이미 있습니다: {out_path}")
                    continue
                out_path.parent.mkdir(parents=True, exist_ok=True)
                if fmt == "txt":
                    content = to_txt(segments, include_timestamps=include_ts)
                elif fmt == "md":
                    content = to_md(segments, meta, include_timestamps=include_ts)
                else:  # srt — Windows 자막 플레이어 호환을 위해 UTF-8(BOM)
                    content = to_srt(segments)
                encoding = "utf-8-sig" if fmt == "srt" else "utf-8"
                out_path.write_text(content, encoding=encoding)
                print(f"[저장] {out_path}")
        except OSError as exc:
            print(f"[실패] {media}: 출력 저장 중 오류: {exc}", file=sys.stderr)
            failed += 1
            continue
        succeeded += 1

    # 4) 요약과 종료 코드
    print(f"\n완료: 성공 {succeeded} / 건너뜀 {skipped} / 실패 {failed} (총 {len(items)})")
    return 1 if failed else 0
