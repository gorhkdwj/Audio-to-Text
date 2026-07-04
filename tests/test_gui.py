"""gui.py 단위 테스트 — CLI 인자 조립(build_command) 검증.

창을 띄우지 않고 순수 함수만 검사한다. GUI 동작 자체는
tools/check_gui.py(헤드리스 E2E)와 수동 확인으로 검증한다.
"""

import unittest

try:
    import PySide6  # noqa: F401

    HAVE_QT = True
except ImportError:
    HAVE_QT = False

if HAVE_QT:
    from gui import TRANSCRIBE_SCRIPT, build_command


@unittest.skipUnless(HAVE_QT, "PySide6 미설치 환경 — GUI 선택 기능")
class BuildCommandTests(unittest.TestCase):
    def test_minimal_defaults(self):
        args = build_command(inputs=["a.mp4"], formats=["md"])
        self.assertEqual(args[0], str(TRANSCRIBE_SCRIPT))
        self.assertIn("a.mp4", args)
        self.assertEqual(args[args.index("--format") + 1], "md")
        self.assertEqual(args[args.index("--language") + 1], "ko")
        for absent in ("--diarize", "--no-timestamps", "--overwrite", "--output-dir"):
            self.assertNotIn(absent, args)

    def test_multiple_inputs_and_formats(self):
        args = build_command(inputs=["a.wav", "b폴더"], formats=["txt", "md", "srt"])
        index = args.index("--format")
        self.assertEqual(args[index + 1 : index + 4], ["txt", "md", "srt"])
        self.assertIn("a.wav", args)
        self.assertIn("b폴더", args)

    def test_diarize_with_speaker_hint(self):
        args = build_command(
            inputs=["a.mp4"], formats=["md"], diarize=True, num_speakers=2
        )
        self.assertIn("--diarize", args)
        self.assertEqual(args[args.index("--num-speakers") + 1], "2")

    def test_speaker_hint_zero_means_auto(self):
        args = build_command(
            inputs=["a.mp4"], formats=["md"], diarize=True, num_speakers=0
        )
        self.assertIn("--diarize", args)
        self.assertNotIn("--num-speakers", args)

    def test_speaker_hint_ignored_without_diarize(self):
        args = build_command(
            inputs=["a.mp4"], formats=["md"], diarize=False, num_speakers=3
        )
        self.assertNotIn("--diarize", args)
        self.assertNotIn("--num-speakers", args)

    def test_all_toggles(self):
        args = build_command(
            inputs=["a.mp4"],
            formats=["srt"],
            language="auto",
            no_timestamps=True,
            overwrite=True,
            output_dir="C:\\결과",
        )
        self.assertEqual(args[args.index("--language") + 1], "auto")
        self.assertEqual(args[args.index("--output-dir") + 1], "C:\\결과")
        self.assertIn("--no-timestamps", args)
        self.assertIn("--overwrite", args)


if __name__ == "__main__":
    unittest.main()
