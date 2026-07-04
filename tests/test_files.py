"""files.py 단위 테스트 — 입력 수집·출력 경로 계산·이름 충돌 회피.

규격 출처: docs/requirements-contract.md
"""

import tempfile
import unittest
from pathlib import Path

from audio_to_text.files import (
    InputError,
    InputItem,
    collect_inputs,
    plan_output_paths,
)


class CollectInputsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, relative: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        return path

    def test_missing_path_raises(self):
        with self.assertRaises(InputError):
            collect_inputs([str(self.root / "없는파일.mp3")])

    def test_unsupported_direct_file_warns_and_skips(self):
        path = self._touch("메모.docx")
        items, warnings = collect_inputs([str(path)])
        self.assertEqual(items, [])
        self.assertEqual(len(warnings), 1)

    def test_folder_recursive_collection(self):
        self._touch("a.mp3")
        self._touch("sub/b.wav")
        self._touch("sub/무시.txt")  # 지원하지 않는 확장자는 조용히 제외
        items, warnings = collect_inputs([str(self.root)])
        names = [item.path.name for item in items]
        self.assertEqual(sorted(names), ["a.mp3", "b.wav"])
        self.assertTrue(all(item.base_dir == self.root for item in items))
        self.assertEqual(warnings, [])

    def test_duplicate_input_collected_once(self):
        path = self._touch("a.mp3")
        items, _ = collect_inputs([str(path), str(path)])
        self.assertEqual(len(items), 1)


class PlanOutputPathsTests(unittest.TestCase):
    def test_default_beside_input(self):
        item = InputItem(path=Path("media/강의.mp4"))
        plan, warnings = plan_output_paths([item], ["md", "srt"], output_dir=None)
        self.assertEqual(plan[(item.path, "md")], Path("media/강의.md"))
        self.assertEqual(plan[(item.path, "srt")], Path("media/강의.srt"))
        self.assertEqual(warnings, [])

    def test_output_dir_single_file(self):
        item = InputItem(path=Path("media/강의.mp4"))
        plan, _ = plan_output_paths([item], ["txt"], output_dir="out")
        self.assertEqual(plan[(item.path, "txt")], Path("out/강의.txt"))

    def test_output_dir_mirrors_folder_structure(self):
        base = Path("녹음")
        item = InputItem(path=base / "회의/7월/a.mp3", base_dir=base)
        plan, _ = plan_output_paths([item], ["md"], output_dir="out")
        self.assertEqual(plan[(item.path, "md")], Path("out/회의/7월/a.md"))

    def test_stem_collision_appends_original_extension(self):
        items = [
            InputItem(path=Path("media/a.mp3")),
            InputItem(path=Path("media/a.wav")),
        ]
        plan, warnings = plan_output_paths(items, ["md"], output_dir=None)
        self.assertEqual(plan[(items[0].path, "md")], Path("media/a.mp3.md"))
        self.assertEqual(plan[(items[1].path, "md")], Path("media/a.wav.md"))
        self.assertEqual(len(warnings), 1)

    def test_no_collision_across_mirrored_subfolders(self):
        base = Path("녹음")
        items = [
            InputItem(path=base / "1주차/a.mp3", base_dir=base),
            InputItem(path=base / "2주차/a.mp3", base_dir=base),
        ]
        plan, warnings = plan_output_paths(items, ["md"], output_dir="out")
        self.assertEqual(plan[(items[0].path, "md")], Path("out/1주차/a.md"))
        self.assertEqual(plan[(items[1].path, "md")], Path("out/2주차/a.md"))
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
