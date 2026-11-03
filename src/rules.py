import csv
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pathlib import Path

def load_registers(client_path: str, mistral_path: str) -> Tuple[List[Dict], List[Dict]]:
    """Load both registers from CSV files."""
    def load_csv(path: str) -> List[Dict]:
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            return [row for row in reader]

    client_register = load_csv(client_path)
    mistral_register = load_csv(mistral_path)
    return client_register, mistral_register

def is_working_day(date: datetime) -> bool:
    """Check if a date is a working day (Monday-Friday)."""
    return date.weekday() < 5  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

def working_days_between(start_date: datetime, end_date: datetime) -> int:
    """Calculate the number of working days between two dates (inclusive of both)."""
    if start_date > end_date:
        return 0

    count = 0
    current = start_date
    while current <= end_date:
        if is_working_day(current):
            count += 1
        current += timedelta(days=1)
    return count

def check_overdue(action: Dict, today: datetime) -> bool:
    """Check if action is overdue: due_date before today and status not Done."""
    if action.get('status') == 'Done':
        return False
    due_date_str = action.get('due_date')
    if not due_date_str:
        return False
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    return due_date < today

def check_no_owner(action: Dict) -> bool:
    """Check if action has no owner."""
    return not action.get('owner') or action.get('owner').strip() == ''

def check_due_soon_critical(action: Dict, today: datetime, critical_path: List[str], due_soon_days: int) -> bool:
    """Check if action is on critical path, due within N working days, and not Done."""
    if action.get('status') == 'Done':
        return False
    if action.get('id') not in critical_path:
        return False
    due_date_str = action.get('due_date')
    if not due_date_str:
        return False
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    if due_date < today:
        return False
    working_days = working_days_between(today, due_date)
    return working_days <= due_soon_days

def check_blocked_too_long(action: Dict, today: datetime, blocked_days: int) -> bool:
    """Check if action is blocked for more than N working days."""
    if action.get('status') != 'Blocked':
        return False
    last_update_str = action.get('last_update')
    if not last_update_str:
        return False
    last_update = datetime.strptime(last_update_str, '%Y-%m-%d')
    working_days = working_days_between(last_update, today)
    return working_days > blocked_days

def check_cross_side_blocker(action: Dict, other_register: List[Dict]) -> bool:
    """Check if action is a cross-side blocker: another action on the other side depends on it and it is not Done."""
    if action.get('status') == 'Done':
        return False
    action_id = action.get('id')
    if not action_id:
        return False
    for other_action in other_register:
        if other_action.get('depends_on') == action_id:
            return True
    return False

def check_critical_and_late(action: Dict, today: datetime, critical_path: List[str]) -> bool:
    """Check if action is on critical path and (overdue or no owner)."""
    if action.get('id') not in critical_path:
        return False
    return check_overdue(action, today) or check_no_owner(action)

def get_flags_for_action(action: Dict, today: datetime, critical_path: List[str],
                          due_soon_days: int, blocked_days: int,
                          other_register: List[Dict]) -> List[Tuple[str, str, str]]:
    """
    Get all flags for an action.
    Returns list of tuples: (action_id, rule_name, level)
    """
    flags = []
    action_id = action.get('id', 'UNKNOWN')

    if check_overdue(action, today):
        flags.append((action_id, 'overdue', 'nudge'))

    if check_no_owner(action):
        flags.append((action_id, 'no_owner', 'nudge'))

    if check_due_soon_critical(action, today, critical_path, due_soon_days):
        flags.append((action_id, 'due_soon_critical', 'nudge'))

    if check_blocked_too_long(action, today, blocked_days):
        flags.append((action_id, 'blocked_too_long', 'escalate'))

    if check_cross_side_blocker(action, other_register):
        flags.append((action_id, 'cross_side_blocker', 'escalate'))

    if check_critical_and_late(action, today, critical_path):
        flags.append((action_id, 'critical_and_late', 'escalate'))

    return flags

def get_all_flags(client_register_path: str, mistral_register_path: str,
                   today: datetime, critical_path: List[str],
                   due_soon_days: int, blocked_days: int) -> List[Tuple[str, str, str]]:
    """
    Get all flags for all actions in both registers.
    Returns list of tuples: (action_id, rule_name, level)
    """
    client_register, mistral_register = load_registers(client_register_path, mistral_register_path)

    all_flags = []

    for action in client_register:
        flags = get_flags_for_action(
            action, today, critical_path, due_soon_days, blocked_days,
            mistral_register
        )
        all_flags.extend(flags)

    for action in mistral_register:
        flags = get_flags_for_action(
            action, today, critical_path, due_soon_days, blocked_days,
            client_register
        )
        all_flags.extend(flags)

    return all_flags

def get_flagged_actions(client_register_path: str, mistral_register_path: str,
                        today: datetime, critical_path: List[str],
                        due_soon_days: int, blocked_days: int) -> Dict[str, List[Tuple[str, str]]]:
    """
    Get a dictionary mapping action IDs to their flags (rule_name, level).
    """
    client_register, mistral_register = load_registers(client_register_path, mistral_register_path)

    flagged_actions = {}

    for action in client_register:
        flags = get_flags_for_action(
            action, today, critical_path, due_soon_days, blocked_days,
            mistral_register
        )
        if flags:
            action_id = action.get('id')
            flagged_actions[action_id] = [(rule, level) for _, rule, level in flags]

    for action in mistral_register:
        flags = get_flags_for_action(
            action, today, critical_path, due_soon_days, blocked_days,
            client_register
        )
        if flags:
            action_id = action.get('id')
            flagged_actions[action_id] = [(rule, level) for _, rule, level in flags]

    return flagged_actions
