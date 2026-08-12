import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from src.audio_extraction import extract_audio


class TestAudioExtraction(unittest.TestCase):

    @patch("subprocess.run")
    def test_extract_audio_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        video = "input.mp4"
        audio = "output.mp3"
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

    @patch("subprocess.run")
    def test_extract_audio_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="ffmpeg", stderr="No audio stream"
        )

        with self.assertRaises(RuntimeError) as ctx:
            extract_audio("input.mp4", "output.mp3")

        self.assertIn("FFmpeg audio extraction failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
