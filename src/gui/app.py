"""Main PyQt6 Application Window for Video-to-Subtitle AI Pipeline."""

import logging
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from PyQt6.QtCore import QThread, Qt, pyqtSignal
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.grammar_correction import get_available_gemini_models
from src.gui.console_widgets import (
    LlmConsoleWidget,
    SrtConsoleWidget,
    WhisperConsoleWidget,
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
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #11111b;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 6px 12px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}
"""


GEMINI_MODELS = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
PUTER_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet",
    "claude-3-haiku",
    "deepseek-chat",
    "gemini-1.5-flash",
]
DEFAULT_OLLAMA_MODELS = ["llama3.2:3b", "llama3.1", "mistral", "gemma2", "phi3"]


def _get_installed_ollama_models() -> list[str]:
    """Fetch installed local models from Ollama API."""
    default_models = DEFAULT_OLLAMA_MODELS
    try:
        import ollama
        resp = ollama.list()
        models = getattr(resp, "models", []) or (resp.get("models", []) if isinstance(resp, dict) else [])
        extracted = []
        for m in models:
            name = m.model if hasattr(m, "model") else (m.get("name", "") if isinstance(m, dict) else str(m))
            if name:
                extracted.append(name)
        return extracted if extracted else default_models
    except Exception:
        return default_models


class OllamaModelFetcherThread(QThread):
    """Background thread fetching local Ollama models without blocking GUI main looper thread."""

    models_fetched = pyqtSignal(list)

    def run(self) -> None:
        models = _get_installed_ollama_models()
        self.models_fetched.emit(models)


class SubtitleGeneratorApp(QMainWindow):
    """Main Window GUI Application for Video-to-Subtitle AI Generator."""

    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[PipelineWorker] = None
        self.selected_video_path: Optional[str] = None
        self._fetch_thread: Optional[OllamaModelFetcherThread] = None
        self._ollama_models: list[str] = list(DEFAULT_OLLAMA_MODELS)

        self.setWindowTitle("Video-to-Subtitle AI Pipeline")
        self.resize(1100, 720)
        self.setStyleSheet(DARK_QSS)

        self._init_ui()

    def _init_ui(self) -> None:
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

        # Target Language
        language_layout = QHBoxLayout()
        language_label = QLabel("Target Language:")
        language_label.setFixedWidth(120)
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "English",
            "Bangla (Bengali)",
            "Spanish",
            "French",
            "German",
            "Hindi",
            "Japanese",
            "Arabic",
            "Chinese",
            "Portuguese",
        ])
        self.language_combo.setCurrentText("English")
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        settings_layout.addLayout(language_layout)

        # Enable LLM Checkbox
        self.enable_llm_check = QCheckBox("Enable LLM Grammar Correction & Translation")
        self.enable_llm_check.setChecked(True)
        settings_layout.addWidget(self.enable_llm_check)

        # Container Widget for LLM Provider Selection
        self.provider_container = QWidget()
        provider_layout = QHBoxLayout(self.provider_container)
        provider_layout.setContentsMargins(0, 0, 0, 0)
        provider_label = QLabel("LLM Provider:")
        provider_label.setFixedWidth(120)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "Local (Ollama)",
            "Google Gemini (Cloud)",
            "Puter.js AI (Cloud)",
        ])
        self.provider_combo.setCurrentText("Local (Ollama)")
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_combo)
        settings_layout.addWidget(self.provider_container)

        # Container Widget for LLM Model Selection
        self.ollama_container = QWidget()
        ollama_layout = QHBoxLayout(self.ollama_container)
        ollama_layout.setContentsMargins(0, 0, 0, 0)
        self.model_label = QLabel("LLM Model:")
        self.model_label.setFixedWidth(120)
        self.ollama_combo = QComboBox()
        self.ollama_combo.setEditable(True)
        self.ollama_combo.addItems(self._ollama_models)
        self.ollama_combo.setCurrentText("llama3.2:3b")

        ollama_layout.addWidget(self.model_label)
        ollama_layout.addWidget(self.ollama_combo)
        settings_layout.addWidget(self.ollama_container)

        # Container Widget for API Key Field (Automated via .env)
        self.api_key_container = QWidget()
        api_key_layout = QHBoxLayout(self.api_key_container)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_label = QLabel("API Key:")
        api_key_label.setFixedWidth(120)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("PUTER_API_KEY") or ""
        if env_key:
            self.api_key_edit.setText(env_key)
        self.api_key_edit.setPlaceholderText("Loaded automatically from .env file")
        self.api_key_edit.textChanged.connect(self._on_api_key_changed)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_edit)
        # Note: self.api_key_container is intentionally NOT added to settings_layout to keep the UI clean.

        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.enable_llm_check.toggled.connect(self._update_llm_visibility)
        self._update_llm_visibility()

        # Offload dynamic model discovery to background QThread
        self._fetch_thread = OllamaModelFetcherThread(self)
        self._fetch_thread.models_fetched.connect(self._on_ollama_models_fetched)
        self._fetch_thread.start()

        left_layout.addWidget(settings_group)

        # 3. Action Controls
        self.start_button = QPushButton("🚀 Start Subtitle Pipeline")
        self.start_button.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #a6e3a1; color: #11111b;"
        )
        self.start_button.clicked.connect(self._on_start_pipeline)
        left_layout.addWidget(self.start_button)

        # 4. Progress Section & Consoles
        progress_group = QGroupBox("Progress & Consoles")
        progress_layout = QVBoxLayout(progress_group)

        self.stage_label = QLabel("Status: Idle")
        self.stage_label.setStyleSheet("font-weight: bold; color: #f5e0dc;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Console Tab Widget (Whisper Log, LLM Output, SRT Preview)
        self.console_tabs = QTabWidget()

        self.whisper_console = WhisperConsoleWidget()
        self.llm_console = LlmConsoleWidget()
        self.llm_console_widget = self.llm_console
        self.srt_console = SrtConsoleWidget()

        self.console_tabs.addTab(self.whisper_console, "🎙️ Whisper Log")
        self.console_tabs.addTab(self.llm_console, "🧠 LLM Telemetry & Diffs")
        self.console_tabs.addTab(self.srt_console, "📄 SRT Preview")

        self.log_console = self.whisper_console.log_area

        progress_layout.addWidget(self.stage_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.console_tabs)

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

        # Action bar for SRT download/export
        srt_action_layout = QHBoxLayout()
        self.export_button = QPushButton("💾 Export / Save .SRT File")
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.export_button.clicked.connect(self._on_export_srt)

        self.load_srt_button = QPushButton("📂 Load .SRT Subtitle File")
        self.load_srt_button.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.load_srt_button.clicked.connect(self._on_load_custom_srt)

        srt_action_layout.addWidget(self.export_button)
        srt_action_layout.addWidget(self.load_srt_button)
        right_layout.addLayout(srt_action_layout)

        # Add panels to split container
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
    def _on_provider_changed(self, index: int = 0) -> None:
        """Handler when LLM Provider selection changes."""
        provider_text = self.provider_combo.currentText()
        is_puter = "Puter" in provider_text
        is_gemini = "Gemini" in provider_text

        current_model = self.ollama_combo.currentText()
        self.ollama_combo.clear()
        if is_puter:
            self.ollama_combo.addItems(PUTER_MODELS)
            self.ollama_combo.setCurrentText("gpt-4o-mini")
        elif is_gemini:
            key = self.api_key_edit.text().strip() or os.environ.get("GEMINI_API_KEY")
            gemini_models = get_available_gemini_models(key)
            self.ollama_combo.addItems(gemini_models)
            if "gemini-2.5-flash" in gemini_models:
                self.ollama_combo.setCurrentText("gemini-2.5-flash")
            elif gemini_models:
                self.ollama_combo.setCurrentText(gemini_models[0])
        else:
            self.ollama_combo.addItems(self._ollama_models)
            if current_model in self._ollama_models:
                self.ollama_combo.setCurrentText(current_model)
            else:
                self.ollama_combo.setCurrentText("llama3.2:3b")

        self._update_llm_visibility()

    def _on_api_key_changed(self, text: str) -> None:
        """Handler when API key field text changes."""
        provider_text = self.provider_combo.currentText()
        if "Gemini" in provider_text:
            key = text.strip() or os.environ.get("GEMINI_API_KEY")
            gemini_models = get_available_gemini_models(key)
            current = self.ollama_combo.currentText()
            self.ollama_combo.clear()
            self.ollama_combo.addItems(gemini_models)
            if current in gemini_models:
                self.ollama_combo.setCurrentText(current)
            elif gemini_models:
                self.ollama_combo.setCurrentText(gemini_models[0])

    def _update_llm_visibility(self) -> None:
        """Dynamically update visibility of LLM setting fields based on toggle state."""
        llm_enabled = self.enable_llm_check.isChecked()

        self.provider_container.setVisible(llm_enabled)
        self.ollama_container.setVisible(llm_enabled)
        self.api_key_container.setVisible(False)

    def _on_ollama_models_fetched(self, models: list[str]) -> None:
        """Callback handling async background discovery of local Ollama models."""
        if not models:
            return
        self._ollama_models = models
        provider_text = self.provider_combo.currentText()
        if "Gemini" not in provider_text and "Puter" not in provider_text and "Cloud" not in provider_text:
            current = self.ollama_combo.currentText()
            self.ollama_combo.clear()
            self.ollama_combo.addItems(models)
            if current in models:
                self.ollama_combo.setCurrentText(current)
            elif "llama3.2:3b" in models:
                self.ollama_combo.setCurrentText("llama3.2:3b")
            else:
                self.ollama_combo.setEditText(current)

    def _on_browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm);;All Files (*)",
        )
        if file_path:
            self.selected_video_path = file_path
            self.file_path_edit.setText(file_path)

    @property
    def skip_grammar_check(self) -> object:
        """Backward compatibility property wrapper for skip_grammar_check."""
        class DummyCheck:
            def __init__(self, check): self._check = check
            def isChecked(self): return not self._check.isChecked()
            def setChecked(self, val): self._check.setChecked(not val)
            def setEnabled(self, val): self._check.setEnabled(val)
        return DummyCheck(self.enable_llm_check)

    @property
    def ollama_edit(self) -> object:
        """Backward compatibility property for tests querying ollama_edit."""
        class DummyEdit:
            def __init__(self, combo):
                self._combo = combo
            def text(self):
                return self._combo.currentText()
            def setText(self, text_val):
                idx = self._combo.findText(text_val)
                if idx >= 0:
                    self._combo.setCurrentIndex(idx)
                else:
                    self._combo.addItem(text_val)
                    self._combo.setCurrentText(text_val)
            def setEnabled(self, enabled):
                self._combo.setEnabled(enabled)
        return DummyEdit(self.ollama_combo)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable interactive UI controls during pipeline execution."""
        self.start_button.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.language_combo.setEnabled(enabled)
        self.enable_llm_check.setEnabled(enabled)
        self.provider_combo.setEnabled(enabled)
        self.ollama_combo.setEnabled(enabled)
        self.api_key_edit.setEnabled(enabled)
        if not enabled:
            self.start_button.setText("⏳ Pipeline Running...")
            self.start_button.setStyleSheet(
                "background-color: #45475a; color: #a6adc8; font-weight: bold; border-radius: 6px;"
            )
        else:
            self.start_button.setText("🚀 Start Subtitle Pipeline")
            self.start_button.setStyleSheet("")

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

        # Disable start button & controls, reset progress & logs
        self._set_controls_enabled(False)
        self.progress_bar.setValue(0)
        self.stage_label.setText("Status: Initializing...")
        self.log_console.clear()
        self.whisper_console.clear_log()
        self.llm_console.clear()
        self.srt_console.set_srt_content("")
        self._llm_warning_notice = None

        # Gather settings
        model_size = self.model_combo.currentText()
        target_language = self.language_combo.currentText()
        ollama_model = self.ollama_combo.currentText().strip() or "llama3.2:3b"
        skip_grammar = not self.enable_llm_check.isChecked()

        self.whisper_console.update_telemetry(
            language=target_language,
            probability=1.0,
            duration=0.0,
            model_size=model_size,
        )

        provider_text = self.provider_combo.currentText()
        if "Puter" in provider_text:
            llm_provider = "puter"
            api_key = self.api_key_edit.text().strip() or os.environ.get("PUTER_API_KEY")
        elif "Gemini" in provider_text or "Cloud" in provider_text:
            llm_provider = "gemini"
            api_key = self.api_key_edit.text().strip() or os.environ.get("GEMINI_API_KEY")
        else:
            llm_provider = "ollama"
            api_key = None

        # Spawn pipeline worker thread
        self.llm_console.clear()
        self.worker = PipelineWorker(
            video_path=video_path,
            model_size=model_size,
            skip_grammar=skip_grammar,
            ollama_model=ollama_model,
            target_language=target_language,
            llm_provider=llm_provider,
            api_key=api_key,
        )
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_emitted.connect(self._on_log_emitted)
        self.worker.llm_data_emitted.connect(self.llm_console.on_llm_data_emitted)
        self.worker.pipeline_finished.connect(
            lambda srt_path: self._on_pipeline_finished(video_path, srt_path)
        )
        self.worker.pipeline_error.connect(self._on_pipeline_error)

        self.worker.start()

    def _on_progress_updated(self, percent: int, stage_text: str):
        self.progress_bar.setValue(percent)
        self.stage_label.setText(f"Status: {stage_text}")

    def _on_log_emitted(self, msg: str):
        self.whisper_console.append_log(msg)
        if "Automatically switched" in msg or "Grammar correction failed" in msg:
            self._llm_warning_notice = msg

    def _on_pipeline_finished(self, video_path: str, srt_path: str):
        self._set_controls_enabled(True)
        self.progress_bar.setValue(100)
        self.stage_label.setText("Status: ✨ Pipeline Completed!")

        self.generated_srt_path = srt_path
        self.export_button.setEnabled(True)

        if srt_path and os.path.exists(srt_path):
            try:
                with open(srt_path, "r", encoding="utf-8") as f:
                    srt_content = f.read()
                self.srt_console.set_srt_content(srt_content)
            except Exception as e:
                logger.error("Failed to load SRT into SrtConsoleWidget: %s", e)

        # Enable Video Player widget, load video & generated .srt, and start playback automatically!
        self.video_player.setEnabled(True)
        self.video_player.load_video(video_path, srt_path)
        self.video_player.play()

        if getattr(self, "_llm_warning_notice", None):
            QMessageBox.warning(
                self,
                "⚠️ LLM Model Warning / Auto-Switch",
                f"{self._llm_warning_notice}\n\nSubtitles were generated successfully. You can select a different model in the LLM Model dropdown if desired.\n\nFile location: {srt_path}",
            )
        else:
            QMessageBox.information(
                self,
                "Pipeline Complete",
                f"✨ Subtitle generation complete!\n\nSubtitles auto-loaded into player.\nClick '💾 Export / Save .SRT File' to save it to your computer.\n\nFile location: {srt_path}",
            )

    def _on_export_srt(self) -> None:
        """Export/save the generated .srt file to user selected path."""
        if not hasattr(self, "generated_srt_path") or not self.generated_srt_path or not os.path.exists(self.generated_srt_path):
            QMessageBox.warning(
                self,
                "No Subtitle File",
                "No generated subtitle file is available to export.",
            )
            return

        default_name = os.path.basename(self.generated_srt_path)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Subtitle File",
            default_name,
            "SubRip Subtitle Files (*.srt);;All Files (*)",
        )
        if save_path:
            import shutil
            try:
                shutil.copy2(self.generated_srt_path, save_path)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Subtitle file saved successfully to:\n\n{save_path}",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to save subtitle file to target location:\n{e}",
                )

    def _on_load_custom_srt(self) -> None:
        """Load an external .srt subtitle file into the video player."""
        srt_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .SRT Subtitle File",
            "",
            "SubRip Subtitle Files (*.srt);;All Files (*)",
        )
        if srt_path:
            self.generated_srt_path = srt_path
            self.export_button.setEnabled(True)
            if os.path.exists(srt_path):
                try:
                    with open(srt_path, "r", encoding="utf-8") as f:
                        srt_content = f.read()
                    self.srt_console.set_srt_content(srt_content)
                except Exception as e:
                    logger.error("Failed to load custom SRT: %s", e)
            if self.selected_video_path and os.path.exists(self.selected_video_path):
                self.video_player.setEnabled(True)
                self.video_player.load_video(self.selected_video_path, srt_path)
                self.video_player.play()
            else:
                QMessageBox.information(
                    self,
                    "Subtitle Loaded",
                    f"Subtitle file loaded: {srt_path}\nSelect a video file to play video with subtitles.",
                )

    def _on_pipeline_error(self, error_msg: str) -> None:
        self._set_controls_enabled(True)
        self.stage_label.setText("Status: ❌ Error Encountered")
        QMessageBox.critical(
            self,
            "Pipeline Failure",
            f"The subtitle pipeline encountered a critical error:\n\n{error_msg}",
        )

    def closeEvent(self, event) -> None:
        """Gracefully handle window closing while worker threads are active."""
        if self._fetch_thread and self._fetch_thread.isRunning():
            self._fetch_thread.wait(1000)
        if self.worker and self.worker.isRunning():
            self.worker.wait(2000)
        event.accept()

