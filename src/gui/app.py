"""Main PyQt6 Application Window for Video-to-Subtitle AI Pipeline."""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.player import VideoPlayerWidget
from src.gui.worker import PipelineWorker

logger = logging.getLogger(__name__)

DARK_QSS = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #cdd6f4;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
    background-color: #181825;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
}
QLineEdit, QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}
QPushButton {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:pressed {
    background-color: #74c7ec;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #a6adc8;
}
QProgressBar {
    border: 1px solid #313244;
    border-radius: 6px;
    text-align: center;
    background-color: #313244;
    color: #cdd6f4;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #a6e3a1;
    border-radius: 5px;
}
QTextEdit {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #a6adc8;
    font-family: "Courier New", Courier, monospace;
    font-size: 12px;
}
QSplitter::handle {
    background-color: #313244;
    width: 4px;
}
QCheckBox {
    font-size: 13px;
    spacing: 8px;
}
"""


class SubtitleGeneratorApp(QMainWindow):
    """Main Window GUI Application for Video-to-Subtitle AI Generator."""

    def __init__(self):
        super().__init__()
        self.worker: Optional[PipelineWorker] = None
        self.selected_video_path: Optional[str] = None

        self.setWindowTitle("Video-to-Subtitle AI Pipeline")
        self.resize(1100, 720)
        self.setStyleSheet(DARK_QSS)

        self._init_ui()

    def _init_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(main_splitter)

        # Left Panel: Controls, Settings & Logs
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        # Header Title
        header_label = QLabel("🎬 Subtitle Generator AI")
        header_label.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #89b4fa; padding-bottom: 4px;"
        )
        left_layout.addWidget(header_label)

        # 1. File Selector Group
        file_group = QGroupBox("Input Video")
        file_layout = QHBoxLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a video file...")
        self.file_path_edit.setReadOnly(True)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_file)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_button)
        left_layout.addWidget(file_group)

        # 2. Settings Panel Group
        settings_group = QGroupBox("Pipeline Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)

        # Whisper Model
        whisper_layout = QHBoxLayout()
        whisper_label = QLabel("Whisper Model:")
        whisper_label.setFixedWidth(120)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("small")
        whisper_layout.addWidget(whisper_label)
        whisper_layout.addWidget(self.model_combo)
        settings_layout.addLayout(whisper_layout)

        # Ollama Model
        ollama_layout = QHBoxLayout()
        ollama_label = QLabel("Ollama Model:")
        ollama_label.setFixedWidth(120)
        self.ollama_edit = QLineEdit("llama3.1")
        ollama_layout.addWidget(ollama_label)
        ollama_layout.addWidget(self.ollama_edit)
        settings_layout.addLayout(ollama_layout)

        # Skip Grammar
        self.skip_grammar_check = QCheckBox("Skip LLM Grammar Correction")
        settings_layout.addWidget(self.skip_grammar_check)

        left_layout.addWidget(settings_group)

        # 3. Action Controls
        self.start_button = QPushButton("🚀 Start Subtitle Pipeline")
        self.start_button.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #a6e3a1; color: #11111b;"
        )
        self.start_button.clicked.connect(self._on_start_pipeline)
        left_layout.addWidget(self.start_button)

        # 4. Progress Section
        progress_group = QGroupBox("Progress & Status")
        progress_layout = QVBoxLayout(progress_group)

        self.stage_label = QLabel("Status: Idle")
        self.stage_label.setStyleSheet("font-weight: bold; color: #f5e0dc;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Console logs will appear here...")

        progress_layout.addWidget(self.stage_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.log_console)

        left_layout.addWidget(progress_group, stretch=1)

        # Right Panel: Video Preview Section
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(16, 16, 16, 16)

        preview_header = QLabel("📺 Video Preview & Subtitles")
        preview_header.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #89b4fa; padding-bottom: 4px;"
        )
        right_layout.addWidget(preview_header)

        self.video_player = VideoPlayerWidget()
        self.video_player.setEnabled(False)
        right_layout.addWidget(self.video_player, stretch=1)

        # Add panels to split container
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([480, 620])

    def _on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm);;All Files (*)",
        )
        if file_path:
            self.selected_video_path = file_path
            self.file_path_edit.setText(file_path)

    def _on_start_pipeline(self):
        video_path = self.file_path_edit.text().strip()
        if not video_path:
            QMessageBox.warning(
                self,
                "No Input File",
                "Please select a valid video file before starting the pipeline.",
            )
            return

        if not os.path.exists(video_path):
            QMessageBox.critical(
                self,
                "File Not Found",
                f"The specified input file does not exist:\n{video_path}",
            )
            return

        # Disable start button & reset status
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.stage_label.setText("Status: Initializing...")
        self.log_console.clear()

        # Gather settings
        model_size = self.model_combo.currentText()
        ollama_model = self.ollama_edit.text().strip() or "llama3.1"
        skip_grammar = self.skip_grammar_check.isChecked()

        # Spawn pipeline worker thread
        self.worker = PipelineWorker(
            video_path=video_path,
            model_size=model_size,
            skip_grammar=skip_grammar,
            ollama_model=ollama_model,
        )
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_emitted.connect(self._on_log_emitted)
        self.worker.pipeline_finished.connect(
            lambda srt_path: self._on_pipeline_finished(video_path, srt_path)
        )
        self.worker.pipeline_error.connect(self._on_pipeline_error)

        self.worker.start()

    def _on_progress_updated(self, percent: int, stage_text: str):
        self.progress_bar.setValue(percent)
        self.stage_label.setText(f"Status: {stage_text}")

    def _on_log_emitted(self, msg: str):
        self.log_console.append(msg)

    def _on_pipeline_finished(self, video_path: str, srt_path: str):
        self.start_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.stage_label.setText("Status: ✨ Pipeline Completed!")

        # Enable Video Player widget, load video & generated .srt, and start playback automatically!
        self.video_player.setEnabled(True)
        self.video_player.load_video(video_path, srt_path)
        self.video_player.play()

    def _on_pipeline_error(self, error_msg: str):
        self.start_button.setEnabled(True)
        self.stage_label.setText("Status: ❌ Error Encountered")
        QMessageBox.critical(
            self,
            "Pipeline Failure",
            f"The subtitle pipeline encountered a critical error:\n\n{error_msg}",
        )
