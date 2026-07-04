"""Audio to Text — 로컬 데스크톱 GUI (PySide6).

검증된 CLI(transcribe.py)를 하위 프로세스(QProcess)로 호출하는 얇은 껍데기다.
변환 규칙·옵션 의미·출력 규격은 CLI와 완전히 동일하다
(docs/requirements-contract.md의 "GUI" 절, D-004).

실행:
  .venv\\Scripts\\python gui.py          (개발용)
  Audio_to_Text.bat 더블클릭             (일반 사용, 콘솔 창 없음)
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

PROJECT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
TRANSCRIBE_SCRIPT = PROJECT_DIR / "transcribe.py"

# 언어 선택지 (표시 이름, --language 값)
LANGUAGES = [
    ("한국어", "ko"),
    ("자동 감지", "auto"),
    ("영어", "en"),
    ("일본어", "ja"),
    ("중국어", "zh"),
]


def build_command(
    inputs: list[str],
    formats: list[str],
    language: str = "ko",
    diarize: bool = False,
    num_speakers: int = 0,
    no_timestamps: bool = False,
    overwrite: bool = False,
    output_dir: str = "",
) -> list[str]:
    """GUI 옵션을 CLI 인자 목록으로 조립한다 (순수 함수 — 단위 테스트 대상).

    반환값은 python.exe 뒤에 붙는 인자들: [transcribe.py, 입력들..., 옵션들...]
    매핑 규칙 출처: docs/requirements-contract.md "GUI" 절.
    """
    args = [str(TRANSCRIBE_SCRIPT), *inputs, "--format", *formats, "--language", language]
    if output_dir:
        args += ["--output-dir", output_dir]
    if no_timestamps:
        args.append("--no-timestamps")
    if diarize:
        args.append("--diarize")
        if num_speakers > 0:
            args += ["--num-speakers", str(num_speakers)]
    if overwrite:
        args.append("--overwrite")
    return args


def media_file_filter() -> str:
    """파일 선택 대화상자용 필터 문자열 (지원 확장자는 files.py가 단일 출처)."""
    from audio_to_text.files import SUPPORTED_EXTENSIONS

    patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
    return f"미디어 파일 ({patterns});;모든 파일 (*.*)"


class MainWindow(QWidget):
    """단일 창 GUI. 공개 메서드(add_paths·start_conversion·log_text)는
    헤드리스 점검(tools/check_gui.py)에서도 사용한다."""

    def __init__(self) -> None:
        super().__init__()
        self.process: QProcess | None = None
        self.setWindowTitle("Audio to Text — 음성 → 텍스트 변환기")
        self.resize(700, 680)
        self.setAcceptDrops(True)
        self._build_ui()

    # ---------- UI 구성 ----------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # 1) 입력 파일 목록
        input_box = QGroupBox("1. 변환할 파일·폴더  (여기로 드래그해서 놓아도 됩니다)")
        input_layout = QVBoxLayout(input_box)
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(110)
        input_layout.addWidget(self.file_list)
        button_row = QHBoxLayout()
        btn_add_files = QPushButton("파일 추가…")
        btn_add_files.clicked.connect(self._add_files)
        btn_add_folder = QPushButton("폴더 추가…")
        btn_add_folder.clicked.connect(self._add_folder)
        btn_clear = QPushButton("목록 비우기")
        btn_clear.clicked.connect(self.file_list.clear)
        button_row.addWidget(btn_add_files)
        button_row.addWidget(btn_add_folder)
        button_row.addWidget(btn_clear)
        button_row.addStretch()
        input_layout.addLayout(button_row)
        root.addWidget(input_box)

        # 2) 옵션
        option_box = QGroupBox("2. 옵션")
        option_layout = QVBoxLayout(option_box)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("출력 형식:"))
        self.chk_md = QCheckBox("md (읽기용 문서)")
        self.chk_md.setChecked(True)
        self.chk_txt = QCheckBox("txt (타임스탬프 텍스트)")
        self.chk_srt = QCheckBox("srt (자막)")
        for chk in (self.chk_md, self.chk_txt, self.chk_srt):
            format_row.addWidget(chk)
        format_row.addStretch()
        option_layout.addLayout(format_row)

        toggle_row = QHBoxLayout()
        self.chk_diarize = QCheckBox("화자 구분 (여러 명 대화)")
        toggle_row.addWidget(self.chk_diarize)
        toggle_row.addWidget(QLabel("화자 수:"))
        self.spin_speakers = QSpinBox()
        self.spin_speakers.setRange(0, 10)
        self.spin_speakers.setSpecialValueText("자동")
        toggle_row.addWidget(self.spin_speakers)
        self.chk_no_timestamps = QCheckBox("타임스탬프 생략")
        toggle_row.addWidget(self.chk_no_timestamps)
        self.chk_overwrite = QCheckBox("기존 결과 덮어쓰기")
        toggle_row.addWidget(self.chk_overwrite)
        toggle_row.addStretch()
        option_layout.addLayout(toggle_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("음성 언어:"))
        self.cmb_language = QComboBox()
        for display, code in LANGUAGES:
            self.cmb_language.addItem(display, code)
        lang_row.addWidget(self.cmb_language)
        lang_row.addSpacing(16)
        lang_row.addWidget(QLabel("출력 폴더:"))
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setReadOnly(True)
        self.edit_output_dir.setPlaceholderText("(비워두면 원본 파일 옆에 저장)")
        lang_row.addWidget(self.edit_output_dir, stretch=1)
        btn_output = QPushButton("변경…")
        btn_output.clicked.connect(self._choose_output_dir)
        lang_row.addWidget(btn_output)
        btn_output_reset = QPushButton("기본값")
        btn_output_reset.clicked.connect(self.edit_output_dir.clear)
        lang_row.addWidget(btn_output_reset)
        option_layout.addLayout(lang_row)
        root.addWidget(option_box)

        # 3) 실행·로그
        run_box = QGroupBox("3. 변환")
        run_layout = QVBoxLayout(run_box)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        run_layout.addWidget(self.progress)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setPlaceholderText("변환을 시작하면 진행 내용이 여기에 표시됩니다.")
        run_layout.addWidget(self.log_view, stretch=1)
        action_row = QHBoxLayout()
        self.btn_start = QPushButton("변환 시작")
        self.btn_start.setMinimumHeight(36)
        self.btn_start.clicked.connect(self._start_or_stop)
        action_row.addWidget(self.btn_start, stretch=1)
        self.btn_open_output = QPushButton("출력 폴더 열기")
        self.btn_open_output.clicked.connect(self._open_output_folder)
        action_row.addWidget(self.btn_open_output)
        run_layout.addLayout(action_row)
        root.addWidget(run_box, stretch=1)

    # ---------- 드래그&드롭 ----------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt 규약)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt 규약)
        paths = [
            url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()
        ]
        self.add_paths(paths)

    # ---------- 입력 관리 ----------
    def add_paths(self, paths: list[str]) -> None:
        existing = {self.file_list.item(i).text() for i in range(self.file_list.count())}
        for raw in paths:
            path = str(Path(raw))
            if path and path not in existing and Path(path).exists():
                self.file_list.addItem(path)
                existing.add(path)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "변환할 미디어 파일 선택", "", media_file_filter()
        )
        self.add_paths(files)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "변환할 폴더 선택")
        if folder:
            self.add_paths([folder])

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if folder:
            self.edit_output_dir.setText(str(Path(folder)))

    # ---------- 변환 실행 ----------
    def current_inputs(self) -> list[str]:
        return [self.file_list.item(i).text() for i in range(self.file_list.count())]

    def current_formats(self) -> list[str]:
        formats = []
        if self.chk_txt.isChecked():
            formats.append("txt")
        if self.chk_md.isChecked():
            formats.append("md")
        if self.chk_srt.isChecked():
            formats.append("srt")
        return formats

    def _start_or_stop(self) -> None:
        if self.process is not None:  # 실행 중 → 중지
            self._append_log("[중지] 사용자가 변환을 중지했습니다.")
            self.process.kill()
            return
        self.start_conversion()

    def start_conversion(self) -> None:
        inputs = self.current_inputs()
        formats = self.current_formats()
        if not inputs:
            QMessageBox.warning(self, "입력 없음", "변환할 파일이나 폴더를 먼저 추가하십시오.")
            return
        if not formats:
            QMessageBox.warning(self, "형식 없음", "출력 형식을 하나 이상 선택하십시오.")
            return

        args = build_command(
            inputs=inputs,
            formats=formats,
            language=self.cmb_language.currentData(),
            diarize=self.chk_diarize.isChecked(),
            num_speakers=self.spin_speakers.value(),
            no_timestamps=self.chk_no_timestamps.isChecked(),
            overwrite=self.chk_overwrite.isChecked(),
            output_dir=self.edit_output_dir.text().strip(),
        )

        self.log_view.clear()
        # 사용자가 CLI 사용법도 익힐 수 있게 동일 명령을 보여준다
        self._append_log(
            "실행: python " + " ".join(f'"{a}"' if " " in a else a for a in args)
        )
        self._append_log("-" * 60)

        process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("TQDM_DISABLE", "1")  # 로그 창에는 진행률 바 대신 결과 줄만
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(PROJECT_DIR))
        process.setProgram(str(VENV_PYTHON))
        process.setArguments(args)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._on_output)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_process_error)
        self.process = process
        self._set_running(True)
        process.start()

    # ---------- 프로세스 이벤트 ----------
    def _on_output(self) -> None:
        if self.process is None:
            return
        data = bytes(self.process.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip():
                self._append_log(line.rstrip())

    def _on_finished(self, exit_code: int, _status) -> None:
        self._append_log("-" * 60)
        if exit_code == 0:
            self._append_log("✅ 변환이 끝났습니다. [출력 폴더 열기]로 결과를 확인하십시오.")
        elif exit_code == 1:
            self._append_log("⚠️ 일부 파일이 실패했습니다. 위 로그의 [실패] 줄을 확인하십시오.")
        else:
            self._append_log(f"❌ 변환이 중단되었습니다 (종료 코드 {exit_code}).")
        self.process = None
        self._set_running(False)

    def _on_process_error(self, _error) -> None:
        if self.process is not None:
            self._append_log(f"[오류] 변환 프로세스 실행 실패: {self.process.errorString()}")

    # ---------- 보조 ----------
    def _set_running(self, running: bool) -> None:
        self.btn_start.setText("중지" if running else "변환 시작")
        if running:
            self.progress.setRange(0, 0)  # 진행 중 애니메이션
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def log_text(self) -> str:
        return self.log_view.toPlainText()

    def _open_output_folder(self) -> None:
        target = self.edit_output_dir.text().strip()
        if not target:
            inputs = self.current_inputs()
            if not inputs:
                QMessageBox.information(
                    self, "안내", "열 폴더가 없습니다. 파일을 추가하거나 출력 폴더를 지정하십시오."
                )
                return
            first = Path(inputs[0])
            target = str(first if first.is_dir() else first.parent)
        if Path(target).exists():
            os.startfile(target)  # noqa: S606 — 로컬 폴더 열기(Windows)


def main() -> int:
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception:  # pythonw(무콘솔) 실행에서도 원인을 남긴다
        error_log = PROJECT_DIR / "out" / "gui-error.log"
        error_log.parent.mkdir(parents=True, exist_ok=True)
        error_log.write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    sys.exit(main())
