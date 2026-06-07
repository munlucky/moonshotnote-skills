import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReviewCompatibilityTest(unittest.TestCase):
    def test_review_low_confidence_accepts_canonical_items(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow is not installed in this Python environment")

        script = Path(__file__).resolve().parents[1] / "scripts" / "review_low_confidence.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "page.png"
            Image.new("RGB", (80, 80), "white").save(image_path)
            payload_path = root / "page.paddle.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "input": str(image_path),
                        "items": [
                            {
                                "text": "검토 필요",
                                "confidence": 0.5,
                                "box": [[10, 10], [40, 10], [40, 30], [10, 30]],
                                "source_engine": "paddle",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [sys.executable, str(script), str(payload_path), "--threshold", "0.75"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = root / "low-confidence-review" / "low_confidence_manifest.json"
            self.assertTrue(manifest.exists())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["crop_count"], 1)


if __name__ == "__main__":
    unittest.main()

