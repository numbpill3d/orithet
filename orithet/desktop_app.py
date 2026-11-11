"""Native Orithet desktop application.

This intentionally uses Qt instead of a browser shell.  The visual language is
inspired by the graphite/platinum Macintosh interfaces: compact controls,
hard borders, bitmap dithering, and a restrained monochrome palette.
"""

import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, Qt, Signal, Slot
from PySide6.QtGui import QColor, QIntValidator, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

try:
    from .core import OrithetCore
except ImportError:  # Support launching the source file from a .desktop entry.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from orithet.core import OrithetCore


LOGGER = logging.getLogger(__name__)


class DitherPanel(QFrame):
    """A subtle procedural bitmap texture that stays crisp at any size."""

    def paintEvent(self, event):  # noqa: N802 - Qt API name
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QColor("#3c3c3c"))
        for y in range(0, self.height(), 4):
            for x in range((y // 4) % 2, self.width(), 4):
                painter.drawPoint(x, y)


class GenerationWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, input_folder, output_path, duration, chaos, seed, resolution, style):
        super().__init__()
        self.args = (input_folder, output_path, duration, chaos, seed, resolution, style)

    @Slot()
    def run(self):
        try:
            input_folder, output_path, duration, chaos, seed, resolution, style = self.args
            engine = OrithetCore(
                input_folder=input_folder,
                duration=duration,
                chaos=chaos,
                seed=seed,
                resolution=resolution,
                style=style,
            )
            result = engine.run(output_path=output_path)
            self.finished.emit(str(result))
        except Exception as exc:  # Surface the error in the UI, not the event loop.
            details = traceback.format_exc()
            report_path = Path.home() / ".cache" / "orithet" / "last-error.log"
            try:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(details, encoding="utf-8")
            except OSError:
                LOGGER.exception("could not write generation error report")
            LOGGER.error("generation failed; full report: %s\n%s", report_path, details)
            self.failed.emit(f"{type(exc).__name__}: {exc}\n\nFull report: {report_path}")


class OrithetWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self._closing = False
        self.setWindowTitle("ORITHET / GENERATIVE VIDEO ART")
        self.setMinimumSize(820, 620)
        self.resize(980, 720)
        self.setStyleSheet(self.stylesheet())
        self.build_ui()

    @staticmethod
    def stylesheet():
        return """
        QWidget { background: #171717; color: #e4e4e4; font-family: 'DejaVu Sans Mono'; font-size: 12px; }
        QMainWindow { background: #171717; }
        QFrame#shell { border: 1px solid #8e8e8e; background: #222222; }
        QFrame#titlebar { background: #c8c8c8; border-bottom: 1px solid #080808; }
        QLabel#title { color: #101010; font-weight: bold; letter-spacing: 2px; }
        QLabel#stamp { color: #454545; font-size: 10px; }
        QLabel#subtitle { color: #b6b6b6; font-size: 11px; }
        QLabel#state { color: #111111; background: #bdbdbd; border: 1px solid #f1f1f1; border-right-color: #555555; border-bottom-color: #555555; padding: 3px 8px; font-weight: bold; }
        QLabel#section { color: #bcbcbc; font-weight: bold; letter-spacing: 1px; }
        QGroupBox { border: 1px solid #696969; margin-top: 14px; padding: 10px 8px 8px 8px; background: #242424; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #d0d0d0; background: #242424; }
        QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #101010; color: #ededed; border: 1px solid #858585; padding: 5px;
            selection-background-color: #d0d0d0; selection-color: #101010;
        }
        QPushButton { background: #c8c8c8; color: #111111; border: 1px solid #f0f0f0; border-right-color: #444444; border-bottom-color: #444444; padding: 7px 12px; font-weight: bold; }
        QPushButton:hover { background: #e1e1e1; }
        QPushButton:pressed { border: 1px solid #444444; border-right-color: #f0f0f0; border-bottom-color: #f0f0f0; }
        QPushButton#generate { background: #8e8e8e; color: #ffffff; font-size: 13px; padding: 11px; }
        QPushButton#generate:hover { background: #ababab; }
        QProgressBar { background: #101010; border: 1px solid #858585; text-align: center; color: #eeeeee; height: 18px; }
        QProgressBar::chunk { background: #8e8e8e; }
        QToolTip { background: #e4e4e4; color: #111111; border: 1px solid #111111; padding: 4px; }
        QScrollBar:vertical { background: #171717; width: 12px; }
        QScrollBar::handle:vertical { background: #777777; min-height: 24px; }
        """

    def build_ui(self):
        self.settings = QSettings("numbpill3d", "Orithet")
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)

        shell = QFrame(objectName="shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)

        titlebar = QFrame(objectName="titlebar")
        title_layout = QHBoxLayout(titlebar)
        title_layout.setContentsMargins(12, 7, 12, 7)
        title = QLabel("ORITHET")
        title.setObjectName("title")
        title_layout.addWidget(title)
        subtitle = QLabel("GENERATIVE VIDEO ART")
        subtitle.setObjectName("subtitle")
        title_layout.addWidget(subtitle)
        title_layout.addStretch()
        stamp = QLabel("PULSE // ECHO // GLITCH // FRACTAL")
        stamp.setObjectName("stamp")
        title_layout.addWidget(stamp)
        self.state = QLabel("READY")
        self.state.setObjectName("state")
        title_layout.addWidget(self.state)
        shell_layout.addWidget(titlebar)

        dither = DitherPanel()
        dither.setFixedHeight(12)
        shell_layout.addWidget(dither)

        content = QGridLayout()
        content.setContentsMargins(16, 12, 16, 16)
        content.setHorizontalSpacing(16)
        content.setVerticalSpacing(10)
        shell_layout.addLayout(content)

        input_box = QGroupBox("SOURCE MATERIAL")
        input_layout = QGridLayout(input_box)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Choose a folder containing images, videos, and audio...")
        self.browse_input = QPushButton("BROWSE")
        self.browse_input.clicked.connect(self.choose_input)
        self.browse_input.setToolTip("Choose a folder containing source media")
        media_label = QLabel("MEDIA FOLDER")
        media_label.setMinimumWidth(96)
        input_layout.addWidget(media_label, 0, 0)
        input_layout.addWidget(self.input_path, 0, 1)
        input_layout.addWidget(self.browse_input, 0, 2)

        output_box = QGroupBox("OUTPUT")
        output_layout = QGridLayout(output_box)
        self.output_path = QLineEdit(str(Path.home() / "Videos" / "orithet_output.mp4"))
        self.browse_output = QPushButton("SAVE AS")
        self.browse_output.clicked.connect(self.choose_output)
        self.browse_output.setToolTip("Choose where the generated MP4 will be saved")
        video_label = QLabel("VIDEO FILE")
        video_label.setMinimumWidth(96)
        output_layout.addWidget(video_label, 0, 0)
        output_layout.addWidget(self.output_path, 0, 1)
        output_layout.addWidget(self.browse_output, 0, 2)

        left = QVBoxLayout()
        left.addWidget(input_box)
        left.addWidget(output_box)
        left.addStretch()
        content.addLayout(left, 0, 0)

        settings = QGroupBox("TRANSMISSION SETTINGS")
        form = QFormLayout(settings)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.duration = QDoubleSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setDecimals(1)
        self.duration.setValue(120)
        self.duration.setSuffix(" sec")
        self.chaos = QDoubleSpinBox()
        self.chaos.setRange(0, 1)
        self.chaos.setDecimals(2)
        self.chaos.setSingleStep(0.05)
        self.chaos.setValue(0.5)
        self.seed = QLineEdit()
        self.seed.setPlaceholderText("AUTO")
        self.seed.setValidator(QIntValidator(-2147483648, 2147483647, self.seed))
        self.seed.setToolTip("Leave blank for a random seed; 0 is a valid reproducible seed")
        self.style = QComboBox()
        self.style.addItems(["dream", "glitch", "psychedelic", "ambient"])
        self.style.setToolTip("Select the visual behavior preset")
        self.resolution = QComboBox()
        self.resolution.addItem("1920 × 1080", (1920, 1080))
        self.resolution.addItem("1280 × 720", (1280, 720))
        self.resolution.addItem("3840 × 2160", (3840, 2160))
        self.resolution.setToolTip("Choose the output frame size")
        settings_fields = (
            ("DURATION", self.duration),
            ("CHAOS", self.chaos),
            ("SEED", self.seed),
            ("STYLE", self.style),
            ("RESOLUTION", self.resolution),
        )
        for label_text, field in settings_fields:
            label = QLabel(label_text)
            label.setMinimumWidth(88)
            form.addRow(label, field)
        content.addWidget(settings, 0, 1)

        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumBlockCount(100)
        self.status.setPlaceholderText("READY. Select source material to begin.")
        content.addWidget(self.status, 1, 0, 1, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFormat("WORKING // PLEASE WAIT")
        self.progress.hide()
        content.addWidget(self.progress, 2, 0, 1, 2)

        self.generate = QPushButton("GENERATE VIDEO")
        self.generate.setObjectName("generate")
        self.generate.setToolTip("Generate the video (Ctrl+G)")
        self.generate.clicked.connect(self.start_generation)
        content.addWidget(self.generate, 3, 0, 1, 2)

        outer.addWidget(shell)
        self.setCentralWidget(root)
        self.setTabOrder(self.input_path, self.browse_input)
        self.setTabOrder(self.browse_input, self.output_path)
        self.setTabOrder(self.output_path, self.browse_output)
        self.setTabOrder(self.browse_output, self.duration)
        self.setTabOrder(self.duration, self.chaos)
        self.setTabOrder(self.chaos, self.seed)
        self.setTabOrder(self.seed, self.style)
        self.setTabOrder(self.style, self.resolution)
        self.setTabOrder(self.resolution, self.generate)
        shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        shortcut.activated.connect(self.start_generation)
        self.append_status("SYSTEM ONLINE // native Qt interface ready")
        self.restore_preferences()

    def append_status(self, message):
        self.status.appendPlainText(message)
        self.status.ensureCursorVisible()

    def set_state(self, label, active=False):
        self.state.setText(label)
        self.state.setStyleSheet(
            "QLabel#state { background: %s; color: %s; }"
            % (("#777777", "#ffffff") if active else ("#bdbdbd", "#111111"))
        )

    def choose_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Orithet media folder")
        if folder:
            self.input_path.setText(folder)
            self.settings.setValue("input_folder", folder)
            self.append_status(f"SOURCE LOCKED // {folder}")

    def choose_output(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Choose output video", self.output_path.text(), "MP4 video (*.mp4)"
        )
        if filename:
            self.output_path.setText(filename)
            self.settings.setValue("output_path", filename)

    def restore_preferences(self):
        input_folder = self.settings.value("input_folder", "")
        output_path = self.settings.value(
            "output_path", str(Path.home() / "Videos" / "orithet_output.mp4")
        )
        self.input_path.setText(input_folder)
        self.output_path.setText(output_path)
        self.duration.setValue(float(self.settings.value("duration", 120)))
        self.chaos.setValue(float(self.settings.value("chaos", 0.5)))
        seed = self.settings.value("seed", "")
        self.seed.setText("" if seed in (None, "") else str(seed))
        self.style.setCurrentText(self.settings.value("style", "dream"))
        resolution = self.settings.value("resolution", "1920x1080")
        for index in range(self.resolution.count()):
            width, height = self.resolution.itemData(index)
            if f"{width}x{height}" == resolution:
                self.resolution.setCurrentIndex(index)
                break
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def save_preferences(self):
        self.settings.setValue("input_folder", self.input_path.text().strip())
        self.settings.setValue("output_path", self.output_path.text().strip())
        self.settings.setValue("duration", self.duration.value())
        self.settings.setValue("chaos", self.chaos.value())
        self.settings.setValue("seed", self.seed.text().strip())
        self.settings.setValue("style", self.style.currentText())
        width, height = self.resolution.currentData()
        self.settings.setValue("resolution", f"{width}x{height}")
        self.settings.setValue("geometry", self.saveGeometry())

    def set_generation_state(self, running):
        self.generate.setEnabled(not running)
        for widget in (
            self.input_path, self.output_path, self.browse_input, self.browse_output,
            self.duration, self.chaos, self.seed, self.style, self.resolution,
        ):
            widget.setEnabled(not running)
        if running:
            self.progress.show()
            self.set_state("WORKING", active=True)
        else:
            self.progress.hide()
            self.set_state("READY")

    def start_generation(self):
        if self.thread is not None and self.thread.isRunning():
            return
        input_folder = self.input_path.text().strip()
        output_path = self.output_path.text().strip()
        source = Path(input_folder).expanduser()
        if not source.is_dir():
            QMessageBox.warning(self, "SOURCE REQUIRED", "Choose an existing media folder before generating.")
            self.set_state("CHECK SOURCE")
            return
        if not input_folder:
            QMessageBox.warning(self, "SOURCE REQUIRED", "Choose a media folder before generating.")
            return
        if not output_path:
            QMessageBox.warning(self, "OUTPUT REQUIRED", "Choose an output video path.")
            return

        output = Path(output_path).expanduser()
        if output.suffix.lower() != ".mp4":
            output = output.with_suffix(".mp4")
            output_path = str(output)
            self.output_path.setText(output_path)
        if output.exists():
            answer = QMessageBox.question(
                self, "REPLACE OUTPUT?", f"{output.name} already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        seed_text = self.seed.text().strip()
        seed = int(seed_text) if seed_text else None
        resolution = self.resolution.currentData()
        self.save_preferences()
        self.set_generation_state(True)
        self.append_status("GENERATION STARTED // scanning source material...")

        self.thread = QThread(self)
        self.worker = GenerationWorker(
            input_folder,
            output_path,
            self.duration.value(),
            self.chaos.value(),
            seed,
            resolution,
            self.style.currentText(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.generation_finished)
        self.worker.failed.connect(self.generation_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()

    @Slot(str)
    def generation_finished(self, output_path):
        self.set_generation_state(False)
        self.append_status(f"COMPLETE // rendered to {output_path}")
        QMessageBox.information(self, "ORITHET COMPLETE", f"Video rendered to:\n{output_path}")

    @Slot(str)
    def generation_failed(self, message):
        self.set_generation_state(False)
        self.set_state("ERROR")
        self.append_status(f"ERROR // {message}")
        QMessageBox.critical(self, "GENERATION FAILED", message)

    def closeEvent(self, event):  # noqa: N802 - Qt API name
        if self._closing:
            event.accept()
            return
        if self.thread is not None and self.thread.isRunning():
            answer = QMessageBox.question(
                self,
                "GENERATION IN PROGRESS",
                "A render is still running. Close the window and abandon it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self._closing = True
        try:
            self.save_preferences()
        except RuntimeError:
            # Qt may already have destroyed child widgets during application shutdown.
            LOGGER.debug("preferences skipped during late Qt shutdown", exc_info=True)
        super().closeEvent(event)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Orithet")
    app.setOrganizationName("numbpill3d")
    window = OrithetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
