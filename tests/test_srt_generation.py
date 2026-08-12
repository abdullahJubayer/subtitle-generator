import os
import tempfile
import unittest
from src.schemas import SegmentDict
from src.srt_generation.generator import format_timestamp, generate_srt


class TestSRTGeneration(unittest.TestCase):

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(0.0), "00:00:00,000")
        self.assertEqual(format_timestamp(2.5), "00:00:02,500")
        self.assertEqual(format_timestamp(83.45), "00:01:23,450")
        self.assertEqual(format_timestamp(3661.123), "01:01:01,123")

    def test_generate_srt_success(self):
        segments: list[SegmentDict] = [
            {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello world!"},
            {"id": 2, "start": 2.5, "end": 5.0, "text": "This is a subtitle test."},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test_output.srt")
            result = generate_srt(segments, out_path)

            self.assertTrue(os.path.exists(result))

            with open(result, "r", encoding="utf-8") as f:
                content = f.read()

            expected_content = (
                "1\n"
                "00:00:00,000 --> 00:00:02,500\n"
                "Hello world!\n\n"
                "2\n"
                "00:00:02,500 --> 00:00:05,000\n"
                "This is a subtitle test.\n\n"
            )
            self.assertEqual(content, expected_content)


if __name__ == "__main__":
    unittest.main()
