"""GUI Worker thread module for non-blocking execution of video-to-subtitle pipeline."""

import logging
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.orchestration.pipeline import run_pipeline
from src.schemas import WhisperModelSize

logger = logging.getLogger(__name__)


class PipelineProgressHandler(logging.Handler):
    """Custom logging handler to convert pipeline log messages into GUI progress & log signals."""

    def __init__(
        self,
        progress_signal: pyqtSignal,
        progress_signal_alt: Optional[pyqtSignal] = None,
        log_signal: Optional[pyqtSignal] = None,
    ) -> None:
        super().__init__()
        self.progress_signal = progress_signal
        self.progress_signal_alt = progress_signal_alt
        self.log_signal = log_signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            if self.log_signal:
                self.log_signal.emit(msg)

            percent = None
            stage = ""
            if "[Step 1/4]" in msg or "Extracting audio" in msg:
                percent, stage = 25, "Audio Extraction"
            elif "[Step 2/4]" in msg or "Transcribing audio" in msg:
                percent, stage = 50, "Transcription"
            elif "[Step 3/4]" in msg or "Starting LLM" in msg or "Processing LLM" in msg or "Correcting grammar" in msg:
                percent, stage = 75, "LLM Processing"
            elif "[Step 4/4]" in msg or "Generating SRT" in msg:
                percent, stage = 90, "SRT Generation"

            if percent is not None:
                self.progress_signal.emit(percent, stage)
                if self.progress_signal_alt:
                    self.progress_signal_alt.emit(percent, stage)
        except Exception:
            self.handleError(record)


QLogHandler = PipelineProgressHandler


class PipelineWorker(QThread):
    """QThread worker executing the video-to-subtitle pipeline asynchronously."""

    progress_updated = pyqtSignal(int, str)
    progress_changed = pyqtSignal(int, str)
    log_emitted = pyqtSignal(str)
    pipeline_finished = pyqtSignal(str)
    pipeline_error = pyqtSignal(str)

    def __init__(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        model_size: WhisperModelSize = "small",
        skip_grammar: bool = False,
        ollama_model: str = "llama3.2:3b",
        target_language: str = "English",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.output_path = output_path
        self.model_size = model_size
        self.skip_grammar = skip_grammar
        self.ollama_model = ollama_model
        self.target_language = target_language

    def run(self) -> None:
        """Execute the pipeline in a separate thread."""
        handler = PipelineProgressHandler(
            progress_signal=self.progress_updated,
            progress_signal_alt=self.progress_changed,
            log_signal=self.log_emitted,
        )
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            self.progress_updated.emit(5, "Initializing pipeline...")
            self.progress_changed.emit(5, "Initializing pipeline...")

            srt_path = run_pipeline(
                video_path=self.video_path,
                output_path=self.output_path,
                model_size=self.model_size,
                skip_grammar=self.skip_grammar,
                ollama_model=self.ollama_model,
                target_language=self.target_language,
            )
            self.progress_updated.emit(100, "Pipeline executed successfully!")
            self.progress_changed.emit(100, "Pipeline executed successfully!")
            self.pipeline_finished.emit(srt_path)
        except Exception as e:
            logger.exception("Error executing pipeline in PipelineWorker")
            self.pipeline_error.emit(str(e))
        finally:
            root_logger.removeHandler(handler)
