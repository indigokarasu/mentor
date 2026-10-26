"""Unit tests for ocas-mentor scripts (run: python3 -m unittest discover -s tests)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep_active", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestActiveSkillFilter(unittest.TestCase):
    def test_unknown_owner_is_not_a_skill(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            (journals / "ocas-alpha" / "2026-10-01").mkdir(parents=True)
            (journals / "ocas-alpha" / "2026-10-01" / "run.json").write_text('{"outcome":"success"}')
            (journals / "dispatch-wave-20260924.json.gz").write_bytes(b"x")
            module.JOURNALS_PATHS = [str(journals)]
            self.assertTrue(module.is_skill_name("ocas-alpha"))
            self.assertFalse(module.is_skill_name("unknown"))
            self.assertEqual(module.resolve_skill_name(str(journals / "dispatch-wave-20260924.json.gz")), "unknown")
