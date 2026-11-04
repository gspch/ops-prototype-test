"""Step 4. Deterministic rules on both registers. No model call here."""
import csv
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

Flag = Tuple[str, str, str]  # (action_id, rule_name, level)


def load_csv(path: str) -> List[Dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_registers(client_path: str, mistral_path: str) -> Tuple[List[Dict], List[Dict]]:
    return load_csv(client_path), load_csv(mistral_path)


def to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def working_days_between(start, end) -> int:
    """Working days strictly after start, up to and including end.

    Saturdays and Sundays are skipped. Returns 0 if end is not after start.
    Example: from Wednesday 2026-10-28 to Friday 2026-11-06 gives 7.
    """
    start, end = to_date(start), to_date(end)
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def is_done(action: Dict) -> bool:
    return (action.get("status") or "").strip().lower() == "done"


def check_overdue(action: Dict, today) -> bool:
    if is_done(action) or not action.get("due_date"):
        return False
    return to_date(action["due_date"]) < to_date(today)


def check_no_owner(action: Dict) -> bool:
    return not (action.get("owner") or "").strip()


def check_due_soon_critical(action: Dict, today, critical_path: List[str], due_soon_days: int) -> bool:
    if is_done(action) or action.get("id") not in critical_path or not action.get("due_date"):
        return False
    due = to_date(action["due_date"])
    if due < to_date(today):
        return False  # already covered by overdue
    return working_days_between(today, due) <= due_soon_days


def check_blocked_too_long(action: Dict, today, blocked_days: int) -> bool:
    if (action.get("status") or "").strip().lower() != "blocked" or not action.get("last_update"):
        return False
    return working_days_between(action["last_update"], today) > blocked_days


def check_cross_side_blocker(action: Dict, other_register: List[Dict]) -> bool:
    if is_done(action) or not action.get("id"):
        return False
    return any(o.get("depends_on") == action["id"] for o in other_register)


def check_critical_and_late(action: Dict, today, critical_path: List[str]) -> bool:
    if action.get("id") not in critical_path:
        return False
    return check_overdue(action, today) or check_no_owner(action)


def get_flags_for_action(action: Dict, today, critical_path: List[str],
                         due_soon_days: int, blocked_days: int,
                         other_register: List[Dict]) -> List[Flag]:
    action_id = action.get("id", "UNKNOWN")
    checks = [
        ("overdue", "nudge", check_overdue(action, today)),
        ("no_owner", "nudge", check_no_owner(action)),
        ("due_soon_critical", "nudge", check_due_soon_critical(action, today, critical_path, due_soon_days)),
        ("blocked_too_long", "escalate", check_blocked_too_long(action, today, blocked_days)),
        ("cross_side_blocker", "escalate", check_cross_side_blocker(action, other_register)),
        ("critical_and_late", "escalate", check_critical_and_late(action, today, critical_path)),
    ]
    return [(action_id, rule, level) for rule, level, hit in checks if hit]


def flags_from_registers(client: List[Dict], mistral: List[Dict], today,
                         critical_path: List[str], due_soon_days: int,
                         blocked_days: int) -> List[Flag]:
    flags: List[Flag] = []
    for action in client:
        flags += get_flags_for_action(action, today, critical_path, due_soon_days, blocked_days, mistral)
    for action in mistral:
        flags += get_flags_for_action(action, today, critical_path, due_soon_days, blocked_days, client)
    return flags


def get_all_flags(client_register_path: str, mistral_register_path: str, today,
                  critical_path: List[str], due_soon_days: int, blocked_days: int) -> List[Flag]:
    client, mistral = load_registers(client_register_path, mistral_register_path)
    return flags_from_registers(client, mistral, today, critical_path, due_soon_days, blocked_days)


def group_by_action(flags: List[Flag]) -> Dict[str, List[Tuple[str, str]]]:
    grouped: Dict[str, List[Tuple[str, str]]] = {}
    for action_id, rule, level in flags:
        grouped.setdefault(action_id, []).append((rule, level))
    return grouped
