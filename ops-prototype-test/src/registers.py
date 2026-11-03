"""Step 3. Read and write the two CSV registers. Each action is written to its own side only."""
import csv
import re
from typing import Dict, List

from schema import Action

FIELDNAMES = ["id", "description", "owner", "side", "workstream", "due_date",
              "status", "depends_on", "source", "last_update"]


def load_register(path: str) -> List[Dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def save_register(path: str, rows: List[Dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def next_id(client: List[Dict], mistral: List[Dict], workstream: str) -> str:
    """Next free number for a workstream, across both registers."""
    numbers = [int(m.group(1)) for row in client + mistral
               if (m := re.fullmatch(rf"{workstream}-(\d+)", row.get("id", "")))]
    return f"{workstream}-{max(numbers, default=0) + 1:03d}"


def to_row(action: Action, action_id: str, today: str) -> Dict:
    return {
        "id": action_id,
        "description": action.description,
        "owner": action.owner or "",
        "side": action.side,
        "workstream": action.workstream,
        "due_date": action.due_date or "",
        "status": "Not started",
        "depends_on": action.depends_on or "",  # the ID only, never the other side's content
        "source": "extracted",
        "last_update": today,
    }


def write_actions(actions: List[Action], client_path: str, mistral_path: str, today: str) -> List[Dict]:
    """Append accepted actions to their own side's register. Returns the rows written."""
    client = load_register(client_path)
    mistral = load_register(mistral_path)
    written = []
    for action in actions:
        row = to_row(action, next_id(client, mistral, action.workstream), today)
        (client if action.side == "Client" else mistral).append(row)
        written.append(row)
        print(f"  {row['id']} -> {action.side} register")
    save_register(client_path, client)
    save_register(mistral_path, mistral)
    return written
