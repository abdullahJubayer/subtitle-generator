"""Video Player widget module with synced subtitle overlays for PyQt6."""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import QEvent, QObject, Qt, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


def timestamp_to_ms(time_str: str) -> int:
    """Convert an SRT timestamp string (HH:MM:SS,mmm or HH:MM:SS.mmm) to milliseconds."""
    time_str = time_str.strip().replace(",", ".")
    parts = time_str.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        sec_parts = parts[2].split(".")
        seconds = int(sec_parts[0])
        millis = int(sec_parts[1].ljust(3, "0")[:3]) if len(sec_parts) > 1 else 0
        return (hours * 3600 + minutes * 60 + seconds) * 1000 + millis
    except ValueError:
        return 0


def parse_srt_time(time_str: str) -> int:
    """Alias for timestamp_to_ms for compatibility."""
    return timestamp_to_ms(time_str)



def parse_srt(srt_path: str) -> List[Tuple[int, int, str]]:
    """Parse a .srt file into a list of tuples (start_ms, end_ms, text)."""
    subtitles: List[Tuple[int, int, str]] = []
    file_path = Path(srt_path)
    if not file_path.exists():
        logger.warning("SRT file not found: %s", srt_path)
        return subtitles

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error("Failed to read SRT file '%s': %s", srt_path, e)
        return subtitles

    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue

        time_index = -1
        for idx, line in enumerate(lines):
            if "-->" in line:
                time_index = idx
                break

        if time_index == -1:
            continue

        times = lines[time_index].split("-->")
        if len(times) != 2:
            continue

        start_ms = timestamp_to_ms(times[0])
        end_ms = timestamp_to_ms(times[1])
        text = "\n".join(lines[time_index + 1 :])

        if end_ms >= start_ms:
            subtitles.append((start_ms, end_ms, text))

    return subtitles


def format_time_ms(ms: int) -> str:
    """Format milliseconds into MM:SS or HH:MM:SS format."""
    total_seconds = max(0, ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class VideoPlayerWidget(QWidget):
    """PyQt6 Video Player Widget with synchronized subtitle overlays."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.subtitles: List[Tuple[int, int, str]] = []

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Video container widget
        self.video_container = QWidget(self)
        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget(self.video_container)
        container_layout.addWidget(self.video_widget)

        # Subtitle overlay label positioned over video widget
        self.subtitle_label = QLabel(self.video_widget)
        self.subtitle_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 180);"
            "color: white;"
            "font-weight: bold;"
            "font-size: 16px;"
            "padding: 6px 12px;"
            "border-radius: 4px;"
        )
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.hide()

        # Media player and audio output initialization
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Transport controls
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 5, 10, 5)

        self.play_button = QPushButton("Play", self)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00", self)

        self.volume_label = QLabel("Vol:", self)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.audio_output.setVolume(0.7)

        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.seek_slider)
        controls_layout.addWidget(self.time_label)
        controls_layout.addWidget(self.volume_label)
        controls_layout.addWidget(self.volume_slider)

        main_layout.addWidget(self.video_container, stretch=1)
        main_layout.addLayout(controls_layout)

        # Event filter to dynamically center subtitle overlay when video widget resizes
        self.video_widget.installEventFilter(self)

    def _connect_signals(self) -> None:
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.seek_slider.sliderMoved.connect(self._on_seek_slider_moved)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched == self.video_widget and event.type() == QEvent.Type.Resize:
            self._update_subtitle_position()
        return super().eventFilter(watched, event)

    def load_video_and_subtitles(self, video_path: str, srt_path: str) -> None:
        """Load video file and subtitle file for playback.

        Args:
            video_path: Absolute or relative path to the video file.
            srt_path: Absolute or relative path to the .srt subtitle file.
        """
        self.subtitles = parse_srt(srt_path) if srt_path else []
        video_url = QUrl.fromLocalFile(video_path)
        self.media_player.setSource(video_url)
        self.subtitle_label.setText("")
        self.subtitle_label.hide()

    def load_video(self, video_path: str, srt_path: Optional[str] = None) -> None:
        """Load video file and optional subtitle file."""
        self.load_video_and_subtitles(video_path, srt_path or "")

    def play(self) -> None:
        """Start or resume video playback."""
        self.media_player.play()

    def pause(self) -> None:
        """Pause video playback."""
        self.media_player.pause()


    def _toggle_play_pause(self) -> None:
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")

    def _on_seek_slider_moved(self, position: int) -> None:
        self.media_player.setPosition(position)

    def _on_volume_changed(self, value: int) -> None:
        self.audio_output.setVolume(value / 100.0)

    def _on_position_changed(self, position: int) -> None:
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        self._update_time_label(position, self.media_player.duration())
        self._update_subtitle_overlay(position)

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, duration)
        self._update_time_label(self.media_player.position(), duration)

    def _update_time_label(self, current_ms: int, duration_ms: int) -> None:
        current_str = format_time_ms(current_ms)
        duration_str = format_time_ms(duration_ms)
        self.time_label.setText(f"{current_str} / {duration_str}")

    def _update_subtitle_overlay(self, position_ms: int) -> None:
        current_text = ""
        for start, end, text in self.subtitles:
            if start <= position_ms <= end:
                current_text = text
                break

        if current_text:
            self.subtitle_label.setText(current_text)
            self.subtitle_label.show()
            self._update_subtitle_position()
        else:
            self.subtitle_label.setText("")
            self.subtitle_label.hide()

    def _update_subtitle_position(self) -> None:
        if not self.subtitle_label.text():
            return

        vw_rect = self.video_widget.rect()
        if vw_rect.isEmpty():
            return

        margin_bottom = 30
        max_width = int(vw_rect.width() * 0.85)

        self.subtitle_label.setMaximumWidth(max_width)
        size_hint = self.subtitle_label.sizeHint()
        width = min(max_width, max(200, size_hint.width() + 24))
        height = size_hint.height() + 12

        x = (vw_rect.width() - width) // 2
        y = vw_rect.height() - height - margin_bottom
        self.subtitle_label.setGeometry(x, max(10, y), width, height)
        self.subtitle_label.raise_()
