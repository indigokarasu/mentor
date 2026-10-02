import importlib.util
import os
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "correct_active_skills_30d.py"


def load_module():
    spec = importlib.util.spec_from_file_location("correct_active_skills", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
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
    import gzip
    d = journals / skill / "2026-10-01"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{skill}-run.json.gz"
    with gzip.open(p, "wb") as f:
        f.write(b'{"outcome": "success"}')
    old = time.time() - age_days * 86400
    os.utime(p, (old, old))
    return p


def test_counts_plain_journals(tmp_path, monkeypatch):
    module = load_module()
    journals = tmp_path / "journals"
    _mk_journal(journals, "ocas-alpha", 1)
    _mk_journal(journals, "ocas-beta", 2)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 2


def test_counts_gzipped_journals(tmp_path, monkeypatch):
    """Genie compresses old journals to .json.gz; those must still count.

    The old `find -name '*.json'` pipeline returned 0 for a gz-only skill.
    """
    module = load_module()
    journals = tmp_path / "journals"
    _mk_gz(journals, "ocas-gamma", 3)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 1


def test_counts_mixed_plain_and_gz(tmp_path, monkeypatch):
    module = load_module()
    journals = tmp_path / "journals"
    _mk_journal(journals, "ocas-alpha", 1)
    _mk_gz(journals, "ocas-beta", 2)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 2


def test_ocas_only_excludes_non_ocas(tmp_path, monkeypatch):
    module = load_module()
    journals = tmp_path / "journals"
    _mk_journal(journals, "ocas-alpha", 1)
    _mk_gz(journals, "browser-vision", 1)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 2
    assert module.count_active_skills_30d_ocas() == 1


def test_root_level_file_is_not_a_skill(tmp_path, monkeypatch):
    """A file directly in journals/ has no skill owner and must not be counted."""
    module = load_module()
    journals = tmp_path / "journals"
    journals.mkdir(parents=True, exist_ok=True)
    (journals / "dispatch-wave-20260924.json.gz").write_bytes(b"x")
    _mk_journal(journals, "ocas-alpha", 1)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 1


def test_excludes_journals_older_than_30_days(tmp_path, monkeypatch):
    module = load_module()
    journals = tmp_path / "journals"
    _mk_journal(journals, "ocas-alpha", 1)
    _mk_gz(journals, "ocas-stale", 45)
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 1


def test_counts_file_sitting_directly_in_skill_dir(tmp_path, monkeypatch):
    """ocas-genie writes `ocas-genie/runs.jsonl` with no date subdirectory.

    Ownership is per FILE (first path component), not per directory: deriving the owner
    from the walk directory silently dropped every skill whose only journal sits
    directly in the skill folder.
    """
    module = load_module()
    journals = tmp_path / "journals"
    d = journals / "ocas-genie"
    d.mkdir(parents=True, exist_ok=True)
    (d / "runs.jsonl").write_text('{"outcome": "success"}\n')
    monkeypatch.setattr(module, "JOURNALS_DIRS", [str(journals)])
    assert module.count_active_skills_30d() == 1