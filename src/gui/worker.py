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
    llm_data_emitted = pyqtSignal(str, str, str, str, str, list, str)
    segments_transcribed = pyqtSignal(list)

    def __init__(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        model_size: WhisperModelSize = "small",
        skip_grammar: bool = False,
        ollama_model: str = "llama3.2:3b",
        target_language: str = "English",
        llm_provider: str = "ollama",
        api_key: Optional[str] = None,
        audio_track: int = 0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.output_path = output_path
        self.model_size = model_size
        self.skip_grammar = skip_grammar
        self.ollama_model = ollama_model
        self.target_language = target_language
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.audio_track = audio_track

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
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

        def _llm_cb(
            payload_json: str,
            response_json: str,
            provider: str,
            model_name: str,
            batch_info: str,
            diff_items: list,
            prompt_system: str = "",
        ) -> None:
            self.llm_data_emitted.emit(
                payload_json, response_json, provider, model_name, batch_info, diff_items, prompt_system
            )

        def _tx_cb(segs: list) -> None:
            self.segments_transcribed.emit(segs)

        def _prog_cb(pct: float, msg: str) -> None:
            val = int(pct)
            self.progress_updated.emit(val, msg)
            self.progress_changed.emit(val, msg)

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
                llm_provider=self.llm_provider,
                api_key=self.api_key,
                audio_track=self.audio_track,
                llm_callback=_llm_cb,
                transcription_callback=_tx_cb,
                progress_callback=_prog_cb,
            )
            self.progress_updated.emit(100, "Pipeline executed successfully!")
            self.progress_changed.emit(100, "Pipeline executed successfully!")
            self.pipeline_finished.emit(srt_path)
        except Exception as e:
            logger.exception("Error executing pipeline in PipelineWorker")
            self.pipeline_error.emit(str(e))
        finally:
            root_logger.removeHandler(handler)


class SingleSegmentWorker(QThread):
    """QThread worker executing single-line segment translation asynchronously."""

    segment_finished = pyqtSignal(int, str, str)
    segment_error = pyqtSignal(int, str)
    llm_data_emitted = pyqtSignal(str, str, str, str, str, list, str)

    def __init__(
        self,
        segment: dict,
        model_name: str = "llama3.2:3b",
        target_language: str = "English",
        provider: str = "ollama",
        api_key: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.segment = segment
        self.model_name = model_name
        self.target_language = target_language
        self.provider = provider
        self.api_key = api_key

    def run(self) -> None:
        """Execute single-line translation in background thread."""
        def _llm_cb(
            payload_json: str,
            response_json: str,
            provider: str,
            model_name: str,
            batch_info: str,
            diff_items: list,
            prompt_system: str = "",
        ) -> None:
            self.llm_data_emitted.emit(
                payload_json, response_json, provider, model_name, batch_info, diff_items, prompt_system
            )

        try:
            seg_id = int(self.segment.get("id", 0))
            from src.grammar_correction.corrector import correct_single_segment

            translated = correct_single_segment(
                segment=self.segment,
                model_name=self.model_name,
                target_language=self.target_language,
                provider=self.provider,
                api_key=self.api_key,
                llm_callback=_llm_cb,
            )
            self.segment_finished.emit(seg_id, translated, "Translated")
        except Exception as e:
            logger.exception("Error executing single segment translation for segment %s", self.segment.get("id"))
            seg_id = int(self.segment.get("id", 0))
            self.segment_error.emit(seg_id, str(e))

