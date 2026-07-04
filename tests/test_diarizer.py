"""diarizer.py 단위 테스트 — 화자 매칭(순수 로직), 토큰 탐색, 미준비 안내.

pyannote 실제 호출 경로는 E2E(S4, W-010)에서 검증한다(여기서는 다루지 않음).
"""

import os
import unittest
from unittest import mock

import numpy as np

from audio_to_text.diarizer import (
    DiarizationUnavailable,
    assign_speakers,
    diarize_waveform,
    find_hf_token,
)
from audio_to_text.formatters import Segment

DUMMY_WAVE = np.zeros(16000, dtype=np.float32)  # 1초 무음 파형


class FindHfTokenTests(unittest.TestCase):
    def test_explicit_argument_wins(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "env-token"}):
            self.assertEqual(find_hf_token("explicit-token"), "explicit-token")

    def test_environment_variable_used(self):
        with mock.patch.dict(os.environ, {"HF_TOKEN": "env-token"}):
            self.assertEqual(find_hf_token(None), "env-token")

    def test_registry_fallback_when_env_missing(self):
        # 환경변수가 없으면 (Windows) HKCU\Environment를 읽는다 (T-007)
        with mock.patch.dict(os.environ):
            os.environ.pop("HF_TOKEN", None)
            with mock.patch("winreg.OpenKey"), mock.patch(
                "winreg.QueryValueEx", return_value=("registry-token", 1)
            ):
                self.assertEqual(find_hf_token(None), "registry-token")

    def test_none_when_nowhere(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("HF_TOKEN", None)
            with mock.patch("winreg.OpenKey", side_effect=OSError):
                self.assertIsNone(find_hf_token(None))


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
        # 어디서도 토큰을 못 찾는 상황을 모사한다 (이 PC에는 실제 토큰이 있으므로 mock)
        with mock.patch("audio_to_text.diarizer.find_hf_token", return_value=None):
            with self.assertRaises(DiarizationUnavailable) as ctx:
                diarize_waveform(DUMMY_WAVE, hf_token=None)
        self.assertIn("HuggingFace 토큰", str(ctx.exception))
        self.assertIn("requirements-diarize.txt", str(ctx.exception))

    def test_token_without_pyannote_raises_install_guide(self):
        # 토큰은 있지만 pyannote 미설치 상황을 모사(sys.modules 차단) → 설치 안내.
        # (실제 환경에 pyannote가 설치돼 있어도 이 테스트는 미설치 경로를 검증한다)
        import sys

        blocked = {"pyannote": None, "pyannote.audio": None}
        with mock.patch.dict(sys.modules, blocked):
            with self.assertRaises(DiarizationUnavailable) as ctx:
                diarize_waveform(DUMMY_WAVE, hf_token="dummy-token-for-test")
        self.assertIn("pyannote.audio가 설치되어 있지 않습니다", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
