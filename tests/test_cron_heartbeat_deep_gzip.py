import gzip
import importlib.util
import json
import os
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_gz(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(json.dumps(payload).encode())


def test_load_journal_entries_reads_gzipped_journal():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        gz = Path(td) / "journal.json.gz"
        _write_gz(gz, {"outcome": "success", "entries": [{"outcome": "success"}]})
        entries = module.load_journal_entries(str(gz))
        assert len(entries) == 1
        assert entries[0]["outcome"] == "success"


def test_load_journal_entries_reads_jsonl_style_gz():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        gz = Path(td) / "journal.jsonl.gz"
        _write_gz(gz, [{"outcome": "error", "detail": "boom"}])
        entries = module.load_journal_entries(str(gz))
        assert entries == [{"outcome": "error", "detail": "boom"}]


def test_discovery_includes_gzipped_journals(tmp_path, monkeypatch):
    """A compressed journal must still be discovered by the dual-path walk."""
    module = load_module()
    journals = tmp_path / "journals"
    gz = journals / "ocas-dispatch" / "2026-10-01" / "wave-1.json.gz"
    _write_gz(gz, {"outcome": "success", "entries": [{"outcome": "success"}]})

    monkeypatch.setattr(module, "JOURNALS_PATHS", [str(journals)])
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
    assert files == [str(gz)]