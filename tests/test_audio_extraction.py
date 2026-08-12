import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from src.audio_extraction.extractor import extract_audio


class TestAudioExtraction(unittest.TestCase):

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_extract_audio_success(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)

        video = "input.mp4"
        audio = "output.wav"
        result = extract_audio(video, audio)

        expected_cmd = [
            "ffmpeg",
            "-i",
            video,
            "-q:a",
            "0",
            "-map",
            "a",
            audio,
            "-y",
        ]
        mock_run.assert_called_once_with(
            expected_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        self.assertEqual(result, os.path.abspath(audio))

    def test_extract_audio_non_existent_file(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            extract_audio("non_existent_file.mp4", "output.wav")
        self.assertIn("Input video file not found", str(ctx.exception))

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_extract_audio_failure(self, mock_run, mock_exists):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="ffmpeg", stderr="No audio stream"
        )

        with self.assertRaises(RuntimeError) as ctx:
            extract_audio("input.mp4", "output.wav")

        self.assertIn("FFmpeg audio extraction failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

