import importlib.util
import os
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep_names", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_name_from_nested_journal_path():
    module = load_module()
    path = os.path.expanduser(
        "~/.hermes/commons/journals/ocas-dispatch/2026-10-01/wave-1.json.gz"
    )
    assert module.resolve_skill_name(path) == "ocas-dispatch"


def test_root_level_file_is_not_a_skill_name():
    """A dispatch wave file sitting directly in journals/ has no skill directory.

    Its filename was being returned as a skill name, which inflated skills_total and
    printed phantom rows like `dispatch-wave-20260924T132000Z.json.gz` in skill health.
    """
    module = load_module()
    path = os.path.expanduser("~/.hermes/commons/journals/dispatch-wave-20260924T132000Z.json.gz")
    assert module.resolve_skill_name(path) == "unknown"


def test_root_level_plain_json_is_not_a_skill_name():
    module = load_module()
    path = os.path.expanduser("~/.hermes/commons/journals/journals_evaluated.jsonl")
    assert module.resolve_skill_name(path) == "unknown"


def test_unrelated_path_falls_back_to_unknown():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        assert module.resolve_skill_name(os.path.join(td, "stray.json")) == "unknown"