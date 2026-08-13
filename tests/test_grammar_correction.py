import os
import unittest
from unittest.mock import MagicMock, patch
from src.grammar_correction.corrector import correct_grammar
from src.grammar_correction.llm_providers import call_llm_provider
from src.schemas import SegmentDict, SubtitleResponse, SubtitleSegment


class TestGrammarCorrection(unittest.TestCase):

    @patch("ollama.chat")
    def test_correct_grammar_ollama_success(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"segments": [{"id": 1, "text": "Hello, world!"}, {"id": 2, "text": "This is a test."}]}'
        mock_chat.return_value = mock_response

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
            {"id": 2, "start": 2.0, "end": 4.0, "text": "this is test"},
        ]

        result = correct_grammar(segments, model_name="llama3.1", provider="ollama")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "Hello, world!")
        self.assertEqual(result[1]["text"], "This is a test.")
        # Check timestamps preserved
        self.assertEqual(result[0]["start"], 0.0)
        self.assertEqual(result[0]["end"], 2.0)
        self.assertEqual(result[1]["start"], 2.0)
        self.assertEqual(result[1]["end"], 4.0)

    @patch("src.grammar_correction.corrector.call_llm_provider")
    def test_correct_grammar_gemini_success(self, mock_call_llm):
        mock_call_llm.return_value = '{"segments": [{"id": 1, "text": "Hello, world!"}]}'

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(
            segments,
            model_name="gemini-2.5-flash",
            provider="gemini",
            api_key="test_api_key",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hello, world!")
        mock_call_llm.assert_called_once()
        _, kwargs = mock_call_llm.call_args
        self.assertEqual(kwargs["provider"], "gemini")
        self.assertEqual(kwargs["api_key"], "test_api_key")

    @patch("ollama.chat")
    def test_correct_grammar_ollama_failure_fallback(self, mock_chat):
        mock_chat.side_effect = Exception("Ollama offline or model missing")

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(segments, model_name="llama3.1", provider="ollama")

        # Must fallback gracefully to original segment text
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "hello world")

    @patch("src.grammar_correction.corrector.call_llm_provider")
    def test_correct_grammar_gemini_failure_fallback(self, mock_call_llm):
        mock_call_llm.side_effect = Exception("Gemini API Rate Limit / Invalid Key")

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(
            segments,
            model_name="gemini-2.5-flash",
            provider="gemini",
            api_key="invalid_key",
        )

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

        correct_grammar(segments, model_name="llama3.1", provider="ollama")

        # Expect 2 batch calls (40 segments + 10 segments)
        self.assertEqual(mock_chat.call_count, 2)

    def test_correct_grammar_empty_input(self):
        result = correct_grammar([])
        self.assertEqual(result, [])

    @patch("ollama.chat")
    def test_correct_grammar_translation_prompt(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"segments": [{"id": 1, "text": "Hola mundo"}]}'
        mock_chat.return_value = mock_response

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(segments, model_name="llama3.2:3b", target_language="Spanish")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hola mundo")

        mock_chat.assert_called_once()
        _, kwargs = mock_chat.call_args
        messages = kwargs["messages"]
        system_prompt = messages[0]["content"]
        self.assertIn("Spanish", system_prompt)
        self.assertIn("ABSOLUTELY NO literal word-for-word or robotic machine translations", system_prompt)

    @patch("ollama.chat")
    def test_correct_grammar_english_prompt(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"segments": [{"id": 1, "text": "Hello, world!"}]}'
        mock_chat.return_value = mock_response

        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"},
        ]

        result = correct_grammar(segments, target_language="English")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hello, world!")

        mock_chat.assert_called_once()
        _, kwargs = mock_chat.call_args
        messages = kwargs["messages"]
        system_prompt = messages[0]["content"]
        self.assertIn("film and TV subtitle editor", system_prompt)

    @patch("google.genai.Client")
    def test_call_llm_provider_gemini_success(self, mock_genai_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"segments": [{"id": 1, "text": "Hello, world!"}]}'
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client_cls.return_value = mock_client

        messages = [
            {"role": "system", "content": "You are an editor."},
            {"role": "user", "content": '[{"id": 1, "text": "hello world"}]'},
        ]

        result = call_llm_provider(
            provider="gemini",
            model_name="gemini-2.5-flash",
            messages=messages,
            api_key="test-api-key",
        )

        self.assertEqual(result, '{"segments": [{"id": 1, "text": "Hello, world!"}]}')
        mock_genai_client_cls.assert_called_once_with(api_key="test-api-key")

    def test_call_llm_provider_gemini_missing_api_key(self):
        messages = [{"role": "user", "content": "hi"}]
        env_backup = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        try:
            with self.assertRaises(ValueError) as ctx:
                call_llm_provider(
                    provider="gemini",
                    model_name="gemini-2.5-flash",
                    messages=messages,
                    api_key=None,
                )
            self.assertIn("Gemini API key is missing", str(ctx.exception))
        finally:
            if env_backup:
                os.environ["GEMINI_API_KEY"] = env_backup

    @patch("google.genai.Client")
    def test_call_llm_provider_gemini_env_key(self, mock_genai_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"segments": []}'
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client_cls.return_value = mock_client

        messages = [{"role": "user", "content": "hi"}]
        env_backup = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "env-secret-key"

        try:
            call_llm_provider(
                provider="gemini",
                model_name="gemini-2.5-flash",
                messages=messages,
            )
            mock_genai_client_cls.assert_called_once_with(api_key="env-secret-key")
        finally:
            if env_backup is not None:
                os.environ["GEMINI_API_KEY"] = env_backup
            else:
                os.environ.pop("GEMINI_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
