import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch
from src.orchestration.pipeline import run_pipeline
from src.schemas import SegmentDict


class TestPipeline(unittest.TestCase):

    @patch("src.orchestration.pipeline.generate_srt")
    @patch("src.orchestration.pipeline.correct_grammar")
    @patch("src.orchestration.pipeline.transcribe_audio")
    @patch("src.orchestration.pipeline.extract_audio")
    def test_run_pipeline_success(
        self,
        mock_extract,
        mock_transcribe,
        mock_correct,
        mock_generate,
    ):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            video_path = tmp_video.name

        try:
            mock_extract.return_value = "/path/to/extracted.wav"
            mock_transcribe.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}
            ]
            mock_correct.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello, world!"}
            ]
            expected_srt = str(Path(video_path).with_suffix(".srt").resolve())
            mock_generate.return_value = expected_srt

            result = run_pipeline(
                video_path=video_path,
                model_size="small",
                skip_grammar=False,
                ollama_model="llama3.1",
            )

            mock_extract.assert_called_once()
            mock_transcribe.assert_called_once_with(
                "/path/to/extracted.wav", model_size="small", progress_callback=ANY
            )
            mock_correct.assert_called_once_with(
                [{"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}],
                model_name="llama3.1",
                target_language="English",
                provider="ollama",
                api_key=None,
                llm_callback=ANY,
            )
            mock_generate.assert_called_once_with(
                [{"id": 1, "start": 0.0, "end": 2.5, "text": "Hello, world!"}],
                expected_srt,
            )
            self.assertEqual(result, expected_srt)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    @patch("src.orchestration.pipeline.generate_srt")
    @patch("src.orchestration.pipeline.correct_grammar")
    @patch("src.orchestration.pipeline.transcribe_audio")
    @patch("src.orchestration.pipeline.extract_audio")
    def test_run_pipeline_skip_grammar(
        self,
        mock_extract,
        mock_transcribe,
        mock_correct,
        mock_generate,
    ):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            video_path = tmp_video.name

        try:
            raw_segments: list[SegmentDict] = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}
            ]
            mock_extract.return_value = "/path/to/extracted.wav"
            mock_transcribe.return_value = raw_segments
            expected_srt = str(Path(video_path).with_suffix(".srt").resolve())
            mock_generate.return_value = expected_srt

            result = run_pipeline(
                video_path=video_path,
                skip_grammar=True,
            )

            mock_extract.assert_called_once()
            mock_transcribe.assert_called_once()
            mock_correct.assert_not_called()
            mock_generate.assert_called_once_with(raw_segments, expected_srt)
            self.assertEqual(result, expected_srt)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    def test_run_pipeline_non_existent_file(self):
        non_existent_path = "non_existent_video_file_9999.mp4"
        with self.assertRaises(FileNotFoundError) as ctx:
            run_pipeline(video_path=non_existent_path)

        self.assertIn("Input video file not found", str(ctx.exception))

    @patch("src.orchestration.pipeline.generate_srt")
    @patch("src.orchestration.pipeline.correct_grammar")
    @patch("src.orchestration.pipeline.transcribe_audio")
    @patch("src.orchestration.pipeline.extract_audio")
    def test_run_pipeline_with_target_language(
        self,
        mock_extract,
        mock_transcribe,
        mock_correct,
        mock_generate,
    ):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            video_path = tmp_video.name

        try:
            mock_extract.return_value = "/path/to/extracted.wav"
            mock_transcribe.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}
            ]
            mock_correct.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "হ্যালো বিশ্ব"}
            ]
            expected_srt = str(Path(video_path).with_suffix(".srt").resolve())
            mock_generate.return_value = expected_srt

            result = run_pipeline(
                video_path=video_path,
                target_language="Bangla",
            )

            mock_correct.assert_called_once_with(
                [{"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}],
                model_name="llama3.2:3b",
                target_language="Bangla",
                provider="ollama",
                api_key=None,
                llm_callback=ANY,
            )
            self.assertEqual(result, expected_srt)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    @patch("src.orchestration.pipeline.generate_srt")
    @patch("src.orchestration.pipeline.correct_grammar")
    @patch("src.orchestration.pipeline.transcribe_audio")
    @patch("src.orchestration.pipeline.extract_audio")
    def test_run_pipeline_with_gemini_provider(
        self,
        mock_extract,
        mock_transcribe,
        mock_correct,
        mock_generate,
    ):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            video_path = tmp_video.name

        try:
            mock_extract.return_value = "/path/to/extracted.wav"
            mock_transcribe.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}
            ]
            mock_correct.return_value = [
                {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello, world!"}
            ]
            expected_srt = str(Path(video_path).with_suffix(".srt").resolve())
            mock_generate.return_value = expected_srt

            result = run_pipeline(
                video_path=video_path,
                llm_provider="gemini",
                api_key="test_api_key",
            )

            mock_correct.assert_called_once_with(
                [{"id": 1, "start": 0.0, "end": 2.5, "text": "hello world"}],
                model_name="llama3.2:3b",
                target_language="English",
                provider="gemini",
                api_key="test_api_key",
                llm_callback=ANY,
            )
            self.assertEqual(result, expected_srt)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)


if __name__ == "__main__":
    unittest.main()
