"""Interactive Subtitle Studio Table widget with per-line Convert, Revert, and cell editing capabilities."""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.srt_generation.generator import format_timestamp

logger = logging.getLogger(__name__)


DEFAULT_MODEL_OPTIONS: list[tuple[str, str, str]] = [
    ("ollama", "llama3.2:3b", "Ollama: llama3.2:3b"),
    ("ollama", "translategemma:4b", "Ollama: translategemma:4b"),
    ("gemini", "gemini-2.5-flash", "Gemini: 2.5-flash"),
    ("gemini", "gemini-2.0-flash", "Gemini: 2.0-flash"),
    ("gemini", "gemini-2.0-flash-lite", "Gemini: 2.0-flash-lite"),
    ("gemini", "gemini-1.5-flash", "Gemini: 1.5-flash"),
    ("gemini", "gemini-1.5-pro", "Gemini: 1.5-pro"),
    ("gemini", "gemini-1.5-flash-8b", "Gemini: 1.5-flash-8b"),
    ("gemini", "gemini-flash-latest", "Gemini: flash-latest"),
    ("puter", "gpt-4o-mini", "Puter: gpt-4o-mini"),
    ("puter", "gpt-4o", "Puter: gpt-4o"),
    ("puter", "claude-3-5-sonnet", "Puter: claude-3-5-sonnet"),
    ("puter", "claude-3-haiku", "Puter: claude-3-haiku"),
    ("puter", "deepseek-chat", "Puter: deepseek-chat"),
]


class SegmentActionWidget(QWidget):
    """Custom cell widget holding per-row Model Combo, [Convert] and [Revert] action buttons."""

    convert_clicked = pyqtSignal(int, str, str)  # (segment_id, provider, model_name)
    revert_clicked = pyqtSignal(int)

    def __init__(
        self,
        segment_id: int,
        available_models: Optional[list[tuple[str, str, str]]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.segment_id = segment_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Select LLM Provider & Model for converting this line")
        self.model_combo.setStyleSheet("font-size: 10px; padding: 2px 4px;")
        self.update_available_models(available_models)

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setToolTip("Translate or correct ONLY this segment line via selected LLM model")
        self.convert_btn.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; font-size: 11px; padding: 4px 8px; border-radius: 4px;"
        )
        self.convert_btn.clicked.connect(self._on_convert_clicked)

        self.revert_btn = QPushButton("Revert")
        self.revert_btn.setToolTip("Revert this segment back to original raw Whisper text")
        self.revert_btn.setStyleSheet(
            "background-color: #45475a; color: #cdd6f4; font-size: 11px; padding: 4px 8px; border-radius: 4px;"
        )
        self.revert_btn.setEnabled(False)
        self.revert_btn.clicked.connect(lambda: self.revert_clicked.emit(self.segment_id))

        layout.addWidget(self.model_combo, stretch=1)
        layout.addWidget(self.convert_btn)
        layout.addWidget(self.revert_btn)

    def _on_convert_clicked(self) -> None:
        provider, model_name = self.get_selected_provider_and_model()
        self.convert_clicked.emit(self.segment_id, provider, model_name)

    def get_selected_provider_and_model(self) -> tuple[str, str]:
        data = self.model_combo.currentData()
        if data and isinstance(data, tuple) and len(data) == 2:
            return data[0], data[1]
        text = self.model_combo.currentText()
        if "Gemini" in text:
            return "gemini", "gemini-1.5-flash"
        elif "Puter" in text:
            return "puter", "gpt-4o-mini"
        return "ollama", text.replace("Ollama: ", "").strip()

    def update_available_models(
        self, available_models: Optional[list[tuple[str, str, str]]] = None
    ) -> None:
        current_data = self.model_combo.currentData()
        self.model_combo.clear()
        models = available_models or DEFAULT_MODEL_OPTIONS
        for provider, model_name, label in models:
            self.model_combo.addItem(label, (provider, model_name))

        if current_data:
            idx = self.model_combo.findData(current_data)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def set_translating(self, is_translating: bool) -> None:
        """Toggle button state while line is translating."""
        self.convert_btn.setEnabled(not is_translating)
        self.model_combo.setEnabled(not is_translating)
        if is_translating:
            self.convert_btn.setText("Converting...")
        else:
            self.convert_btn.setText("Convert")

    def set_revert_enabled(self, enabled: bool) -> None:
        """Enable or disable [Revert] button."""
        self.revert_btn.setEnabled(enabled)


class InteractiveSubtitleTableWidget(QWidget):
    """Interactive Subtitle Studio Table widget displaying Whisper segments with line-by-line controls."""

    convert_requested = pyqtSignal(int, dict, str, str)  # (segment_id, seg_dict, provider, model_name)
    revert_requested = pyqtSignal(int)
    segments_changed = pyqtSignal()
    convert_all_requested = pyqtSignal()
    revert_all_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._raw_segments: list[dict] = []
        self._row_map: dict[int, int] = {}  # segment_id -> row index
        self._available_models: list[tuple[str, str, str]] = list(DEFAULT_MODEL_OPTIONS)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.info_label = QLabel("Interactive Subtitle Studio: Review and convert line by line")
        self.info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px;")

        self.convert_all_btn = QPushButton("Convert All Lines")
        self.convert_all_btn.setStyleSheet(
            "background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 6px 12px; border-radius: 6px;"
        )
        self.convert_all_btn.clicked.connect(self.convert_all_requested.emit)

        self.revert_all_btn = QPushButton("Revert All")
        self.revert_all_btn.setStyleSheet(
            "background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 6px 12px; border-radius: 6px;"
        )
        self.revert_all_btn.clicked.connect(self.revert_all_segments)

        self.concurrency_combo = QComboBox()
        self.concurrency_combo.addItems([
            "4 Workers (Default)",
            "2 Workers",
            "8 Workers",
            "16 Workers",
        ])
        self.concurrency_combo.setToolTip("Select number of parallel concurrent calls for batch line conversion")
        self.concurrency_combo.setStyleSheet("padding: 4px 8px; font-size: 11px;")

        toolbar.addWidget(self.info_label, stretch=1)
        toolbar.addWidget(QLabel("Parallel Calls:"))
        toolbar.addWidget(self.concurrency_combo)
        toolbar.addWidget(self.convert_all_btn)
        toolbar.addWidget(self.revert_all_btn)
        layout.addLayout(toolbar)

        # Subtitle Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "#",
            "Timestamp",
            "Raw Speech (Whisper)",
            "Active Subtitle Text (Editable)",
            "Status / Model",
            "Actions & Model Selector",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 280)

        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, stretch=1)

    def set_available_models(self, models: list[tuple[str, str, str]]) -> None:
        """Update available LLM models for per-row conversion dropdowns."""
        self._available_models = models
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 5)
            if isinstance(widget, SegmentActionWidget):
                widget.update_available_models(models)

    def load_segments(self, segments: list[dict]) -> None:
        """Load raw Whisper segments into interactive table view."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._raw_segments = [dict(s) for s in segments]
        self._row_map.clear()

        for idx, seg in enumerate(segments):
            seg_id = int(seg["id"])
            start_fmt = format_timestamp(float(seg["start"]))
            end_fmt = format_timestamp(float(seg["end"]))
            ts_text = f"{start_fmt} --> {end_fmt}"
            raw_text = str(seg["text"])

            self.table.insertRow(idx)
            self._row_map[seg_id] = idx

            # ID Item (Read-only)
            id_item = QTableWidgetItem(f"#{seg_id}")
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 0, id_item)

            # Timestamp Item (Read-only)
            ts_item = QTableWidgetItem(ts_text)
            ts_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            ts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 1, ts_item)

            # Raw Speech Item (Read-only)
            raw_item = QTableWidgetItem(raw_text)
            raw_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(idx, 2, raw_item)

            # Subtitle Text Item (Editable)
            sub_item = QTableWidgetItem(raw_text)
            sub_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(idx, 3, sub_item)

            # Status Item (Read-only badge)
            status_item = QTableWidgetItem("Raw")
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(idx, 4, status_item)

            # Action Buttons Widget with Model Selector Dropdown
            actions_widget = SegmentActionWidget(seg_id, available_models=self._available_models)
            actions_widget.convert_clicked.connect(self._on_convert_clicked)
            actions_widget.revert_clicked.connect(self.revert_segment)
            self.table.setCellWidget(idx, 5, actions_widget)

        self.table.blockSignals(False)
        self.info_label.setText(f"Interactive Subtitle Studio: {len(segments)} segments loaded")
        self.segments_changed.emit()

    def update_segment_translation(
        self, segment_id: int, translated_text: str, status: str = "Translated"
    ) -> None:
        """Update subtitle text and status badge for a single segment line."""
        if segment_id not in self._row_map:
            return
        row = self._row_map[segment_id]
        self.table.blockSignals(True)

        sub_item = self.table.item(row, 3)
        if sub_item:
            sub_item.setText(translated_text.strip())

        status_item = self.table.item(row, 4)
        if status_item:
            status_item.setText(status)
            if "Error" in status:
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == "Raw":
                status_item.setForeground(Qt.GlobalColor.gray)
            else:
                status_item.setForeground(Qt.GlobalColor.green)

        actions_widget = self.table.cellWidget(row, 5)
        if isinstance(actions_widget, SegmentActionWidget):
            actions_widget.set_translating(False)
            raw_item = self.table.item(row, 2)
            raw_text = raw_item.text() if raw_item else ""
            actions_widget.set_revert_enabled(translated_text.strip() != raw_text.strip())

        self.table.blockSignals(False)
        self.segments_changed.emit()

    def get_max_concurrency(self) -> int:
        """Get maximum number of parallel concurrent line translation workers."""
        text = self.concurrency_combo.currentText()
        if "2" in text:
            return 2
        elif "8" in text:
            return 8
        elif "16" in text:
            return 16
        return 4

    def get_row_selected_model(self, segment_id: int) -> tuple[str, str]:
        """Return (provider, model_name) selected for the given segment row."""
        if segment_id in self._row_map:
            row = self._row_map[segment_id]
            actions_widget = self.table.cellWidget(row, 5)
            if isinstance(actions_widget, SegmentActionWidget):
                return actions_widget.get_selected_provider_and_model()
        return "ollama", "llama3.2:3b"

    def set_convert_all_running(
        self, is_running: bool, current: int = 0, total: int = 0
    ) -> None:
        """Update Convert All button disabled state and text while converting lines."""
        if is_running:
            self.convert_all_btn.setEnabled(False)
            if total > 0:
                self.convert_all_btn.setText(f"Status: Running ({current}/{total})...")
            else:
                self.convert_all_btn.setText("Status: Running...")
            self.convert_all_btn.setStyleSheet(
                "background-color: #45475a; color: #a6adc8; font-weight: bold; padding: 6px 12px; border-radius: 6px;"
            )
        else:
            self.convert_all_btn.setEnabled(True)
            self.convert_all_btn.setText("Convert All Lines")
            self.convert_all_btn.setStyleSheet(
                "background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 6px 12px; border-radius: 6px;"
            )

    def set_segment_translating(self, segment_id: int) -> None:
        """Mark row status as 'Translating...'."""
        if segment_id not in self._row_map:
            return
        row = self._row_map[segment_id]
        status_item = self.table.item(row, 4)
        if status_item:
            status_item.setText("Translating...")
            status_item.setForeground(Qt.GlobalColor.yellow)

        actions_widget = self.table.cellWidget(row, 5)
        if isinstance(actions_widget, SegmentActionWidget):
            actions_widget.set_translating(True)

    def revert_segment(self, segment_id: int) -> None:
        """Revert a single segment line back to original raw Whisper text."""
        if segment_id not in self._row_map:
            return
        row = self._row_map[segment_id]
        self.table.blockSignals(True)

        raw_item = self.table.item(row, 2)
        raw_text = raw_item.text() if raw_item else ""

        sub_item = self.table.item(row, 3)
        if sub_item:
            sub_item.setText(raw_text)

        status_item = self.table.item(row, 4)
        if status_item:
            status_item.setText("Raw")
            status_item.setForeground(Qt.GlobalColor.gray)

        actions_widget = self.table.cellWidget(row, 5)
        if isinstance(actions_widget, SegmentActionWidget):
            actions_widget.set_translating(False)
            actions_widget.set_revert_enabled(False)

        self.table.blockSignals(False)
        self.segments_changed.emit()

    def revert_all_segments(self) -> None:
        """Revert all segments back to original raw Whisper text."""
        for seg_id in list(self._row_map.keys()):
            self.revert_segment(seg_id)
        self.revert_all_requested.emit()

    def get_active_segments(self) -> list[dict]:
        """Return active segment dicts with current subtitle text for SRT generation."""
        active: list[dict] = []
        for idx in range(self.table.rowCount()):
            raw_seg = self._raw_segments[idx] if idx < len(self._raw_segments) else {}
            sub_item = self.table.item(idx, 3)
            current_text = sub_item.text() if sub_item else str(raw_seg.get("text", ""))

            active.append({
                "id": raw_seg.get("id", idx + 1),
                "start": raw_seg.get("start", 0.0),
                "end": raw_seg.get("end", 0.0),
                "text": current_text,
            })
        return active

    def _on_convert_clicked(self, segment_id: int, provider: str, model_name: str) -> None:
        """Handle per-row [Convert] button click."""
        if segment_id not in self._row_map:
            return
        row = self._row_map[segment_id]
        raw_seg = self._raw_segments[row] if row < len(self._raw_segments) else {}
        self.set_segment_translating(segment_id)
        self.convert_requested.emit(segment_id, raw_seg, provider, model_name)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle manual text cell editing."""
        if item.column() == 3:  # Subtitle Text column
            row = item.row()
            raw_item = self.table.item(row, 2)
            raw_text = raw_item.text() if raw_item else ""
            current_text = item.text()

            status_item = self.table.item(row, 4)
            if status_item:
                if current_text.strip() != raw_text.strip():
                    status_item.setText("Edited")
                    status_item.setForeground(Qt.GlobalColor.cyan)
                else:
                    status_item.setText("Raw")
                    status_item.setForeground(Qt.GlobalColor.gray)

            actions_widget = self.table.cellWidget(row, 5)
            if isinstance(actions_widget, SegmentActionWidget):
                actions_widget.set_revert_enabled(current_text.strip() != raw_text.strip())

            self.segments_changed.emit()
