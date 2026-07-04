"""테스트용: WAV를 다른 미디어 컨테이너로 변환해 다양한 입력 경로를 검증한다.

사용법: .venv\\Scripts\\python tools/make_test_video.py <입력.wav> [출력]
지원 출력: .mp4 .mkv .mov .ts (AAC) / .webm (Opus 48kHz) / .mp3 (MP3) / .m4a (AAC)

- 컨테이너와 코덱은 출력 확장자로 결정된다.
- FFmpeg 없이 PyAV(기본 의존성 av)만 사용한다. 생성물은 커밋하지 않는다.
(docs/validation-plan.md — 테스트 동영상/오디오 생성)
"""

import sys
from pathlib import Path

import av
from av.audio.resampler import AudioResampler


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src_path = Path(sys.argv[1])
    dst_path = Path(sys.argv[2]) if len(sys.argv) > 2 else src_path.with_suffix(".mp4")
    if not src_path.exists():
        print(f"[오류] 입력 파일이 없습니다: {src_path}")
        return 2
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # 확장자별 코덱: webm은 AAC를 허용하지 않아 Opus(48kHz 필수), mp3는 LAME 인코더
    suffix = dst_path.suffix.lower()
    if suffix == ".webm":
        codec, rate, sample_format = "libopus", 48000, "s16"
    elif suffix == ".mp3":
        codec, rate, sample_format = "libmp3lame", None, "s16p"
    else:
        codec, rate, sample_format = "aac", None, "fltp"

    with av.open(str(src_path)) as src, av.open(str(dst_path), "w") as dst:
        in_stream = src.streams.audio[0]
        out_rate = rate or in_stream.rate or 22050
        out_stream = dst.add_stream(codec, rate=out_rate)
        # 인코더가 요구하는 샘플 형식/레이트로 변환한다.
        resampler = AudioResampler(format=sample_format, layout="mono", rate=out_rate)
        for frame in src.decode(in_stream):
            for resampled in resampler.resample(frame):
                for packet in out_stream.encode(resampled):
                    dst.mux(packet)
        for packet in out_stream.encode():  # 인코더 버퍼 비우기
            dst.mux(packet)

    print(f"생성: {dst_path} (codec={codec}, rate={out_rate})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
