"""Unit tests for InteractiveSubtitleTableWidget in src/gui/subtitle_table.py."""

import os
import unittest
from PyQt6.QtWidgets import QApplication
from src.gui.subtitle_table import InteractiveSubtitleTableWidget, SegmentActionWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_app = QApplication.instance() or QApplication([])


class TestInteractiveSubtitleTableWidget(unittest.TestCase):
    """Test suite for InteractiveSubtitleTableWidget."""

    def setUp(self):
        self.widget = InteractiveSubtitleTableWidget()
        self.segments = [
            {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello world"},
            {"id": 2, "start": 2.5, "end": 5.0, "text": "This is a test"},
        ]

    def test_load_segments(self):
        """Verify loading segments populates table rows correctly."""
        self.widget.load_segments(self.segments)
        self.assertEqual(self.widget.table.rowCount(), 2)

        # Check raw and active text
        self.assertEqual(self.widget.table.item(0, 2).text(), "Hello world")
        self.assertEqual(self.widget.table.item(0, 3).text(), "Hello world")
        self.assertEqual(self.widget.table.item(0, 4).text(), "Raw")

    def test_update_segment_translation(self):
        """Verify updating single segment translation."""
        self.widget.load_segments(self.segments)
        self.widget.update_segment_translation(1, "হ্যালো বিশ্ব", status="Translated")

        self.assertEqual(self.widget.table.item(0, 3).text(), "হ্যালো বিশ্ব")
        self.assertEqual(self.widget.table.item(0, 4).text(), "Translated")

        # Check action widget revert button is enabled
        actions_widget = self.widget.table.cellWidget(0, 5)
        self.assertIsInstance(actions_widget, SegmentActionWidget)
        self.assertTrue(actions_widget.revert_btn.isEnabled())

    def test_revert_segment(self):
        """Verify reverting a segment restores original raw text."""
        self.widget.load_segments(self.segments)
        self.widget.update_segment_translation(1, "হ্যালো বিশ্ব", status="Translated")
        self.widget.revert_segment(1)

        self.assertEqual(self.widget.table.item(0, 3).text(), "Hello world")
        self.assertEqual(self.widget.table.item(0, 4).text(), "Raw")

    def test_revert_all_segments(self):
        """Verify revert_all_segments resets all rows."""
        self.widget.load_segments(self.segments)
        self.widget.update_segment_translation(1, "হ্যালো বিশ্ব", status="Translated")
        self.widget.update_segment_translation(2, "এটি একটি পরীক্ষা", status="Translated")

        self.widget.revert_all_segments()

        self.assertEqual(self.widget.table.item(0, 3).text(), "Hello world")
        self.assertEqual(self.widget.table.item(1, 3).text(), "This is a test")

    def test_get_active_segments(self):
        """Verify active segments extraction matches table state."""
        self.widget.load_segments(self.segments)
        self.widget.update_segment_translation(1, "Hello World (Edited)")

        active = self.widget.get_active_segments()
        self.assertEqual(len(active), 2)
        self.assertEqual(active[0]["text"], "Hello World (Edited)")
        self.assertEqual(active[1]["text"], "This is a test")

    def test_set_convert_all_running_toggle(self):
        """Verify set_convert_all_running disables button and updates text."""
        self.widget.set_convert_all_running(True, current=1, total=5)
        self.assertFalse(self.widget.convert_all_btn.isEnabled())
        self.assertIn("Status: Running (1/5)", self.widget.convert_all_btn.text())

        self.widget.set_convert_all_running(False)
        self.assertTrue(self.widget.convert_all_btn.isEnabled())
        self.assertEqual(self.widget.convert_all_btn.text(), "Convert All Lines")

    def test_per_row_model_selection(self):
        """Verify each segment row has a model selection QComboBox and passes selected provider/model on convert."""
        self.widget.load_segments(self.segments)
        actions_widget = self.widget.table.cellWidget(0, 5)
        self.assertIsInstance(actions_widget, SegmentActionWidget)
        self.assertTrue(hasattr(actions_widget, "model_combo"))

        # Select Gemini in row 0
        idx = actions_widget.model_combo.findText("Gemini: 1.5-flash")
        self.assertTrue(idx >= 0)
        actions_widget.model_combo.setCurrentIndex(idx)

        provider, model_name = actions_widget.get_selected_provider_and_model()
        self.assertEqual(provider, "gemini")
        self.assertEqual(model_name, "gemini-1.5-flash")
