import unittest
from unittest.mock import MagicMock, patch
from src.grammar_correction.corrector import correct_grammar
from src.schemas import SegmentDict, SubtitleResponse, SubtitleSegment


class TestGrammarCorrection(unittest.TestCase):

    @patch("ollama.chat")
    def test_correct_grammar_success(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"segments": [{"id": 1, "text": "Hello, world!"}, {"id": 2, "text": "This is a test."}]}'
        mock_chat.return_value = mock_response

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
            {"id": 2, "start": 2.0, "end": 4.0, "text": "this is test"},
        ]

        result = correct_grammar(segments, model_name="llama3.1")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "Hello, world!")
        self.assertEqual(result[1]["text"], "This is a test.")
        # Check timestamps preserved
        self.assertEqual(result[0]["start"], 0.0)
        self.assertEqual(result[0]["end"], 2.0)
        self.assertEqual(result[1]["start"], 2.0)
        self.assertEqual(result[1]["end"], 4.0)

    @patch("ollama.chat")
    def test_correct_grammar_ollama_failure_fallback(self, mock_chat):
        mock_chat.side_effect = Exception("Ollama offline or model missing")

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(segments, model_name="llama3.1")

        # Must fallback gracefully to original segment text
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "hello world")

    @patch("ollama.chat")
    def test_correct_grammar_batching(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"segments": []}'
        mock_chat.return_value = mock_response

        # Create 50 segments to test chunking (> 40 batch size)
        segments: list[SegmentDict] = [
            {"id": i, "start": float(i), "end": float(i + 1), "text": f"segment {i}"}
            for i in range(1, 51)
        ]

        correct_grammar(segments, model_name="llama3.1")

        # Expect 2 batch calls (40 segments + 10 segments)
        self.assertEqual(mock_chat.call_count, 2)

    def test_correct_grammar_empty_input(self):
        result = correct_grammar([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
