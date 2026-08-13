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
        if self.app._fetch_thread and self.app._fetch_thread.isRunning():
            self.app._fetch_thread.wait(2000)
        self.app.show()

    def tearDown(self):
        if hasattr(self, "app") and self.app:
            if self.app._fetch_thread and self.app._fetch_thread.isRunning():
                self.app._fetch_thread.quit()
                self.app._fetch_thread.wait(2000)
            if self.app.worker and self.app.worker.isRunning():
                self.app.worker.quit()
                self.app.worker.wait(2000)
            self.app.close()

    def test_app_initialization(self):
        """Verify SubtitleGeneratorApp window title, QSS, widgets, and default values."""
        self.assertEqual(self.app.windowTitle(), "Video-to-Subtitle AI Pipeline")
        self.assertEqual(self.app.model_combo.currentText(), "small")
        self.assertEqual(self.app.language_combo.currentText(), "English")
        expected_languages = [
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
        ]
        self.assertEqual(
            [self.app.language_combo.itemText(i) for i in range(self.app.language_combo.count())],
            expected_languages,
        )
        self.assertTrue(self.app.enable_llm_check.isChecked())
        self.assertTrue(self.app.ollama_combo.isEditable())
        self.assertTrue(self.app.ollama_container.isVisible())
        self.assertFalse(self.app.ollama_container.isHidden())
        self.assertFalse(self.app.video_player.isEnabled())

    def test_ollama_container_visibility_toggle(self):
        """Verify ollama_container visibility updates dynamically based on enable_llm_check state."""
        self.assertTrue(self.app.enable_llm_check.isChecked())
        self.assertTrue(self.app.ollama_container.isVisible())
        self.assertFalse(self.app.ollama_container.isHidden())

        self.app.enable_llm_check.setChecked(False)
        self.assertFalse(self.app.ollama_container.isVisible())
        self.assertTrue(self.app.ollama_container.isHidden())

        self.app.enable_llm_check.setChecked(True)
        self.assertTrue(self.app.ollama_container.isVisible())
        self.assertFalse(self.app.ollama_container.isHidden())

    def test_start_pipeline_skip_grammar_toggle(self):
        """Verify PipelineWorker receives skip_grammar=True when enable_llm_check is unchecked, and skip_grammar=False when checked."""
        self.app.file_path_edit.setText("/tmp/sample.mp4")
        with patch("os.path.exists", return_value=True), \
             patch("src.gui.app.PipelineWorker") as mock_worker_cls:
            mock_worker_instance = MagicMock()
            mock_worker_cls.return_value = mock_worker_instance

            # Checked: skip_grammar=False
            self.app.enable_llm_check.setChecked(True)
            self.app._on_start_pipeline()
            mock_worker_cls.assert_called_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=False,
                ollama_model=self.app.ollama_combo.currentText(),
                target_language="English",
                llm_provider="ollama",
                api_key=None,
            )

            mock_worker_cls.reset_mock()

            # Unchecked: skip_grammar=True
            self.app.enable_llm_check.setChecked(False)
            self.app._on_start_pipeline()
            mock_worker_cls.assert_called_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=True,
                ollama_model=self.app.ollama_combo.currentText(),
                target_language="English",
                llm_provider="ollama",
                api_key=None,
            )

    def test_custom_ollama_model_string_passing(self):
        """Verify editable ollama_combo passes custom model string to PipelineWorker."""
        self.app.file_path_edit.setText("/tmp/sample.mp4")
        self.assertTrue(self.app.ollama_combo.isEditable())
        custom_model = "mistral:7b-instruct-q4_0"
        self.app.ollama_combo.setEditText(custom_model)

        with patch("os.path.exists", return_value=True), \
             patch("src.gui.app.PipelineWorker") as mock_worker_cls:
            mock_worker_instance = MagicMock()
            mock_worker_cls.return_value = mock_worker_instance

            self.app._on_start_pipeline()

            mock_worker_cls.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=False,
                ollama_model=custom_model,
                target_language="English",
                llm_provider="ollama",
                api_key=None,
            )
            mock_worker_instance.start.assert_called_once()

    def test_start_pipeline_passes_target_language(self):
        """Verify _on_start_pipeline extracts target_language and passes to PipelineWorker."""
        self.app.file_path_edit.setText("/tmp/sample.mp4")
        self.app.language_combo.setCurrentText("Spanish")
        with patch("os.path.exists", return_value=True), \
             patch("src.gui.app.PipelineWorker") as mock_worker_cls:
            mock_worker_instance = MagicMock()
            mock_worker_cls.return_value = mock_worker_instance

            self.app._on_start_pipeline()

            mock_worker_cls.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=False,
                ollama_model=self.app.ollama_combo.currentText(),
                target_language="Spanish",
                llm_provider="ollama",
                api_key=None,
            )
            mock_worker_instance.start.assert_called_once()

    def test_worker_passes_target_language(self):
        """Verify PipelineWorker passes target_language to run_pipeline."""
        worker = PipelineWorker(
            video_path="/tmp/test.mp4",
            target_language="Bangla (Bengali)",
        )
        with patch("src.gui.worker.run_pipeline", return_value="/tmp/test.srt") as mock_run:
            worker.run()
            mock_run.assert_called_once_with(
                video_path="/tmp/test.mp4",
                output_path=None,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.2:3b",
                target_language="Bangla (Bengali)",
                llm_provider="ollama",
                api_key=None,
            )

    def test_provider_selection_toggles_models_and_api_key_visibility(self):
        """Verify selecting Gemini Cloud provider shows API Key field and populates Gemini models."""
        from PyQt6.QtWidgets import QLineEdit

        # Default Local Ollama provider
        self.assertEqual(self.app.provider_combo.currentText(), "Local (Ollama)")
        self.assertTrue(self.app.api_key_container.isHidden())
        self.assertEqual(self.app.api_key_edit.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(
            self.app.api_key_edit.placeholderText(),
            "Enter Gemini API Key (or set GEMINI_API_KEY env var)",
        )

        # Switch to Gemini Cloud provider
        self.app.provider_combo.setCurrentText("Google Gemini (Cloud)")
        self.assertTrue(self.app.api_key_container.isVisible())
        self.assertFalse(self.app.api_key_container.isHidden())
        self.assertEqual(self.app.ollama_combo.currentText(), "gemini-2.5-flash")
        gemini_items = [self.app.ollama_combo.itemText(i) for i in range(self.app.ollama_combo.count())]
        self.assertEqual(gemini_items, ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"])

        # Switch back to Local Ollama provider
        self.app.provider_combo.setCurrentText("Local (Ollama)")
        self.assertTrue(self.app.api_key_container.isHidden())
        self.assertIn("llama3.2:3b", [self.app.ollama_combo.itemText(i) for i in range(self.app.ollama_combo.count())])

    def test_start_pipeline_passes_llm_provider_and_api_key(self):
        """Verify _on_start_pipeline extracts llm_provider='gemini' and api_key correctly."""
        self.app.file_path_edit.setText("/tmp/sample.mp4")
        self.app.provider_combo.setCurrentText("Google Gemini (Cloud)")
        self.app.api_key_edit.setText("test-secret-key-123")

        with patch("os.path.exists", return_value=True), \
             patch("src.gui.app.PipelineWorker") as mock_worker_cls:
            mock_worker_instance = MagicMock()
            mock_worker_cls.return_value = mock_worker_instance

            self.app._on_start_pipeline()

            mock_worker_cls.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=False,
                ollama_model="gemini-2.5-flash",
                target_language="English",
                llm_provider="gemini",
                api_key="test-secret-key-123",
            )
            mock_worker_instance.start.assert_called_once()

    def test_worker_passes_llm_provider_and_api_key(self):
        """Verify PipelineWorker passes llm_provider and api_key to run_pipeline."""
        worker = PipelineWorker(
            video_path="/tmp/test.mp4",
            llm_provider="gemini",
            api_key="cloud-api-key-xyz",
        )
        with patch("src.gui.worker.run_pipeline", return_value="/tmp/test.srt") as mock_run:
            worker.run()
            mock_run.assert_called_once_with(
                video_path="/tmp/test.mp4",
                output_path=None,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.2:3b",
                target_language="English",
                llm_provider="gemini",
                api_key="cloud-api-key-xyz",
            )

    def test_puter_provider_selection(self):
        """Verify selecting Puter provider shows API key field with Puter placeholder and populates Puter models."""
        from src.gui.app import PUTER_MODELS

        self.app.provider_combo.setCurrentText("Puter.js AI (Cloud)")
        self.assertTrue(self.app.api_key_container.isVisible())
        self.assertFalse(self.app.api_key_container.isHidden())
        self.assertEqual(
            self.app.api_key_edit.placeholderText(),
            "Enter Puter API Key (or set PUTER_API_KEY env var)",
        )
        self.assertEqual(self.app.ollama_combo.currentText(), "gpt-4o-mini")
        puter_items = [self.app.ollama_combo.itemText(i) for i in range(self.app.ollama_combo.count())]
        self.assertEqual(puter_items, PUTER_MODELS)

    def test_start_pipeline_passes_puter_provider(self):
        """Verify _on_start_pipeline extracts llm_provider='puter' and passes provider to PipelineWorker."""
        self.app.file_path_edit.setText("/tmp/sample.mp4")
        self.app.provider_combo.setCurrentText("Puter.js AI (Cloud)")
        self.app.api_key_edit.setText("puter-secret-key-456")

        with patch("os.path.exists", return_value=True), \
             patch("src.gui.app.PipelineWorker") as mock_worker_cls:
            mock_worker_instance = MagicMock()
            mock_worker_cls.return_value = mock_worker_instance

            self.app._on_start_pipeline()

            mock_worker_cls.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                model_size="small",
                skip_grammar=False,
                ollama_model="gpt-4o-mini",
                target_language="English",
                llm_provider="puter",
                api_key="puter-secret-key-456",
            )
            mock_worker_instance.start.assert_called_once()

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
             patch.object(self.app.video_player, "play") as mock_play, \
             patch("src.gui.app.QMessageBox.information") as mock_info:
            self.app._on_pipeline_finished(video_path, srt_path)
            self.assertTrue(self.app.start_button.isEnabled())
            self.assertEqual(self.app.progress_bar.value(), 100)
            self.assertIn("Completed", self.app.stage_label.text())
            self.assertTrue(self.app.video_player.isEnabled())
            mock_load.assert_called_once_with(video_path, srt_path)
            mock_play.assert_called_once()
            mock_info.assert_called_once()

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

    def test_main_cli_target_language_flag(self):
        """Verify main.py CLI accepts -l / --target-language flag and passes to run_pipeline."""
        with patch("sys.argv", ["main.py", "-i", "/tmp/sample.mp4", "-l", "French"]), \
             patch("src.orchestration.pipeline.run_pipeline", return_value="/tmp/sample.srt") as mock_run, \
             patch("main.setup_logging"):
            res = main.main()
            self.assertEqual(res, 0)
            mock_run.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                output_path=None,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.2:3b",
                target_language="French",
                llm_provider="ollama",
                api_key=None,
            )

    def test_main_cli_llm_provider_and_api_key_flags(self):
        """Verify main.py CLI accepts --llm-provider and --api-key flags and passes to run_pipeline."""
        with patch("sys.argv", ["main.py", "-i", "/tmp/sample.mp4", "--llm-provider", "gemini", "--api-key", "my-gemini-key"]), \
             patch("src.orchestration.pipeline.run_pipeline", return_value="/tmp/sample.srt") as mock_run, \
             patch("main.setup_logging"):
            res = main.main()
            self.assertEqual(res, 0)
            mock_run.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                output_path=None,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.2:3b",
                target_language="English",
                llm_provider="gemini",
                api_key="my-gemini-key",
            )

    def test_main_cli_puter_provider_flag(self):
        """Verify main.py CLI accepts --llm-provider puter and passes to run_pipeline."""
        with patch("sys.argv", ["main.py", "-i", "/tmp/sample.mp4", "--llm-provider", "puter"]), \
             patch("src.orchestration.pipeline.run_pipeline", return_value="/tmp/sample.srt") as mock_run, \
             patch("main.setup_logging"):
            res = main.main()
            self.assertEqual(res, 0)
            mock_run.assert_called_once_with(
                video_path="/tmp/sample.mp4",
                output_path=None,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.2:3b",
                target_language="English",
                llm_provider="puter",
                api_key=None,
            )


if __name__ == "__main__":
    unittest.main()
