import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from doctor import pdf_inspector_capability
from ocr_pipeline.engines.pdf_inspector import (
    PdfInspectionInfo,
    fallback_inspect_pdf,
    inspect_pdf,
    pdf_inspector_available,
    run_pdf_inspector,
)
from ocr_pipeline.router import ENGINES, run_ocr
from ocr_pipeline.utils import SUPPORTED_EXTENSIONS


class PdfInspectorIntegrationTest(unittest.TestCase):
    def test_supported_extensions_includes_pdf(self):
        self.assertIn(".pdf", SUPPORTED_EXTENSIONS)
        self.assertIn("pdf-inspector", ENGINES)

    def test_pdf_inspector_capability_format(self):
        cap = pdf_inspector_capability()
        self.assertIn("available", cap)
        self.assertIn("reason", cap)
        self.assertIsInstance(cap["available"], bool)

    def test_run_pdf_inspector_mock(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "dummy.pdf"
            pdf_path.write_text("%PDF-1.4 dummy", encoding="utf-8")

            res = run_pdf_inspector(pdf_path)
            self.assertEqual(res.engine, "pdf-inspector")
            self.assertEqual(res.input_path, pdf_path)
            self.assertIn("pdf_inspector_installed", res.runtime_metadata)

    def test_router_handles_pdf_inspector_engine(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "test_doc.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 header text\ntrailer\n%%EOF")
            out_dir = Path(tmp_dir) / "out"

            res = run_ocr(pdf_path, engine="pdf-inspector", page_mode="auto", lang="korean", out_dir=out_dir)
            self.assertEqual(res.engine, "pdf-inspector")
            self.assertIn("pdf_inspector", res.runtime_metadata.get("capabilities", {}))


if __name__ == "__main__":
    unittest.main()
