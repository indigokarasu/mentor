"""Unit tests for ocas-mentor scripts (run: python3 -m unittest discover -s tests)."""
import gzip
import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "correct_active_skills_30d.py"


def load_module():
    spec = importlib.util.spec_from_file_location("correct_active_skills", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mk_journal(journals: Path, skill: str, age_days: int) -> Path:
    d = journals / skill / "2026-10-01"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{skill}-run.json"
    p.write_text('{"outcome": "success"}')
    old = time.time() - age_days * 86400
    os.utime(p, (old, old))
    return p


def _mk_gz(journals: Path, skill: str, age_days: int) -> Path:
    d = journals / skill / "2026-10-01"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{skill}-run.json.gz"
    with gzip.open(p, "wb") as f:
        f.write(b'{"outcome": "success"}')
    old = time.time() - age_days * 86400
    os.utime(p, (old, old))
    return p


class TestCorrectActiveSkills30d(unittest.TestCase):
    def test_counts_plain_journals(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            _mk_journal(journals, "ocas-alpha", 1)
            _mk_journal(journals, "ocas-beta", 2)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 2)

    def test_counts_gzipped_journals(self):
        """Genie compresses old journals to .json.gz; those must still count."""
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            _mk_gz(journals, "ocas-gamma", 3)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 1)

    def test_counts_mixed_plain_and_gz(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            _mk_journal(journals, "ocas-alpha", 1)
            _mk_gz(journals, "ocas-beta", 2)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 2)

    def test_ocas_only_excludes_non_ocas(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            _mk_journal(journals, "ocas-alpha", 1)
            _mk_gz(journals, "browser-vision", 1)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 2)
            self.assertEqual(module.count_active_skills_30d_ocas(), 1)

    def test_root_level_file_is_not_a_skill(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            journals.mkdir(parents=True, exist_ok=True)
            (journals / "dispatch-wave-20260924.json.gz").write_bytes(b"x")
            _mk_journal(journals, "ocas-alpha", 1)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 1)

    def test_excludes_journals_older_than_30_days(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            _mk_journal(journals, "ocas-alpha", 1)
            _mk_gz(journals, "ocas-stale", 45)
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 1)

    def test_counts_file_sitting_directly_in_skill_dir(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as td:
            journals = Path(td) / "journals"
            d = journals / "ocas-genie"
            d.mkdir(parents=True, exist_ok=True)
            (d / "runs.jsonl").write_text('{"outcome": "success"}\n')
            module.JOURNALS_DIRS = [str(journals)]
            self.assertEqual(module.count_active_skills_30d(), 1)
