"""Unit tests for ocas-mentor scripts (run: python3 -m unittest discover -s tests)."""
import os
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-light.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_light", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCronHeartbeatLight(unittest.TestCase):
    def test_extract_skill_from_profile_scoped_journal_path(self):
        module = load_module()
        path = os.path.expanduser("~/.hermes/profiles/indigo/commons/journals/ocas-mentor/2026-07-09/mentor-light-20260709T133823Z.json")
        self.assertEqual(module.extract_skill_from_journal_path(path), "ocas-mentor")

    def test_extract_skill_from_shared_commons_journal_path(self):
        module = load_module()
        path = os.path.expanduser("~/.hermes/commons/journals/ocas-praxis/2026-07-09/praxis-run.json")
        self.assertEqual(module.extract_skill_from_journal_path(path), "ocas-praxis")
