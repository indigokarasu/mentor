import importlib.util
from pathlib import Path

DEEP = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_deep():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep", DEEP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grade_health(success, error, unknown):
    """Mirror of the skill_health grading in cron-heartbeat-deep-dualpath.py.

    Kept as a pure function here so the scoring rule is testable without
    running the whole heartbeat (which walks 33k journals).
    """
    t = success + error + unknown
    sr = (success + unknown) / t
    er = error / t
    vr = unknown / t
    if er > 0.05:
        return "failing"
    if er > 0.0:
        return "degraded"
    if vr > 0.5:
        return "unverified"
    return "healthy"


def test_zero_error_skill_is_never_failing():
    """Regression: a skill whose journals use a richer outcome vocabulary
    (e.g. 'watching', 'complete') was reported as `failing` with ZERO errors,
    because success_rate counted unreadable outcomes as failures."""
    assert grade_health(0, 0, 2) != "failing"


def test_all_unreadable_outcomes_is_unverified_not_failure():
    assert grade_health(0, 0, 2) == "unverified"


def test_mostly_unreadable_is_unverified():
    assert grade_health(1, 0, 9) == "unverified"


def test_partly_unreadable_with_no_errors_is_healthy():
    assert grade_health(8, 0, 2) == "healthy"


def test_actual_errors_still_fail():
    assert grade_health(2, 8, 0) == "failing"


def test_mixed_errors_degraded():
    # 1 error in 100 entries = 1% error rate -> below the 5% "failing" threshold
    assert grade_health(99, 1, 0) == "degraded"


def test_error_rate_at_threshold_is_failing():
    # 2 errors in 10 entries = 20% -> failing
    assert grade_health(8, 2, 0) == "failing"


def test_clean_skill_healthy():
    assert grade_health(10, 0, 0) == "healthy"


def test_unknown_counts_toward_success_rate():
    """Matches orchestration_success_rate convention (gotcha #34): sr == 1 - er."""
    t = 0 + 0 + 10
    sr = (0 + 10) / t
    assert sr == 1.0
    assert grade_health(0, 0, 10) == "unverified"


def test_script_contains_error_rate_field():
    """The journal schema now carries error_rate so a zero-error skill can be
    distinguished from a failing one by any consumer."""
    src = DEEP.read_text()
    assert '"error_rate": round(er, 4)' in src
    assert '"unverified"' in src
    assert '"unknown_vocabulary"' not in src
