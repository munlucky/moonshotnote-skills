import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ocr_pipeline.engines.paddle import extract_from_mapping
from ocr_pipeline.models import OcrResult
from ocr_pipeline.output import result_payload, write_outputs


class CanonicalSchemaTest(unittest.TestCase):
    def test_paddle_mapping_keeps_legacy_item_keys_and_adds_metadata(self):
        items = extract_from_mapping(
            {
                "rec_texts": ["첫 문장", "둘째 문장"],
                "rec_scores": [0.98, 0.5],
                "rec_boxes": [
                    [[0, 0], [10, 0], [10, 10], [0, 10]],
                    [[0, 20], [10, 20], [10, 30], [0, 30]],
                ],
            }
        )
        result = OcrResult(
            engine="paddle",
            requested_engine="auto",
            input_path=Path("sample.png"),
            items=items,
            page_type="plain-text",
            page_type_confidence=0.9,
        )

        payload = result_payload(result)

        self.assertEqual(payload["engine"], "paddle")
        self.assertEqual(payload["requested_engine"], "auto")
        self.assertIn("text", payload)
        self.assertIn("items", payload)
        self.assertIn("warnings", payload)
        self.assertIn("low_confidence", payload)
        self.assertEqual(payload["items"][0]["text"], "첫 문장")
        self.assertIsNotNone(payload["items"][0]["box"])
        self.assertEqual(payload["items"][0]["source_engine"], "paddle")
        self.assertEqual(payload["low_confidence"], ["둘째 문장"])

    def test_write_outputs_uses_requested_out_dir_and_actual_engine_prefix(self):
        items = extract_from_mapping({"rec_texts": ["본문"], "rec_scores": [0.99], "rec_boxes": [[0, 0, 10, 10]]})
        result = OcrResult(
            engine="paddle",
            requested_engine="auto",
            input_path=Path("capture.png"),
            items=items,
            page_type="plain-text",
            page_type_confidence=0.8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = write_outputs(result, out_dir, Namespace(json=True, md=False, all=False))
            self.assertEqual(written["txt"].name, "capture.paddle.txt")
            self.assertEqual(written["json"].name, "capture.paddle.json")
            payload = json.loads(written["json"].read_text(encoding="utf-8"))
            self.assertEqual(payload["requested_engine"], "auto")


if __name__ == "__main__":
    unittest.main()

