"""테스트용: WAV를 mp4(AAC) 컨테이너로 변환해 "동영상 입력" 경로를 검증한다.

사용법: .venv\\Scripts\\python tools/make_test_video.py <입력.wav> [출력.mp4]

FFmpeg 없이 PyAV(기본 의존성 av)만 사용한다. 생성물은 커밋하지 않는다.
(docs/validation-plan.md — 테스트 동영상 생성)
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

    with av.open(str(src_path)) as src, av.open(str(dst_path), "w") as dst:
        in_stream = src.streams.audio[0]
        rate = in_stream.rate or 22050
        out_stream = dst.add_stream("aac", rate=rate)
        # AAC 인코더는 fltp 샘플 형식을 요구하므로 변환한다.
        resampler = AudioResampler(format="fltp", layout="mono", rate=rate)
        for frame in src.decode(in_stream):
            for resampled in resampler.resample(frame):
                for packet in out_stream.encode(resampled):
                    dst.mux(packet)
        for packet in out_stream.encode():  # 인코더 버퍼 비우기
            dst.mux(packet)

    print(f"생성: {dst_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
