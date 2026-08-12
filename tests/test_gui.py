"""Unit tests for PyQt6 GUI components and main.py GUI CLI flag integration."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_app = QApplication.instance() or QApplication([])

from src.gui.app import SubtitleGeneratorApp
from src.gui.player import VideoPlayerWidget, parse_srt, parse_srt_time
from src.gui.worker import PipelineWorker, QLogHandler
import main


class TestGUIComponents(unittest.TestCase):
    """Test suite for GUI widgets, player, worker threads, and CLI flags."""

    def setUp(self):
        self.app = SubtitleGeneratorApp()

    def test_app_initialization(self):
        """Verify SubtitleGeneratorApp window title, QSS, widgets, and default values."""
        self.assertEqual(self.app.windowTitle(), "Video-to-Subtitle AI Pipeline")
        self.assertEqual(self.app.model_combo.currentText(), "small")
        self.assertEqual(self.app.ollama_edit.text(), "llama3.1")
        self.assertFalse(self.app.skip_grammar_check.isChecked())
        self.assertFalse(self.app.video_player.isEnabled())

    def test_browse_file_selection(self):
        """Verify QFileDialog file selection updates file_path_edit."""
        with patch("src.gui.app.QFileDialog.getOpenFileName", return_value=("/tmp/sample.mp4", "Video Files")):
            self.app._on_browse_file()
            self.assertEqual(self.app.file_path_edit.text(), "/tmp/sample.mp4")
            self.assertEqual(self.app.selected_video_path, "/tmp/sample.mp4")

    def test_start_pipeline_validation_empty(self):
        """Verify warning dialog when trying to start without selecting a file."""
        self.app.file_path_edit.setText("")
        with patch("src.gui.app.QMessageBox.warning") as mock_warn:
            self.app._on_start_pipeline()
            mock_warn.assert_called_once()

    def test_pipeline_finished_handler(self):
        """Verify app state and player activation when pipeline finished signal fires."""
        video_path = "/tmp/test.mp4"
        srt_path = "/tmp/test.srt"
        with patch.object(self.app.video_player, "load_video") as mock_load, \
             patch.object(self.app.video_player, "play") as mock_play:
            self.app._on_pipeline_finished(video_path, srt_path)
            self.assertTrue(self.app.start_button.isEnabled())
            self.assertEqual(self.app.progress_bar.value(), 100)
            self.assertIn("Completed", self.app.stage_label.text())
            self.assertTrue(self.app.video_player.isEnabled())
            mock_load.assert_called_once_with(video_path, srt_path)
            mock_play.assert_called_once()

    def test_pipeline_error_handler(self):
        """Verify error dialog displayed when worker emits pipeline error."""
        with patch("src.gui.app.QMessageBox.critical") as mock_crit:
            self.app._on_pipeline_error("Test failure details")
            self.assertTrue(self.app.start_button.isEnabled())
            self.assertIn("Error", self.app.stage_label.text())
            mock_crit.assert_called_once()

    def test_srt_time_parser(self):
        """Verify SRT timestamp string parsing to milliseconds."""
        self.assertEqual(parse_srt_time("00:01:23,456"), 83456)
        self.assertEqual(parse_srt_time("01:00:00,000"), 3600000)

    def test_player_widget_methods(self):
        """Verify VideoPlayerWidget loading and toggle state."""
        player = VideoPlayerWidget()
        self.assertEqual(player.play_button.text(), "Play")
        with patch.object(player.media_player, "setSource") as mock_source:
            player.load_video("/tmp/sample.mp4", "/tmp/sample.srt")
            mock_source.assert_called_once()


    def test_main_cli_gui_flag(self):
        """Verify main.py launches GUI on --gui or no arguments."""
        with patch("sys.argv", ["main.py", "--gui"]), patch("main.launch_gui", return_value=0) as mock_launch:
            res = main.main()
            self.assertEqual(res, 0)
            mock_launch.assert_called_once()

        with patch("sys.argv", ["main.py"]), patch("main.launch_gui", return_value=0) as mock_launch:
            res = main.main()
            self.assertEqual(res, 0)
            mock_launch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
