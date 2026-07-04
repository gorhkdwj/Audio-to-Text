"""GUI 헤드리스 점검 도구 — 화면 없이 실제 창을 구성하고 변환 1건을 E2E로 수행한다.

사용법: .venv\\Scripts\\python tools/check_gui.py <미디어 파일> [출력 폴더]

QT_QPA_PLATFORM=offscreen 으로 창을 렌더링 없이 만들고,
GUI의 공개 메서드(add_paths → start_conversion)를 그대로 호출해
QProcess → CLI → 출력 파일 생성까지의 배선을 검증한다.
(클릭·드래그 같은 실제 상호작용은 사용자 수동 확인 대상 — docs/validation-plan.md)
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    media = Path(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) > 2 else str(PROJECT_DIR / "out" / "gui_check")
    if not media.exists():
        print(f"[오류] 입력 파일이 없습니다: {media}")
        return 2

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    import gui

    app = QApplication([])
    window = gui.MainWindow()

    # 사용자가 하는 조작을 코드로 재현
    window.add_paths([str(media)])
    window.chk_overwrite.setChecked(True)
    window.edit_output_dir.setText(output_dir)
    window.start_conversion()

    if window.process is None:
        print("[실패] 변환 프로세스가 시작되지 않았습니다 (입력/형식 검증 확인).")
        return 1
    window.process.finished.connect(app.quit)
    QTimer.singleShot(600_000, app.quit)  # 10분 타임아웃 보호
    app.exec()

    log = window.log_text()
    print("--- GUI 로그 마지막 부분 ---")
    print("\n".join(log.splitlines()[-6:]))

    expected = Path(output_dir) / f"{media.stem}.md"
    if "✅" in log and expected.exists():
        print(f"[통과] GUI 헤드리스 E2E — 생성 확인: {expected}")
        return 0
    print(f"[실패] 완료 표시={'✅' in log}, 파일 존재={expected.exists()}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
