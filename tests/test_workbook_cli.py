import json
from pathlib import Path
import tempfile
import unittest

from keyword_extractor.cli import run
from keyword_extractor.workbook import read_rows
from scripts.generate_demo_xlsx import generate


class WorkbookAndCliTests(unittest.TestCase):
    def test_reads_synthetic_xlsx(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.xlsx"
            generate(path)
            rows = read_rows(path)
        self.assertEqual(rows[0]["sku"], "SYN-001")
        self.assertEqual(len(rows), 6)

    def test_cli_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "keywords.json"
            code = run(["examples/products.csv", "--columns", "title", "description", "--top", "4", "--output", str(output)])
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(result["documents"], 6)
        self.assertEqual(len(result["keywords"]), 4)

    def test_unknown_column_returns_usage_error(self) -> None:
        self.assertEqual(run(["examples/products.csv", "--columns", "missing"]), 2)


if __name__ == "__main__":
    unittest.main()
