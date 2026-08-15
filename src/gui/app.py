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
    QStackedWidget,
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
from src.gui.subtitle_table import InteractiveSubtitleTableWidget
from src.gui.worker import PipelineWorker, SingleSegmentWorker

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


GEMINI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-3.1-pro-preview"]
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
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(12, 12, 12, 12)
        central_layout.setSpacing(10)
        self.setCentralWidget(central_widget)

        # Step Navigation Bar at top
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        self.btn_step1 = QPushButton("1. Setup & Pipeline")
        self.btn_step1.setStyleSheet(
            "font-weight: bold; padding: 6px 14px; border-radius: 6px; background-color: #313244; color: #89b4fa;"
        )
        self.btn_step1.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        self.btn_step2 = QPushButton("2. Line Conversion Studio")
        self.btn_step2.setStyleSheet(
            "font-weight: bold; padding: 6px 14px; border-radius: 6px; background-color: #313244; color: #a6adc8;"
        )
        self.btn_step2.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        self.btn_step3 = QPushButton("3. Video Player & Export")
        self.btn_step3.setStyleSheet(
            "font-weight: bold; padding: 6px 14px; border-radius: 6px; background-color: #313244; color: #a6adc8;"
        )
        self.btn_step3.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        nav_bar.addWidget(self.btn_step1)
        nav_bar.addWidget(self.btn_step2)
        nav_bar.addWidget(self.btn_step3)
        nav_bar.addStretch(1)
        central_layout.addLayout(nav_bar)

        self.stack = QStackedWidget()
        self.stack.currentChanged.connect(self._on_stage_changed)
        central_layout.addWidget(self.stack, stretch=1)

        # ----------------------------------------------------
        # PAGE 0: Setup & Pipeline Settings Page
        # ----------------------------------------------------
        page_setup = QWidget()
        setup_layout = QHBoxLayout(page_setup)
        setup_layout.setContentsMargins(0, 0, 0, 0)

        setup_left = QWidget()
        setup_left_layout = QVBoxLayout(setup_left)
        setup_left_layout.setContentsMargins(8, 8, 8, 8)
        setup_left_layout.setSpacing(10)

        # Header Title
        header_label = QLabel("Subtitle Generator AI")
        header_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #89b4fa; padding-bottom: 4px;"
        )
        setup_left_layout.addWidget(header_label)

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
        setup_left_layout.addWidget(file_group)

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

        # Audio Track Selector (Visible when multiple audio streams exist)
        self.audio_track_container = QWidget()
        audio_track_layout = QHBoxLayout(self.audio_track_container)
        audio_track_layout.setContentsMargins(0, 0, 0, 0)
        audio_track_label = QLabel("Audio Track:")
        audio_track_label.setFixedWidth(120)
        self.audio_track_combo = QComboBox()
        self.audio_track_combo.addItems(["Track 1: Default Audio Stream"])
        audio_track_layout.addWidget(audio_track_label)
        audio_track_layout.addWidget(self.audio_track_combo)
        self.audio_track_container.setVisible(False)
        settings_layout.addWidget(self.audio_track_container)

        # Enable LLM Checkbox
        self.enable_llm_check = QCheckBox("Enable LLM Grammar Correction & Translation")
        self.enable_llm_check.setChecked(True)
        settings_layout.addWidget(self.enable_llm_check)

        # Container Widget for LLM Provider Selection (Off-layout; per-row selection used in Studio Table)
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

        # Container Widget for LLM Model Selection (Off-layout; per-row selection used in Studio Table)
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

        # Container Widget for API Key Field
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

        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.enable_llm_check.toggled.connect(self._update_llm_visibility)
        self._update_llm_visibility()

        # Offload dynamic model discovery
        self._fetch_thread = OllamaModelFetcherThread(self)
        self._fetch_thread.models_fetched.connect(self._on_ollama_models_fetched)
        self._fetch_thread.start()

        setup_left_layout.addWidget(settings_group)

        # 3. Action Controls
        self.start_button = QPushButton("Start Subtitle Pipeline")
        self.start_button.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 6px;"
        )
        self.start_button.clicked.connect(self._on_start_pipeline)
        setup_left_layout.addWidget(self.start_button)

        # Progress Section
        progress_group = QGroupBox("Pipeline Status")
        progress_layout = QVBoxLayout(progress_group)

        self.stage_label = QLabel("Status: Idle")
        self.stage_label.setStyleSheet("font-weight: bold; color: #f5e0dc;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.stage_label)
        progress_layout.addWidget(self.progress_bar)
        setup_left_layout.addWidget(progress_group)

        # Console Tab Widget for Setup Page (Whisper Log, LLM Output, SRT Preview)
        self.console_tabs = QTabWidget()

        self.whisper_console = WhisperConsoleWidget()
        self.llm_console = LlmConsoleWidget()
        self.llm_console_widget = self.llm_console
        self.srt_console = SrtConsoleWidget()

        self.console_tabs.addTab(self.whisper_console, "Whisper Log")
        self.console_tabs.addTab(self.llm_console, "LLM Telemetry & Diffs")
        self.console_tabs.addTab(self.srt_console, "SRT Preview")

        self.log_console = self.whisper_console.log_area

        # Right side setup logs & consoles
        setup_right = QWidget()
        setup_right_layout = QVBoxLayout(setup_right)
        setup_right_layout.setContentsMargins(8, 8, 8, 8)
        setup_right_layout.addWidget(self.console_tabs)

        setup_layout.addWidget(setup_left, stretch=1)
        setup_layout.addWidget(setup_right, stretch=1)
        self.stack.addWidget(page_setup)

        # ----------------------------------------------------
        # PAGE 1: Full Screen Dedicated Interactive Studio Page
        # ----------------------------------------------------
        page_studio = QWidget()
        studio_layout = QVBoxLayout(page_studio)
        studio_layout.setContentsMargins(12, 12, 12, 12)
        studio_layout.setSpacing(10)

        studio_header_layout = QHBoxLayout()
        studio_header = QLabel("Interactive Line-by-Line Subtitle Studio")
        studio_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa;")

        self.build_srt_top_btn = QPushButton("Build & Load .SRT")
        self.build_srt_top_btn.setStyleSheet(
            "background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 6px;"
        )
        self.build_srt_top_btn.clicked.connect(self._on_build_and_load_srt)

        studio_header_layout.addWidget(studio_header)
        studio_header_layout.addStretch(1)
        studio_header_layout.addWidget(self.build_srt_top_btn)
        studio_layout.addLayout(studio_header_layout)

        # Prominent Studio Table occupying full screen area
        self.studio_table = InteractiveSubtitleTableWidget()
        self.studio_table.convert_requested.connect(self._on_single_convert_requested)
        self.studio_table.convert_all_requested.connect(self._on_convert_all_requested)
        self.studio_table.segments_changed.connect(self._on_studio_segments_changed)
        studio_layout.addWidget(self.studio_table, stretch=1)

        # Bottom Bar: Large Build & Load .SRT action button
        studio_bottom_layout = QHBoxLayout()
        self.build_srt_btn = QPushButton("Build & Load .SRT into Player")
        self.build_srt_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; background-color: #a6e3a1; color: #11111b; padding: 12px 24px; border-radius: 6px;"
        )
        self.build_srt_btn.clicked.connect(self._on_build_and_load_srt)
        studio_bottom_layout.addStretch(1)
        studio_bottom_layout.addWidget(self.build_srt_btn)
        studio_bottom_layout.addStretch(1)
        studio_layout.addLayout(studio_bottom_layout)

        self.stack.addWidget(page_studio)

        # ----------------------------------------------------
        # PAGE 2: Video Player & Subtitle Review Page
        # ----------------------------------------------------
        page_player = QWidget()
        player_layout = QVBoxLayout(page_player)
        player_layout.setContentsMargins(12, 12, 12, 12)
        player_layout.setSpacing(10)

        player_header_layout = QHBoxLayout()
        player_header = QLabel("Video Subtitle Player & Preview")
        player_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa;")

        self.back_to_studio_btn = QPushButton("Back to Line Studio")
        self.back_to_studio_btn.setStyleSheet(
            "background-color: #313244; color: #89b4fa; font-weight: bold; padding: 6px 14px; border-radius: 6px;"
        )
        self.back_to_studio_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        player_header_layout.addWidget(player_header)
        player_header_layout.addStretch(1)
        player_header_layout.addWidget(self.back_to_studio_btn)
        player_layout.addLayout(player_header_layout)

        self.video_player = VideoPlayerWidget()
        self.video_player.setEnabled(False)
        player_layout.addWidget(self.video_player, stretch=1)

        # Action bar for SRT download/export
        srt_action_layout = QHBoxLayout()
        self.export_button = QPushButton("Export / Save .SRT File")
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.export_button.clicked.connect(self._on_export_srt)

        self.load_srt_button = QPushButton("Load .SRT Subtitle File")
        self.load_srt_button.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.load_srt_button.clicked.connect(self._on_load_custom_srt)

        srt_action_layout.addWidget(self.export_button)
        srt_action_layout.addWidget(self.load_srt_button)
        player_layout.addLayout(srt_action_layout)

        self.stack.addWidget(page_player)
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
            gemini_models = get_available_gemini_models(key) or []
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
            gemini_models = get_available_gemini_models(key) or []
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
        self.ollama_models = models
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

        # Dynamically fetch live Gemini & Puter models using environment / API keys
        from src.grammar_correction.llm_providers import get_available_gemini_models, get_available_puter_models
        api_key = self.api_key_edit.text().strip() or os.environ.get("GEMINI_API_KEY")
        gemini_models = get_available_gemini_models(api_key=api_key)
        puter_models = get_available_puter_models(api_key=os.environ.get("PUTER_API_KEY"))

        # Build dynamic per-row model list for studio table
        model_options = []
        for m in models:
            model_options.append(("ollama", m, f"Ollama: {m}"))

        for g_mod in gemini_models:
            display_name = g_mod.replace("gemini-", "")
            model_options.append(("gemini", g_mod, f"Gemini: {display_name}"))

        for p_mod in puter_models:
            model_options.append(("puter", p_mod, f"Puter: {p_mod}"))

        self.studio_table.set_available_models(model_options)

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
            self._inspect_audio_tracks(file_path)

    def _inspect_audio_tracks(self, video_path: str) -> None:
        """Inspect video file audio streams and populate audio track selector if multiple streams exist."""
        if not video_path or not os.path.exists(video_path):
            self.audio_track_container.setVisible(False)
            return

        from src.audio_extraction.extractor import get_audio_tracks
        tracks = get_audio_tracks(video_path)
        self.audio_track_combo.clear()

        if len(tracks) > 1:
            for t in tracks:
                self.audio_track_combo.addItem(t["label"])
            self.audio_track_container.setVisible(True)
            self.whisper_console.append_log(
                f"[Audio Inspector] 🎵 Detected {len(tracks)} audio streams in video! Showing track selection."
            )
        elif len(tracks) == 1:
            self.audio_track_combo.addItem(tracks[0]["label"])
            self.audio_track_container.setVisible(False)
        else:
            self.audio_track_combo.addItem("Track 1: Default Audio Stream")
            self.audio_track_container.setVisible(False)

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
            self.start_button.setText("⏳ Processing Subtitles...")
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

        audio_track = self.audio_track_combo.currentIndex() if self.audio_track_combo.count() > 0 else 0
        if audio_track < 0:
            audio_track = 0

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
            audio_track=audio_track,
        )
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_emitted.connect(self._on_log_emitted)
        self.worker.llm_data_emitted.connect(self.llm_console.on_llm_data_emitted)
        self.worker.segments_transcribed.connect(self._on_segments_transcribed)
        self.worker.pipeline_finished.connect(
            lambda srt_path: self._on_pipeline_finished(video_path, srt_path)
        )
        self.worker.pipeline_error.connect(self._on_pipeline_error)

        self.worker.start()

    def _on_stage_changed(self, index: int) -> None:
        """Update stage navigation button styles when active page changes."""
        buttons = [self.btn_step1, self.btn_step2, self.btn_step3]
        for idx, btn in enumerate(buttons):
            if idx == index:
                btn.setStyleSheet(
                    "font-weight: bold; padding: 6px 14px; border-radius: 6px; background-color: #89b4fa; color: #11111b;"
                )
            else:
                btn.setStyleSheet(
                    "font-weight: bold; padding: 6px 14px; border-radius: 6px; background-color: #313244; color: #a6adc8;"
                )

    def _on_segments_transcribed(self, segments: list[dict]) -> None:
        """Handle raw Whisper transcription completion signal and populate Stage 1 Studio table."""
        self.studio_table.load_segments(segments)
        self.stack.setCurrentIndex(1)  # Automatically switch to Stage 1: Full-Screen Interactive Studio!

    def _on_build_final_srt(self) -> None:
        """Handle 'Build Final Subtitle & Play Video' button click in Stage 1 Studio."""
        active_segs = self.studio_table.get_active_segments()
        if not active_segs:
            QMessageBox.warning(self, "No Segments", "No subtitle segments available to build SRT.")
            return

        from src.srt_generation.generator import generate_srt_content
        srt_content = generate_srt_content(active_segs)
        self.srt_console.set_srt_content(srt_content)

    def _on_build_and_load_srt(self) -> None:
        """Build final .srt file from active Studio segments, load into Video Player, and switch to Player view."""
        active_segs = self.studio_table.get_active_segments()
        if not active_segs:
            QMessageBox.warning(
                self,
                "No Subtitle Segments",
                "No subtitle segments available to build .SRT file.",
            )
            return

        from src.srt_generation.generator import generate_srt_content
        srt_content = generate_srt_content(active_segs)
        self.srt_console.set_srt_content(srt_content)

        if self.selected_video_path and os.path.exists(self.selected_video_path):
            import tempfile
            with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".srt", encoding="utf-8") as f:
                f.write(srt_content)
                temp_srt = f.name
            self.generated_srt_path = temp_srt
            self.export_button.setEnabled(True)
            self.video_player.setEnabled(True)
            self.video_player.load_video(self.selected_video_path, temp_srt)
            self.video_player.play()

        self.stack.setCurrentIndex(2)  # Automatically switch to Stage 3: Full Screen Video Player & Export!

    def _on_single_convert_requested(
        self,
        seg_id: int,
        segment: dict,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        is_batch: bool = False,
        on_complete_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Handle single segment line conversion request via SingleSegmentWorker."""
        self.studio_table.set_segment_translating(seg_id)
        target_language = self.language_combo.currentText()

        if not provider or not model_name:
            provider_text = self.provider_combo.currentText()
            if "Puter" in provider_text:
                llm_provider = "puter"
            elif "Gemini" in provider_text or "Cloud" in provider_text:
                llm_provider = "gemini"
            else:
                llm_provider = "ollama"
            ollama_model = self.ollama_combo.currentText().strip() or "llama3.2:3b"
        else:
            llm_provider = provider
            ollama_model = model_name

        if llm_provider == "puter":
            api_key = self.api_key_edit.text().strip() or os.environ.get("PUTER_API_KEY")
        elif llm_provider == "gemini":
            api_key = self.api_key_edit.text().strip() or os.environ.get("GEMINI_API_KEY")
        else:
            api_key = None

        worker = SingleSegmentWorker(
            segment=segment,
            model_name=ollama_model,
            target_language=target_language,
            provider=llm_provider,
            api_key=api_key,
            parent=self,
        )

        def _on_finish(sid: int, text: str, status: str) -> None:
            model_label = f"{llm_provider.capitalize()}: {ollama_model}"
            self.studio_table.update_segment_translation(sid, text, model_label)
            if is_batch and hasattr(self, "_convert_all_pending") and self._convert_all_pending > 0:
                self._convert_all_pending -= 1
                completed = getattr(self, "_convert_all_total", 0) - self._convert_all_pending
                self.studio_table.set_convert_all_running(True, current=completed, total=getattr(self, "_convert_all_total", 0))
                if self._convert_all_pending == 0:
                    self.studio_table.set_convert_all_running(False)
            if on_complete_callback:
                on_complete_callback()

        def _on_err(sid: int, err: str) -> None:
            self.studio_table.update_segment_translation(sid, segment.get("text", ""), "Error")
            if is_batch and hasattr(self, "_convert_all_pending") and self._convert_all_pending > 0:
                self._convert_all_pending -= 1
                completed = getattr(self, "_convert_all_total", 0) - self._convert_all_pending
                self.studio_table.set_convert_all_running(True, current=completed, total=getattr(self, "_convert_all_total", 0))
                if self._convert_all_pending == 0:
                    self.studio_table.set_convert_all_running(False)
            if on_complete_callback:
                on_complete_callback()

        worker.segment_finished.connect(_on_finish)
        worker.segment_error.connect(_on_err)
        worker.start()

    def _on_convert_all_requested(self) -> None:
        """Handle Convert All Lines toolbar button click: executes controlled parallel concurrent conversions."""
        active_segs = self.studio_table.get_active_segments()
        if not active_segs:
            return

        total = len(active_segs)
        max_workers = self.studio_table.get_max_concurrency()
        self._convert_all_total = total
        self._convert_all_pending = total
        self._active_worker_count = 0
        self.studio_table.set_convert_all_running(True, current=0, total=total)

        queue = list(active_segs)

        def dispatch_next() -> None:
            while queue and getattr(self, "_active_worker_count", 0) < max_workers:
                seg = queue.pop(0)
                seg_id = int(seg["id"])
                prov, mod = self.studio_table.get_row_selected_model(seg_id)
                self._active_worker_count = getattr(self, "_active_worker_count", 0) + 1
                self._on_single_convert_requested(
                    seg_id, seg, provider=prov, model_name=mod, is_batch=True, on_complete_callback=on_worker_complete
                )

        def on_worker_complete() -> None:
            self._active_worker_count = max(0, getattr(self, "_active_worker_count", 1) - 1)
            dispatch_next()

        dispatch_next()

    def _on_studio_segments_changed(self) -> None:
        """Auto-update SRT preview console whenever interactive table changes."""
        active_segs = self.studio_table.get_active_segments()
        if not active_segs:
            return
        from src.srt_generation.generator import generate_srt_content
        srt_content = generate_srt_content(active_segs)
        self.srt_console.set_srt_content(srt_content)

    def _on_progress_updated(self, percent: int, stage_text: str):
        self.progress_bar.setValue(percent)
        self.stage_label.setText(f"Status: {stage_text}")

    def _on_log_emitted(self, msg: str):
        self.whisper_console.append_log(msg)
        if "[Whisper Progress]" in msg:
            parts = msg.split("[Whisper Progress]")
            if len(parts) > 1:
                clean_msg = parts[1].strip()
                self.stage_label.setText(f"Status: {clean_msg}")
                if "%" in clean_msg:
                    try:
                        pct_str = clean_msg.split("%")[0].split("-")[-1].strip()
                        pct_val = float(pct_str)
                        overall_pct = int(20.0 + (pct_val * 0.70))
                        self.progress_bar.setValue(overall_pct)
                    except Exception:
                        pass
        elif "Automatically switched" in msg or "Grammar correction failed" in msg:
            self._llm_warning_notice = msg

    def _on_pipeline_finished(self, video_path: str, srt_path: str):
        self._set_controls_enabled(True)
        self.progress_bar.setValue(100)
        self.stage_label.setText("Status: Pipeline Completed!")

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
                "LLM Model Warning / Auto-Switch",
                f"{self._llm_warning_notice}\n\nSubtitles were generated successfully. You can select a different model in the LLM Model dropdown if desired.\n\nFile location: {srt_path}",
            )
        else:
            QMessageBox.information(
                self,
                "Pipeline Complete",
                f"Subtitle generation complete!\n\nSubtitles auto-loaded into player.\nClick 'Export / Save .SRT File' to save it to your computer.\n\nFile location: {srt_path}",
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
        self.stage_label.setText("Status: Error Encountered")
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

