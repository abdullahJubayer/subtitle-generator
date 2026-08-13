"""Unit tests for PyQt6 GUI components and main.py GUI CLI flag integration."""

import os
import unittest
from unittest.mock import ANY, MagicMock, patch

from PyQt6.QtWidgets import QApplication

import main
from src.gui.app import SubtitleGeneratorApp
from src.gui.console_widgets import SrtConsoleWidget, WhisperConsoleWidget, verify_srt_integrity
from src.gui.player import VideoPlayerWidget, parse_srt_time
from src.gui.worker import PipelineWorker

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_app = QApplication.instance() or QApplication([])


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
                audio_track=0,
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
                audio_track=0,
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
                audio_track=0,
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
                audio_track=0,
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
                audio_track=0,
                llm_callback=ANY,
                transcription_callback=ANY,
            )

    def test_provider_selection_toggles_models_and_api_key_visibility(self):
        """Verify selecting Gemini Cloud provider shows API Key field and populates Gemini models."""
        from PyQt6.QtWidgets import QLineEdit

        # Default Local Ollama provider
        self.assertEqual(self.app.provider_combo.currentText(), "Local (Ollama)")
        self.assertTrue(self.app.api_key_container.isHidden())
        self.assertEqual(self.app.api_key_edit.echoMode(), QLineEdit.EchoMode.Password)
        self.assertIn("Loaded automatically", self.app.api_key_edit.placeholderText())

        # Switch to Gemini Cloud provider
        self.app.provider_combo.setCurrentText("Google Gemini (Cloud)")
        self.assertTrue(self.app.api_key_container.isHidden())
        gemini_items = [self.app.ollama_combo.itemText(i) for i in range(self.app.ollama_combo.count())]
        self.assertTrue(len(gemini_items) > 0)
        self.assertIn(self.app.ollama_combo.currentText(), gemini_items)

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
                ollama_model="gemini-1.5-flash",
                target_language="English",
                llm_provider="gemini",
                api_key="test-secret-key-123",
                audio_track=0,
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
                audio_track=0,
                llm_callback=ANY,
                transcription_callback=ANY,
            )

    def test_puter_provider_selection(self):
        """Verify selecting Puter provider shows API key field with Puter placeholder and populates Puter models."""
        from src.gui.app import PUTER_MODELS

        self.app.provider_combo.setCurrentText("Puter.js AI (Cloud)")
        self.assertTrue(self.app.api_key_container.isHidden())
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
                audio_track=0,
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
                audio_track=0,
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
                audio_track=0,
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
                audio_track=0,
            )

    def test_whisper_console_widget(self):
        """Verify WhisperConsoleWidget telemetry updating, logging, filtering, and export signal."""
        widget = WhisperConsoleWidget()
        widget.update_telemetry("French", 0.92, 45.67, "medium")
        self.assertIn("French", widget.telemetry_label.text())
        self.assertIn("0.92", widget.telemetry_label.text())
        self.assertIn("45.67s", widget.telemetry_label.text())
        self.assertIn("medium", widget.telemetry_label.text())

        widget.append_log("Segment 1: Transcription started")
        widget.append_log("Segment 2: Processing audio frames")
        self.assertIn("Transcription started", widget.get_log_text())
        self.assertIn("Processing audio frames", widget.get_log_text())

        # Test search filter
        widget.search_input.setText("audio")
        self.assertIn("Processing audio frames", widget.log_area.toPlainText())
        self.assertNotIn("Transcription started", widget.log_area.toPlainText())

        widget.search_input.setText("")
        self.assertIn("Transcription started", widget.log_area.toPlainText())

        # Test export signal & method
        mock_slot = MagicMock()
        widget.export_requested.connect(mock_slot)
        import tempfile
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as temp_file:
            temp_path = temp_file.name
        try:
            res = widget.export_log(temp_path)
            self.assertTrue(res)
            mock_slot.assert_called_once_with(temp_path)
            with open(temp_path, "r", encoding="utf-8") as f:
                saved_content = f.read()
            self.assertIn("Transcription started", saved_content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # Test clear log
        widget.clear_log()
        self.assertEqual(widget.get_log_text(), "")
        self.assertEqual(widget.log_area.toPlainText(), "")

    def test_srt_console_widget(self):
        """Verify SrtConsoleWidget SRT loading, timestamp integrity status, copy, and save features."""
        widget = SrtConsoleWidget()
        valid_srt = "1\n00:00:01,000 --> 00:00:04,000\nTest subtitle line.\n\n"
        widget.set_srt_content(valid_srt)

        self.assertEqual(widget.get_srt_content(), valid_srt)
        self.assertIn("Valid", widget.integrity_label.text())

        # Test manual update integrity status
        widget.update_integrity_status(False, "Invalid sequence")
        self.assertIn("Invalid", widget.integrity_label.text())
        self.assertIn("Invalid sequence", widget.integrity_label.text())

        # Test copy to clipboard
        widget.copy_button.click()
        clipboard_text = _app.clipboard().text()
        self.assertEqual(clipboard_text, valid_srt)

        # Test save .srt file button
        import tempfile
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".srt") as temp_file:
            save_target = temp_file.name
        try:
            with patch("src.gui.console_widgets.QFileDialog.getSaveFileName", return_value=(save_target, "SubRip")):
                widget.save_button.click()
            with open(save_target, "r", encoding="utf-8") as f:
                file_content = f.read()
            self.assertEqual(file_content, valid_srt)
        finally:
            if os.path.exists(save_target):
                os.remove(save_target)

    def test_app_console_tabs_integration(self):
        """Verify QTabWidget embedding WhisperConsoleWidget, LlmConsoleWidget, and SrtConsoleWidget in SubtitleGeneratorApp."""
        self.assertTrue(hasattr(self.app, "console_tabs"))
        self.assertTrue(hasattr(self.app, "studio_table"))
        self.assertTrue(hasattr(self.app, "whisper_console"))
        self.assertTrue(hasattr(self.app, "llm_console"))
        self.assertTrue(hasattr(self.app, "srt_console"))

        self.assertEqual(self.app.console_tabs.count(), 3)
        self.assertEqual(self.app.console_tabs.tabText(0), "Whisper Log")
        self.assertEqual(self.app.console_tabs.tabText(1), "LLM Telemetry & Diffs")
        self.assertEqual(self.app.console_tabs.tabText(2), "SRT Preview")

        # Test log routing
        self.app._on_log_emitted("[Step 3/4] LLM grammar correction starting...")
        self.assertIn("LLM grammar correction starting", self.app.whisper_console.get_log_text())

        # Test srt auto-loading on pipeline finish
        import tempfile
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".srt") as temp_srt:
            temp_srt.write("1\n00:00:01,000 --> 00:00:03,000\nTab preview text\n\n")
            temp_srt_path = temp_srt.name

        try:
            with patch.object(self.app.video_player, "load_video"), \
                 patch.object(self.app.video_player, "play"), \
                 patch("src.gui.app.QMessageBox.information"):
                self.app._on_pipeline_finished("/tmp/dummy.mp4", temp_srt_path)
            self.assertIn("Tab preview text", self.app.srt_console.get_srt_content())
            self.assertIn("Valid", self.app.srt_console.integrity_label.text())
        finally:
            if os.path.exists(temp_srt_path):
                os.remove(temp_srt_path)


    def test_llm_console_widget_initialization(self):
        """Verify LlmConsoleWidget components, read-only edits, columns, and initial telemetry label."""
        from src.gui.console_widgets import LlmConsoleWidget

        widget = LlmConsoleWidget()
        self.assertTrue(widget.payload_edit.isReadOnly())
        self.assertTrue(widget.response_edit.isReadOnly())
        self.assertEqual(widget.diff_table.columnCount(), 2)
        self.assertIn("Provider: N/A", widget.telemetry_label.text())

    def test_llm_console_widget_update_and_diffs(self):
        """Verify update_llm_interaction, add_diff_rows, and clear methods of LlmConsoleWidget."""
        from src.gui.console_widgets import LlmConsoleWidget

        widget = LlmConsoleWidget()
        payload = '[{"id": 1, "text": "Hello world"}]'
        response = '{"segments": [{"id": 1, "text": "Hello, world!"}]}'
        provider = "ollama"
        model_name = "llama3.2:3b"
        batch_info = "Batch 1/1 (1 segs) | Latency: 0.12s"

        widget.update_llm_interaction(payload, response, provider, model_name, batch_info)
        self.assertEqual(widget.payload_edit.toPlainText(), payload)
        self.assertEqual(widget.response_edit.toPlainText(), response)
        self.assertIn("ollama", widget.telemetry_label.text())
        self.assertIn("llama3.2:3b", widget.telemetry_label.text())

        diffs = [("Hello world", "Hello, world!")]
        widget.add_diff_rows(diffs)
        self.assertEqual(widget.diff_table.rowCount(), 1)
        self.assertEqual(widget.diff_table.item(0, 0).text(), "Hello world")
        self.assertEqual(widget.diff_table.item(0, 1).text(), "Hello, world!")

        widget.clear()
        self.assertEqual(widget.payload_edit.toPlainText(), "")
        self.assertEqual(widget.response_edit.toPlainText(), "")
        self.assertEqual(widget.diff_table.rowCount(), 0)

    def test_llm_console_slot_receiver(self):
        """Verify on_llm_data_emitted slot method updates telemetry text and diff table rows."""
        from src.gui.console_widgets import LlmConsoleWidget

        widget = LlmConsoleWidget()
        widget.on_llm_data_emitted(
            payload_json='[{"id": 1, "text": "test"}]',
            response_json='[{"id": 1, "text": "Test."}]',
            provider="gemini",
            model_name="gemini-2.5-flash",
            batch_info="Batch 1/1 (1 segs) | Latency: 0.25s",
            diff_items=[("test", "Test.")],
        )
        self.assertEqual(widget.payload_edit.toPlainText(), '[{"id": 1, "text": "test"}]')
        self.assertEqual(widget.diff_table.rowCount(), 1)
        self.assertEqual(widget.diff_table.item(0, 0).text(), "test")
        self.assertEqual(widget.diff_table.item(0, 1).text(), "Test.")

    def test_corrector_llm_callback_invocation(self):
        """Verify correct_grammar invokes llm_callback with telemetry data and diff pairs."""
        from src.grammar_correction.corrector import correct_grammar

        segments = [{"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"}]
        mock_cb = MagicMock()

        mock_response = '{"segments": [{"id": 1, "text": "Hello world."}]}'
        with patch("src.grammar_correction.corrector.call_llm_provider", return_value=mock_response):
            res = correct_grammar(
                segments,
                model_name="llama3.2:3b",
                provider="ollama",
                llm_callback=mock_cb,
            )

        self.assertEqual(res[0]["text"], "Hello world.")
        mock_cb.assert_called_once()
        args = mock_cb.call_args[0]
        payload_json, resp_json, provider, model_name, batch_info, diff_items = args
        self.assertIn("hello world", payload_json)
        self.assertEqual(resp_json, mock_response)
        self.assertEqual(provider, "ollama")
        self.assertEqual(model_name, "llama3.2:3b")
        self.assertIn("Batch", batch_info)
        self.assertEqual(diff_items, [("hello world", "Hello world.")])

    def test_worker_llm_data_emitted_signal(self):
        """Verify PipelineWorker emits llm_data_emitted signal when callback is invoked."""
        worker = PipelineWorker(video_path="/tmp/test.mp4")
        received_data = []
        worker.llm_data_emitted.connect(lambda *args: received_data.append(args))

        def dummy_run_pipeline(*args, **kwargs):
            cb = kwargs.get("llm_callback")
            if cb:
                cb('{"id": 1}', '{"id": 1, "text": "out"}', "ollama", "llama3.2", "Batch 1/1", [("in", "out")])
            return "/tmp/test.srt"

        with patch("src.gui.worker.run_pipeline", side_effect=dummy_run_pipeline):
            worker.run()

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0][2], "ollama")
        self.assertEqual(received_data[0][5], [("in", "out")])

    def test_stage_transitions_manual_navigation(self):
        """Verify navigation buttons correctly switch between Stage 0 (Setup), Stage 1 (Studio), and Stage 2 (Player)."""
        self.assertEqual(self.app.stack.currentIndex(), 0)

        # Switch to Stage 1 (Studio)
        self.app.btn_step2.click()
        self.assertEqual(self.app.stack.currentIndex(), 1)

        # Switch to Stage 2 (Player)
        self.app.btn_step3.click()
        self.assertEqual(self.app.stack.currentIndex(), 2)

        # Back to Stage 0 (Setup)
        self.app.btn_step1.click()
        self.assertEqual(self.app.stack.currentIndex(), 0)

    def test_on_segments_transcribed_stage_transition(self):
        """Verify _on_segments_transcribed loads segments into studio table and transitions to Stage 1."""
        segments = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "First line"},
            {"id": 2, "start": 2.0, "end": 4.0, "text": "Second line"},
        ]
        self.assertEqual(self.app.stack.currentIndex(), 0)
        self.app._on_segments_transcribed(segments)
        self.assertEqual(self.app.stack.currentIndex(), 1)
        self.assertEqual(self.app.studio_table.table.rowCount(), 2)
        active = self.app.studio_table.get_active_segments()
        self.assertEqual(len(active), 2)
        self.assertEqual(active[0]["text"], "First line")

    def test_on_build_and_load_srt_stage_transition(self):
        """Verify _on_build_and_load_srt builds SRT from active studio segments and transitions to Stage 2."""
        segments = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "Sample active line"},
        ]
        self.app.studio_table.load_segments(segments)
        self.app.selected_video_path = "/tmp/sample.mp4"

        with patch("os.path.exists", return_value=True), \
             patch.object(self.app.video_player, "load_video") as mock_load, \
             patch.object(self.app.video_player, "play") as mock_play:
            self.app._on_build_and_load_srt()
            self.assertEqual(self.app.stack.currentIndex(), 2)
            self.assertIn("Sample active line", self.app.srt_console.get_srt_content())
            mock_load.assert_called_once()
            mock_play.assert_called_once()


if __name__ == "__main__":
    unittest.main()



