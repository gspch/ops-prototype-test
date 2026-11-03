"""Rules are tested without any API call or network access.

Run from the repository root:  python -m unittest discover tests
"""
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402
from rules import (  # noqa: E402
    flags_from_registers, get_all_flags, group_by_action, load_registers, working_days_between,
)

CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text())
TODAY = CONFIG["today"]  # yaml parses 2026-11-06 as a date
CRITICAL = CONFIG["critical_path"]
DUE_SOON = CONFIG["thresholds"]["due_soon_working_days"]
BLOCKED = CONFIG["thresholds"]["blocked_escalate_working_days"]
CLIENT = str(ROOT / "data" / "register_client.csv")
MISTRAL = str(ROOT / "data" / "register_mistral.csv")

# Complete expected flags on 2026-11-06 (README, "Expected flags").
EXPECTED = {
    "PLT-031": {"overdue", "critical_and_late"},
    "PLT-040": {"overdue", "no_owner", "cross_side_blocker", "critical_and_late"},
    "PLT-041": {"due_soon_critical", "blocked_too_long"},
    "PLT-020": {"overdue"},
    "UC-008": {"overdue", "blocked_too_long"},
    "DSC-003": {"no_owner"},
}
UNFLAGGED = {"PLT-035", "INF-002", "UC-010"}
ESCALATE_RULES = {"blocked_too_long", "cross_side_blocker", "critical_and_late"}


class TestWorkingDays(unittest.TestCase):
    def test_excludes_start_includes_end(self):
        self.assertEqual(working_days_between(date(2026, 10, 28), date(2026, 11, 6)), 7)

    def test_skips_weekend(self):
        self.assertEqual(working_days_between(date(2026, 11, 6), date(2026, 11, 9)), 1)

    def test_same_day_is_zero(self):
        self.assertEqual(working_days_between(date(2026, 11, 6), date(2026, 11, 6)), 0)


class TestExpectedFlags(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flags = get_all_flags(CLIENT, MISTRAL, TODAY, CRITICAL, DUE_SOON, BLOCKED)
        cls.by_action = {k: {r for r, _ in v} for k, v in group_by_action(cls.flags).items()}

    def test_exact_flags_per_action(self):
        for action_id, rules in EXPECTED.items():
            with self.subTest(action_id=action_id):
                self.assertEqual(self.by_action.get(action_id, set()), rules)

    def test_no_unexpected_action_flagged(self):
        self.assertEqual(set(self.by_action) & UNFLAGGED, set())
        self.assertEqual(set(self.by_action), set(EXPECTED))

    def test_levels(self):
        for action_id, rule, level in self.flags:
            with self.subTest(action_id=action_id, rule=rule):
                self.assertEqual(level, "escalate" if rule in ESCALATE_RULES else "nudge")

    def test_new_action_without_owner_is_flagged(self):
        client, mistral = load_registers(CLIENT, MISTRAL)
        client.append({
            "id": "UC-011", "description": "Book a demo with the plant managers", "owner": "",
            "side": "Client", "workstream": "UC", "due_date": "", "status": "Not started",
            "depends_on": "", "source": "extracted", "last_update": "2026-11-06",
        })
        flags = flags_from_registers(client, mistral, TODAY, CRITICAL, DUE_SOON, BLOCKED)
        self.assertIn(("UC-011", "no_owner", "nudge"), flags)

    def test_done_action_raises_nothing(self):
        client, mistral = load_registers(CLIENT, MISTRAL)
        for row in client:
            if row["id"] == "PLT-040":
                row["status"] = "Done"
        flags = flags_from_registers(client, mistral, TODAY, CRITICAL, DUE_SOON, BLOCKED)
        rules = {r for a, r, _ in flags if a == "PLT-040"}
        self.assertEqual(rules, {"no_owner"})


if __name__ == "__main__":
    unittest.main()
