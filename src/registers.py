import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Literal
import re
import shutil

try:
    from pydantic import BaseModel

    class Action(BaseModel):
        description: str
        owner: Optional[str]
        side: Literal["Client", "Mistral"]
        workstream: Literal["PLT", "UC", "DSC", "INF"]
        due_date: Optional[str]
        depends_on: Optional[str]
        evidence: str
except ImportError:
    Action = None

def load_register(path: str) -> List[Dict]:
    """Load a register CSV file."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def save_register(path: str, rows: List[Dict], fieldnames: List[str]) -> None:
    """Save a register CSV file."""
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def get_next_id_across_registers(client_register: List[Dict], mistral_register: List[Dict],
                                  workstream: str) -> str:
    """
    Get the next available ID for a workstream across both registers.
    """
    all_ids = []
    for row in client_register + mistral_register:
        if row.get('id', '').startswith(workstream):
            match = re.match(rf'{workstream}-(\d+)', row.get('id', ''))
            if match:
                all_ids.append(int(match.group(1)))

    if not all_ids:
        return f"{workstream}-001"

    next_num = max(all_ids) + 1
    return f"{workstream}-{next_num:03d}"

def action_to_register_row(action, action_id: str, today: str) -> Dict:
    """Convert an Action to a register row dictionary."""
    return {
        'id': action_id,
        'description': action.description,
        'owner': action.owner if action.owner else '',
        'side': action.side,
        'workstream': action.workstream,
        'due_date': action.due_date if action.due_date else '',
        'status': 'Not started',
        'depends_on': action.depends_on if action.depends_on else '',
        'source': 'extracted',
        'last_update': today,
    }

def write_actions_to_registers(actions, client_register_path: str,
                              mistral_register_path: str, today: str) -> None:
    """
    Write multiple accepted actions to their respective registers.
    """
    client_register = load_register(client_register_path)
    mistral_register = load_register(mistral_register_path)

    client_actions = [a for a in actions if a.side == 'Client']
    mistral_actions = [a for a in actions if a.side == 'Mistral']

    for action in client_actions:
        action_id = get_next_id_across_registers(client_register, mistral_register, action.workstream)
        row = action_to_register_row(action, action_id, today)
        client_register.append(row)
        print(f"Wrote action {action_id} to Client register")

    for action in mistral_actions:
        action_id = get_next_id_across_registers(client_register, mistral_register, action.workstream)
        row = action_to_register_row(action, action_id, today)
        mistral_register.append(row)
        print(f"Wrote action {action_id} to Mistral register")

    fieldnames = ['id', 'description', 'owner', 'side', 'workstream', 'due_date',
                  'status', 'depends_on', 'source', 'last_update']
    save_register(client_register_path, client_register, fieldnames)
    save_register(mistral_register_path, mistral_register, fieldnames)

def backup_registers(client_register_path: str, mistral_register_path: str) -> None:
    """Create backups of the register files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    client_backup = f"{client_register_path}.backup_{timestamp}"
    mistral_backup = f"{mistral_register_path}.backup_{timestamp}"
    shutil.copy2(client_register_path, client_backup)
    shutil.copy2(mistral_register_path, mistral_backup)
    print(f"Created backups: {client_backup}, {mistral_backup}")
