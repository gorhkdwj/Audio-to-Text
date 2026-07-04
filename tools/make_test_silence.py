"""테스트용: 무음 WAV를 생성한다 (기본 3초, 16kHz mono PCM16).

사용법: .venv\\Scripts\\python tools/make_test_silence.py [출력.wav] [초]

무음/경계 검증용: 인식 결과 0건일 때 "(인식된 음성 없음)" 출력 확인.
(docs/validation-plan.md, docs/requirements-contract.md — 누락·경계 데이터 처리)
"""

import sys
import wave
from pathlib import Path


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/test_silence.wav")
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    rate = 16000

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16bit
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(rate * seconds))

    print(f"생성: {out_path} ({seconds}초 무음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
