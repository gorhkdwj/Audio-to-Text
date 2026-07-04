"""진입점: python transcribe.py <파일_또는_폴더> [옵션]

전체 옵션은 python transcribe.py --help 참조.
"""

import sys

from audio_to_text.cli import main

if __name__ == "__main__":
    sys.exit(main())
