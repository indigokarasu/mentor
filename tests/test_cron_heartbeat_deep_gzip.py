"""Unit tests for ocas-mentor scripts (run: python3 -m unittest discover -s tests)."""
import gzip
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_gz(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(payload).encode())


class TestCronHeartbeatDeepGzip(unittest.TestCase):
    def test_load_journal_entries_reads_gzipped_journal(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            gz = Path(td) / "journal.json.gz"
            _write_gz(gz, {"outcome": "success", "entries": [{"outcome": "success"}]})
            entries = module.load_journal_entries(str(gz))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["outcome"], "success")

    def test_load_journal_entries_reads_jsonl_style_gz(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            gz = Path(td) / "journal.jsonl.gz"
            _write_gz(gz, [{"outcome": "error", "detail": "boom"}])
            self.assertEqual(module.load_journal_entries(str(gz)), [{"outcome": "error", "detail": "boom"}])

    def test_discovery_includes_gzipped_journals(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            gz = journals / "ocas-dispatch" / "2026-10-01" / "wave-1.json.gz"
            _write_gz(gz, {"outcome": "success", "entries": [{"outcome": "success"}]})
            module.JOURNALS_PATHS = [str(journals)]
            seen, files = set(), []
            for base_path in module.JOURNALS_PATHS:
                if not os.path.isdir(base_path):
                    continue
                for root, _dirs, names in os.walk(base_path):
                    for fn in names:
                        if module.is_journal_file(fn):
                            fp = os.path.join(root, fn)
                            if fp not in seen:
                                seen.add(fp)
                                files.append(fp)
            self.assertEqual(files, [str(gz)])
