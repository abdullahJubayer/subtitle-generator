import unittest
from unittest.mock import MagicMock, patch

from src.transcription import transcribe_audio


class TestTranscription(unittest.TestCase):

    @patch("src.transcription.transcriber.WhisperModel")
    def test_transcribe_audio_success(self, mock_whisper_cls):
        mock_model = MagicMock()
        mock_whisper_cls.return_value = mock_model

        seg1 = MagicMock()
        seg1.start = 0.0
        seg1.end = 2.5
        seg1.text = " Hello world! "

        seg2 = MagicMock()
        seg2.start = 2.5
        seg2.end = 5.0
        seg2.text = "This is a test segment.  "

        mock_model.transcribe.return_value = ([seg1, seg2], None)

        result = transcribe_audio("test.mp3", model_size="small")

        mock_whisper_cls.assert_called_once_with(
            "small", device="cpu", compute_type="int8"
        )
        mock_model.transcribe.assert_called_once_with("test.mp3", beam_size=5)

        expected = [
            {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello world!"},
            {"id": 2, "start": 2.5, "end": 5.0, "text": "This is a test segment."},
        ]
        self.assertEqual(result, expected)

    @patch("src.transcription.transcriber.WhisperModel")
    def test_transcribe_audio_failure(self, mock_whisper_cls):
        mock_whisper_cls.side_effect = Exception("Model load failed")

        with self.assertRaises(RuntimeError) as ctx:
            transcribe_audio("test.mp3")

        self.assertIn("Transcription failed for audio file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
