"""Native Orithet desktop application.

This intentionally uses Qt instead of a browser shell.  The visual language is
inspired by the graphite/platinum Macintosh interfaces: compact controls,
hard borders, bitmap dithering, and a restrained monochrome palette.
"""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
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
    QSpinBox,
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
            LOGGER.exception("generation failed")
            self.failed.emit(str(exc))


class OrithetWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
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
        QScrollBar:vertical { background: #171717; width: 12px; }
        QScrollBar::handle:vertical { background: #777777; min-height: 24px; }
        """

    def build_ui(self):
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
        title_layout.addStretch()
        stamp = QLabel("PULSEFORGE // ECHOMOSAIC // GLITCHGARDEN // FRACTALFUSION")
        stamp.setObjectName("stamp")
        title_layout.addWidget(stamp)
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
        browse = QPushButton("BROWSE")
        browse.clicked.connect(self.choose_input)
        input_layout.addWidget(QLabel("MEDIA FOLDER"), 0, 0)
        input_layout.addWidget(self.input_path, 0, 1)
        input_layout.addWidget(browse, 0, 2)

        output_box = QGroupBox("OUTPUT")
        output_layout = QGridLayout(output_box)
        self.output_path = QLineEdit(str(Path.home() / "Videos" / "orithet_output.mp4"))
        output_browse = QPushButton("SAVE AS")
        output_browse.clicked.connect(self.choose_output)
        output_layout.addWidget(QLabel("VIDEO FILE"), 0, 0)
        output_layout.addWidget(self.output_path, 0, 1)
        output_layout.addWidget(output_browse, 0, 2)

        left = QVBoxLayout()
        left.addWidget(input_box)
        left.addWidget(output_box)
        left.addStretch()
        content.addLayout(left, 0, 0)

        settings = QGroupBox("TRANSMISSION SETTINGS")
        form = QFormLayout(settings)
        form.setLabelAlignment(Qt.AlignLeft)
        self.duration = QDoubleSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(120)
        self.duration.setSuffix(" sec")
        self.chaos = QDoubleSpinBox()
        self.chaos.setRange(0, 1)
        self.chaos.setSingleStep(0.05)
        self.chaos.setValue(0.5)
        self.seed = QSpinBox()
        self.seed.setRange(-2147483648, 2147483647)
        self.seed.setSpecialValueText("AUTO")
        self.seed.setValue(0)
        self.style = QComboBox()
        self.style.addItems(["dream", "glitch", "psychedelic", "ambient"])
        self.resolution = QComboBox()
        self.resolution.addItem("1920 × 1080", (1920, 1080))
        self.resolution.addItem("1280 × 720", (1280, 720))
        self.resolution.addItem("3840 × 2160", (3840, 2160))
        form.addRow("DURATION", self.duration)
        form.addRow("CHAOS", self.chaos)
        form.addRow("SEED", self.seed)
        form.addRow("STYLE", self.style)
        form.addRow("RESOLUTION", self.resolution)
        content.addWidget(settings, 0, 1)

        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumBlockCount(100)
        self.status.setPlaceholderText("READY. Select source material to begin.")
        content.addWidget(self.status, 1, 0, 1, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        content.addWidget(self.progress, 2, 0, 1, 2)

        self.generate = QPushButton("GENERATE VIDEO")
        self.generate.setObjectName("generate")
        self.generate.clicked.connect(self.start_generation)
        content.addWidget(self.generate, 3, 0, 1, 2)

        self.setCentralWidget(root)
        self.append_status("SYSTEM ONLINE // native Qt interface ready")

    def append_status(self, message):
        self.status.appendPlainText(message)

    def choose_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Orithet media folder")
        if folder:
            self.input_path.setText(folder)
            self.append_status(f"SOURCE LOCKED // {folder}")

    def choose_output(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Choose output video", self.output_path.text(), "MP4 video (*.mp4)"
        )
        if filename:
            self.output_path.setText(filename)

    def start_generation(self):
        input_folder = self.input_path.text().strip()
        output_path = self.output_path.text().strip()
        if not input_folder:
            QMessageBox.warning(self, "SOURCE REQUIRED", "Choose a media folder before generating.")
            return
        if not output_path:
            QMessageBox.warning(self, "OUTPUT REQUIRED", "Choose an output video path.")
            return

        seed = self.seed.value() or None
        resolution = self.resolution.currentData()
        self.generate.setEnabled(False)
        self.progress.show()
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
        self.generate.setEnabled(True)
        self.progress.hide()
        self.append_status(f"COMPLETE // rendered to {output_path}")
        QMessageBox.information(self, "ORITHET COMPLETE", f"Video rendered to:\n{output_path}")

    @Slot(str)
    def generation_failed(self, message):
        self.generate.setEnabled(True)
        self.progress.hide()
        self.append_status(f"ERROR // {message}")
        QMessageBox.critical(self, "GENERATION FAILED", message)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("Orithet")
    app.setOrganizationName("numbpill3d")
    window = OrithetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
