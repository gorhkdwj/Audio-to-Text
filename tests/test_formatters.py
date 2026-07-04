"""formatters.py 단위 테스트 — 타임스탬프·문단 병합·txt/md/srt 규격.

규격 출처: docs/requirements-contract.md
실행: .venv\\Scripts\\python -m unittest discover -s tests -v
"""

import unittest
from datetime import datetime

from audio_to_text.formatters import (
    EMPTY_NOTICE,
    Segment,
    TranscriptMeta,
    format_srt_timestamp,
    format_timestamp,
    merge_paragraphs,
    to_md,
    to_srt,
    to_txt,
)


def make_meta() -> TranscriptMeta:
    return TranscriptMeta(
        source_name="sample.wav",
        duration=7.5,
        model="small",
        language="ko",
        created_at=datetime(2026, 7, 4, 12, 0, 0),
    )


class TimestampTests(unittest.TestCase):
    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(0), "00:00:00")
        self.assertEqual(format_timestamp(83.4), "00:01:23")
        self.assertEqual(format_timestamp(3661.5), "01:01:01")

    def test_format_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(3661.5), "01:01:01,500")
        self.assertEqual(format_srt_timestamp(1.007), "00:00:01,007")


class ParagraphTests(unittest.TestCase):
    def test_merge_by_gap(self):
        segs = [
            Segment(0.0, 1.0, "가"),
            Segment(1.5, 2.5, "나"),  # 간격 0.5초 → 같은 문단
            Segment(5.0, 6.0, "다"),  # 간격 2.5초 → 새 문단
        ]
        paragraphs = merge_paragraphs(segs)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual([s.text for s in paragraphs[0]], ["가", "나"])

    def test_split_on_speaker_change(self):
        segs = [
            Segment(0.0, 1.0, "가", speaker="화자 1"),
            Segment(1.2, 2.0, "나", speaker="화자 2"),  # 화자 변경 → 새 문단
        ]
        self.assertEqual(len(merge_paragraphs(segs)), 2)


class TxtTests(unittest.TestCase):
    def test_with_timestamps_and_speaker(self):
        segs = [Segment(83.0, 85.0, " 안녕하세요 ", speaker="화자 1")]
        self.assertEqual(to_txt(segs), "[00:01:23] 화자 1: 안녕하세요\n")

    def test_no_timestamps_merges_paragraphs(self):
        segs = [Segment(0.0, 1.0, "가"), Segment(1.2, 2.0, "나"), Segment(5.0, 6.0, "다")]
        self.assertEqual(to_txt(segs, include_timestamps=False), "가 나\n\n다\n")

    def test_empty(self):
        self.assertEqual(to_txt([]), EMPTY_NOTICE + "\n")


class MdTests(unittest.TestCase):
    def test_meta_table_and_body(self):
        segs = [Segment(0.0, 1.0, "안녕하세요")]
        md = to_md(segs, make_meta())
        self.assertIn("# sample.wav", md)
        self.assertIn("| 모델 | small |", md)
        self.assertIn("| 길이 | 00:00:07 |", md)
        self.assertIn("| 생성일 | 2026-07-04 12:00:00 |", md)
        self.assertIn("[00:00:00] 안녕하세요", md)

    def test_speaker_bold_and_no_timestamps(self):
        segs = [Segment(0.0, 1.0, "안녕", speaker="화자 1")]
        md = to_md(segs, make_meta(), include_timestamps=False)
        self.assertIn("**화자 1:** 안녕", md)
        self.assertNotIn("[00:00:00]", md)

    def test_empty(self):
        md = to_md([], make_meta())
        self.assertIn(EMPTY_NOTICE, md)


class SrtTests(unittest.TestCase):
    def test_standard_blocks(self):
        segs = [
            Segment(0.0, 1.5, "첫 번째"),
            Segment(2.0, 3.25, "두 번째", speaker="화자 2"),
        ]
        srt = to_srt(segs)
        expected = (
            "1\n00:00:00,000 --> 00:00:01,500\n첫 번째\n"
            "\n"
            "2\n00:00:02,000 --> 00:00:03,250\n화자 2: 두 번째\n"
        )
        self.assertEqual(srt, expected)

    def test_empty_has_notice_block(self):
        srt = to_srt([])
        self.assertIn("1\n00:00:00,000 --> 00:00:01,000\n" + EMPTY_NOTICE, srt)


if __name__ == "__main__":
    unittest.main()
