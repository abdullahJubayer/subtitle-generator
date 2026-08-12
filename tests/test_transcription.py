import unittest
from unittest.mock import MagicMock, patch

from src.transcription.transcriber import transcribe_audio


class TestTranscription(unittest.TestCase):

    @patch("os.path.exists", return_value=True)
    @patch("src.transcription.transcriber.WhisperModel")
    def test_transcribe_audio_success(self, mock_whisper_cls, mock_exists):
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

        result = transcribe_audio("test.wav", model_size="small")

        mock_whisper_cls.assert_called_once_with(
            "small", device="cpu", compute_type="int8"
        )
        mock_model.transcribe.assert_called_once_with("test.wav", beam_size=5)

        expected = [
            {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello world!"},
            {"id": 2, "start": 2.5, "end": 5.0, "text": "This is a test segment."},
        ]
        self.assertEqual(result, expected)

    def test_transcribe_audio_non_existent_file(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            transcribe_audio("non_existent_audio.wav")
        self.assertIn("Input audio file not found", str(ctx.exception))

    @patch("os.path.exists", return_value=True)
    @patch("src.transcription.transcriber.WhisperModel")
    def test_transcribe_audio_failure(self, mock_whisper_cls, mock_exists):
        mock_whisper_cls.side_effect = Exception("Model load failed")

        with self.assertRaises(RuntimeError) as ctx:
            transcribe_audio("test.wav")

        self.assertIn("Transcription failed for audio file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

