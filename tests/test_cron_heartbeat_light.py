import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-light.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_light", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_skill_from_profile_scoped_journal_path():
    module = load_module()
    path = "/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/2026-07-09/mentor-light-20260709T133823Z.json"
    assert module.extract_skill_from_journal_path(path) == "ocas-mentor"


def test_extract_skill_from_shared_commons_journal_path():
    module = load_module()
    path = "/root/.hermes/commons/journals/ocas-praxis/2026-07-09/praxis-run.json"
    assert module.extract_skill_from_journal_path(path) == "ocas-praxis"
