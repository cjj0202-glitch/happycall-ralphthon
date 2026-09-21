import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("log_inventory", Path(__file__).resolve().parents[1] / "scripts/log_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class LogInventoryTests(unittest.TestCase):
    def test_metadata_does_not_include_conversation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            path.write_text('{"type":"message","text":"private test content"}\n', encoding="utf-8")
            result = inventory.inspect(path)
            self.assertEqual(result["json_lines"], 1)
            self.assertEqual(result["invalid_lines"], 0)
            self.assertNotIn("private test content", str(result))
            self.assertEqual(len(result["sha256"]), 64)

    def test_bad_json_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{}\ninvalid\n[]\n\n', encoding="utf-8")
            result = inventory.inspect(path)
            self.assertEqual(result["json_lines"], 3)
            self.assertEqual(result["invalid_lines"], 2)
            self.assertEqual(result["blank_lines"], 1)

    def test_empty_log_has_no_valid_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.jsonl"
            path.write_bytes(b"")
            self.assertEqual(inventory.inspect(path)["json_lines"], 0)
