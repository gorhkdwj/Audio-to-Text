"""diarizer.py 단위 테스트 — 세그먼트-화자 매칭(순수 로직)과 미준비 안내.

pyannote 실제 호출 경로는 S4에서 검증한다(여기서는 다루지 않음).
"""

import unittest
from pathlib import Path

from audio_to_text.diarizer import (
    DiarizationUnavailable,
    assign_speakers,
    diarize_file,
)
from audio_to_text.formatters import Segment


class AssignSpeakersTests(unittest.TestCase):
    def test_labels_numbered_by_first_appearance(self):
        # SPEAKER_01이 먼저 말했으므로 "화자 1"이 되어야 한다 (D-003)
        turns = [
            (0.0, 2.0, "SPEAKER_01"),
            (2.0, 4.0, "SPEAKER_00"),
        ]
        segs = [Segment(0.5, 1.5, "먼저"), Segment(2.5, 3.5, "나중")]
        assign_speakers(segs, turns)
        self.assertEqual(segs[0].speaker, "화자 1")
        self.assertEqual(segs[1].speaker, "화자 2")

    def test_max_overlap_wins(self):
        turns = [
            (0.0, 1.0, "A"),  # 세그먼트와 1.0초 겹침
            (1.0, 5.0, "B"),  # 세그먼트와 2.0초 겹침 → B가 할당
        ]
        segs = [Segment(0.0, 3.0, "텍스트")]
        assign_speakers(segs, turns)
        self.assertEqual(segs[0].speaker, "화자 2")

    def test_no_overlap_leaves_segment_unlabeled(self):
        turns = [(10.0, 12.0, "A")]
        segs = [Segment(0.0, 1.0, "텍스트")]
        assign_speakers(segs, turns)
        self.assertIsNone(segs[0].speaker)

    def test_empty_turns_is_noop(self):
        segs = [Segment(0.0, 1.0, "텍스트")]
        assign_speakers(segs, [])
        self.assertIsNone(segs[0].speaker)


class DiarizeFileGuardTests(unittest.TestCase):
    def test_missing_token_raises_korean_guide(self):
        # HF_TOKEN 환경변수가 없는 상태를 가정한다 (테스트 환경 기본값)
        import os

        old = os.environ.pop("HF_TOKEN", None)
        try:
            with self.assertRaises(DiarizationUnavailable) as ctx:
                diarize_file(Path("아무.wav"), hf_token=None)
            self.assertIn("HuggingFace 토큰", str(ctx.exception))
            self.assertIn("requirements-diarize.txt", str(ctx.exception))
        finally:
            if old is not None:
                os.environ["HF_TOKEN"] = old

    def test_token_without_pyannote_raises_install_guide(self):
        # 토큰은 있지만 pyannote 미설치(기본 환경) → 설치 안내
        with self.assertRaises(DiarizationUnavailable) as ctx:
            diarize_file(Path("아무.wav"), hf_token="dummy-token-for-test")
        self.assertIn("pyannote.audio가 설치되어 있지 않습니다", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
