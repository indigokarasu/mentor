import importlib.util
import os
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep_active", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unknown_owner_is_not_a_skill(tmp_path, monkeypatch):
    """Files at the journals root resolve to "unknown" and must not be an active skill."""
    module = load_module()
    journals = tmp_path / "journals"
    (journals / "ocas-alpha").mkdir(parents=True)
    (journals / "ocas-alpha" / "2026-10-01").mkdir()
    (journals / "ocas-alpha" / "2026-10-01" / "run.json").write_text('{"outcome":"success"}')
    (journals / "dispatch-wave-20260924.json.gz").write_bytes(b"x")

    monkeypatch.setattr(module, "JOURNALS_PATHS", [str(journals)])
    assert module.is_skill_name("ocas-alpha")
    assert not module.is_skill_name("unknown")
    assert module.resolve_skill_name(str(journals / "dispatch-wave-20260924.json.gz")) == "unknown"