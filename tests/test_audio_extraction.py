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
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-map",
            "0:a:0?",
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

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_get_audio_tracks_multi_audio(self, mock_run, mock_exists):
        from src.audio_extraction.extractor import get_audio_tracks
        mock_output = '{"streams": [{"index": 1, "codec_name": "aac", "channels": 2, "tags": {"language": "hin", "title": "Hindi"}}, {"index": 2, "codec_name": "aac", "channels": 6, "tags": {"language": "eng", "title": "English"}}]}'
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)

        tracks = get_audio_tracks("multi_audio.mkv")
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0]["language"], "hin")
        self.assertIn("Hindi", tracks[0]["label"])
        self.assertEqual(tracks[1]["language"], "eng")
        self.assertIn("English", tracks[1]["label"])


if __name__ == "__main__":
    unittest.main()

