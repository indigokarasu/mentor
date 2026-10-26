"""Unit tests for ocas-mentor scripts (run: python3 -m unittest discover -s tests)."""
import importlib.util
import unittest
from pathlib import Path

DEEP = Path(__file__).resolve().parents[1] / "scripts" / "cron-heartbeat-deep-dualpath.py"


def load_deep():
    spec = importlib.util.spec_from_file_location("cron_heartbeat_deep", DEEP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grade_health(success, error, unknown):
    """Mirror of the skill_health grading in cron-heartbeat-deep-dualpath.py."""
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


class TestSkillHealthScoring(unittest.TestCase):
    def test_zero_error_skill_is_never_failing(self):
        """Regression: a skill whose journals use a richer outcome vocabulary
        was reported as `failing` with ZERO errors."""
        self.assertNotEqual(grade_health(0, 0, 2), "failing")

    def test_all_unreadable_outcomes_is_unverified_not_failure(self):
        self.assertEqual(grade_health(0, 0, 2), "unverified")

    def test_mostly_unreadable_is_unverified(self):
        self.assertEqual(grade_health(1, 0, 9), "unverified")

    def test_partly_unreadable_with_no_errors_is_healthy(self):
        self.assertEqual(grade_health(8, 0, 2), "healthy")

    def test_actual_errors_still_fail(self):
        self.assertEqual(grade_health(2, 8, 0), "failing")

    def test_mixed_errors_degraded(self):
        self.assertEqual(grade_health(99, 1, 0), "degraded")

    def test_error_rate_at_threshold_is_failing(self):
        self.assertEqual(grade_health(8, 2, 0), "failing")

    def test_clean_skill_healthy(self):
        self.assertEqual(grade_health(10, 0, 0), "healthy")

    def test_unknown_counts_toward_success_rate(self):
        """Matches orchestration_success_rate convention (gotcha #34)."""
        t = 0 + 0 + 10
        sr = (0 + 10) / t
        self.assertEqual(sr, 1.0)
        self.assertEqual(grade_health(0, 0, 10), "unverified")

    def test_script_contains_error_rate_field(self):
        module = load_deep()
        src = str(module.__file__)
        with open(src) as f:
            content = f.read()
        self.assertIn('"error_rate": round(er, 4)', content)
        self.assertIn('"unverified"', content)
        self.assertNotIn('"unknown_vocabulary"', content)
