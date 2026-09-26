"""Tests for the static CI unit; no Helm/Terraform or third-party Python dependencies."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
from snapshot import compare
from static import forbidden


class StaticCITests(unittest.TestCase):
    def test_changed_and_missing_baseline_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual, expected = root / "actual.json", root / "expected.json"
            actual.write_text('{"disk": 200}\n')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(compare(expected, actual, root), 1)
                expected.write_text('{"disk": 100}\n')
                self.assertEqual(compare(expected, actual, root), 1)
                expected.write_text(actual.read_text())
                self.assertEqual(compare(expected, actual, root), 0)


    def test_ci_cannot_update_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("{}")
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
                with self.assertRaises(ValueError):
                    compare(path, path, path.parent, update=True)


    def test_sensitive_file_rules(self):
        for path in ('terraform/local.tfstate.backup', 'terraform/prod.tfvars', 'keys/id_ed25519'):
            self.assertTrue(forbidden(path))
        for path in ('terraform/.terraform.lock.hcl', '.env.example', 'tests/snapshots/terraform.json'):
            self.assertFalse(forbidden(path))



if __name__ == "__main__":
    unittest.main()
