import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ocr_pipeline.classifiers.page_type import classify_page_type
from ocr_pipeline.models import OcrItem


class PageTypeTest(unittest.TestCase):
    def test_plain_text_when_lines_share_left_edge(self):
        items = [
            OcrItem(text="긴 본문 문장입니다", confidence=0.95, box=[10, y, 210, y + 10])
            for y in range(0, 80, 16)
        ]
        result = classify_page_type(items)
        self.assertEqual(result.page_type, "plain-text")

    def test_multi_column_when_left_edges_cluster(self):
        items = []
        for x in (10, 160, 310):
            for y in range(0, 80, 20):
                items.append(OcrItem(text="문장", confidence=0.95, box=[x, y, x + 80, y + 10]))
        result = classify_page_type(items)
        self.assertIn(result.page_type, {"multi-column", "table"})
        self.assertGreater(result.confidence, 0.5)

    def test_unknown_without_boxes(self):
        result = classify_page_type([OcrItem(text="본문", confidence=0.9)])
        self.assertEqual(result.page_type, "unknown")


if __name__ == "__main__":
    unittest.main()

