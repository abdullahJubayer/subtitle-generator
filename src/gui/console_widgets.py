"""Console widgets module providing Whisper log streaming, SRT editor views, and LLM telemetry/diff visualization."""

import logging
import re
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


def verify_srt_integrity(content: str) -> tuple[bool, str]:
    """Verify format and timestamp integrity of SRT subtitle content.

    Args:
        content: Raw SRT file text content.

    Returns:
        Tuple of (is_valid, status_message).
    """
    if not content or not content.strip():
        return False, "Empty content"

    lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    if not lines:
        return False, "No non-empty lines"

    ts_lines = [line for line in lines if "-->" in line]
    if not ts_lines:
        return False, "No timestamp arrows ('-->') found"

    from src.gui.player import timestamp_to_ms

    ts_pattern = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})$")
    valid_count = 0
    for line in ts_lines:
        m = ts_pattern.match(line)
        if m:
            start_ms = timestamp_to_ms(m.group(1))
            end_ms = timestamp_to_ms(m.group(2))
            if end_ms >= start_ms:
                valid_count += 1

    if valid_count == len(ts_lines):
        return True, f"{len(ts_lines)} subtitle segments intact"
    else:
        return False, f"Malformed timestamps ({valid_count}/{len(ts_lines)} valid)"


class WhisperConsoleWidget(QWidget):
    """Widget displaying telemetry header, search filter toolbar, and live Whisper segment streaming log area."""

    export_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._log_history: list[str] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Telemetry header QLabel
        self.telemetry_label = QLabel(
            "Detected Language: N/A | Prob: N/A | Duration: 0.0s | Model: N/A"
        )
        self.telemetry_label.setStyleSheet(
            "font-weight: bold; color: #89b4fa; padding: 6px; background-color: #181825; border-radius: 4px;"
        )
        layout.addWidget(self.telemetry_label)

        # Toolbar layout
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter log entries...")
        self.search_input.textChanged.connect(self._on_search_changed)

        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)

        self.export_button = QPushButton("Export Log")
        self.export_button.clicked.connect(self._on_export_clicked)

        toolbar_layout.addWidget(self.search_input, stretch=1)
        toolbar_layout.addWidget(self.clear_button)
        toolbar_layout.addWidget(self.export_button)
        layout.addLayout(toolbar_layout)

        # Log text area (QTextEdit)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Whisper transcription log stream...")
        layout.addWidget(self.log_area, stretch=1)

    @property
    def search_filter(self) -> QLineEdit:
        """Alias property for search filter input widget."""
        return self.search_input

    @property
    def log_edit(self) -> QTextEdit:
        """Alias property for log text edit area widget."""
        return self.log_area

    def update_telemetry(
        self, language: str, probability: float, duration: float, model_size: str
    ) -> None:
        """Update telemetry header with language, probability score, duration, and Whisper model size."""
        prob_str = f"{probability:.2f}" if isinstance(probability, (int, float)) else str(probability)
        dur_str = f"{duration:.2f}s" if isinstance(duration, (int, float)) else str(duration)
        text = f"Detected Language: {language} | Prob: {prob_str} | Duration: {dur_str} | Model: {model_size}"
        self.telemetry_label.setText(text)

    def append_log(self, text: str) -> None:
        """Append a log line to live streaming log text area."""
        self._log_history.append(text)
        query = self.search_input.text().strip().lower()
        if not query or query in text.lower():
            self.log_area.append(text)

    def clear_log(self) -> None:
        """Clear log history and reset text display area."""
        self._log_history.clear()
        self.log_area.clear()

    def get_log_text(self) -> str:
        """Return all logged text lines as a single string."""
        return "\n".join(self._log_history)

    def _on_search_changed(self, query: str) -> None:
        """Filter displayed log lines based on search query string."""
        query_str = query.strip().lower()
        if not query_str:
            filtered = self._log_history
        else:
            filtered = [line for line in self._log_history if query_str in line.lower()]
        self.log_area.setPlainText("\n".join(filtered))

    def export_log(self, file_path: str) -> bool:
        """Save current log content to file path and emit export_requested signal."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.get_log_text() or self.log_area.toPlainText())
            self.export_requested.emit(file_path)
            return True
        except Exception as e:
            logger.error("Failed to export log to '%s': %s", file_path, e)
            return False

    def _on_export_clicked(self) -> None:
        """Handle Export Log button click via QFileDialog."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            "whisper_log.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if save_path:
            self.export_log(save_path)


class SrtConsoleWidget(QWidget):
    """Widget providing formatted SRT text content editor and timestamp integrity status monitoring."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar layout
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(6)

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self._on_copy_clicked)

        self.save_button = QPushButton("Save .SRT File")
        self.save_button.clicked.connect(self._on_save_clicked)

        self.integrity_label = QLabel("Integrity: Status Unknown")
        self.integrity_label.setStyleSheet(
            "font-weight: bold; color: #a6adc8; padding: 6px; background-color: #181825; border-radius: 4px;"
        )

        toolbar_layout.addWidget(self.copy_button)
        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.integrity_label, stretch=1)
        layout.addLayout(toolbar_layout)

        # Editor text area (QTextEdit)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Formatted .srt content will appear here...")
        layout.addWidget(self.editor, stretch=1)

    @property
    def editor_area(self) -> QTextEdit:
        """Alias property for editor text area widget."""
        return self.editor

    def set_srt_content(self, content: str) -> None:
        """Set rendered formatted SRT text content in editor area and auto-check integrity."""
        self.editor.setPlainText(content)
        is_valid, msg = verify_srt_integrity(content)
        self.update_integrity_status(is_valid, msg)

    def get_srt_content(self) -> str:
        """Get text content from editor area."""
        return self.editor.toPlainText()

    def update_integrity_status(self, is_valid: bool, message: str) -> None:
        """Update timestamp integrity status label text and styling."""
        if is_valid:
            status_text = f"Integrity: Valid ✓ ({message})" if message else "Integrity: Valid ✓"
            color = "#a6e3a1"
        else:
            status_text = f"Integrity: Invalid ❌ ({message})" if message else "Integrity: Invalid ❌"
            color = "#f38ba8"

        self.integrity_label.setText(status_text)
        self.integrity_label.setStyleSheet(
            f"font-weight: bold; color: {color}; padding: 6px; background-color: #181825; border-radius: 4px;"
        )

    def _on_copy_clicked(self) -> None:
        """Copy editor text content to system clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.editor.toPlainText())

    def _on_save_clicked(self) -> None:
        """Save editor text content to .srt file using QFileDialog."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save .SRT Subtitle File",
            "subtitle.srt",
            "SubRip Subtitle Files (*.srt);;All Files (*)",
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
            except Exception as e:
                logger.error("Failed to save SRT file to '%s': %s", save_path, e)


class LlmConsoleWidget(QWidget):
    """Console widget for displaying LLM interaction telemetry, raw payloads/responses, and diffs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Telemetry Label: Provider, model, batch count, execution latency
        self.telemetry_label = QLabel("Provider: N/A | Model: N/A | Batch: N/A | Latency: N/A")
        self.telemetry_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px;")
        layout.addWidget(self.telemetry_label)

        # Splitter for JSON Payload/Response TextEdits and Diffs Table
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top Section: Side-by-side Payload & Response
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        payload_group = QGroupBox("Sent JSON Segment Payload")
        payload_layout = QVBoxLayout(payload_group)
        self.payload_edit = QTextEdit()
        self.payload_edit.setReadOnly(True)
        payload_layout.addWidget(self.payload_edit)

        response_group = QGroupBox("Raw LLM Response")
        response_layout = QVBoxLayout(response_group)
        self.response_edit = QTextEdit()
        self.response_edit.setReadOnly(True)
        response_layout.addWidget(self.response_edit)

        top_layout.addWidget(payload_group)
        top_layout.addWidget(response_group)
        splitter.addWidget(top_widget)

        # Bottom Section: Side-by-side translation diff table
        diff_group = QGroupBox("Side-by-Side Translation Diffs")
        diff_layout = QVBoxLayout(diff_group)
        self.diff_table = QTableWidget()
        self.diff_table.setColumnCount(2)
        self.diff_table.setHorizontalHeaderLabels(
            ["Original Speech", "Adapted/Translated Subtitle"]
        )
        header = self.diff_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        diff_layout.addWidget(self.diff_table)
        splitter.addWidget(diff_group)

        layout.addWidget(splitter)

    def update_llm_interaction(
        self,
        payload_json: str,
        response_json: str,
        provider: str,
        model_name: str,
        batch_info: str,
    ) -> None:
        """Update telemetry metadata label and raw payload/response text views."""
        self.payload_edit.setText(payload_json)
        self.response_edit.setText(response_json)
        self.telemetry_label.setText(
            f"Provider: {provider} | Model: {model_name} | {batch_info}"
        )

    def add_diff_rows(self, items: list[tuple[str, str]]) -> None:
        """Append original vs adapted translation diff pairs to table widget."""
        for orig, adapted in items:
            row = self.diff_table.rowCount()
            self.diff_table.insertRow(row)
            self.diff_table.setItem(row, 0, QTableWidgetItem(str(orig)))
            self.diff_table.setItem(row, 1, QTableWidgetItem(str(adapted)))

    def clear(self) -> None:
        """Reset widget state, clearing text edits and table rows."""
        self.payload_edit.clear()
        self.response_edit.clear()
        self.diff_table.setRowCount(0)
        self.telemetry_label.setText("Provider: N/A | Model: N/A | Batch: N/A | Latency: N/A")

    def on_llm_data_emitted(
        self,
        payload_json: str,
        response_json: str,
        provider: str,
        model_name: str,
        batch_info: str,
        diff_items: list[tuple[str, str]],
    ) -> None:
        """Slot receiver for worker thread llm_data_emitted signal."""
        self.update_llm_interaction(payload_json, response_json, provider, model_name, batch_info)
        self.add_diff_rows(diff_items)
