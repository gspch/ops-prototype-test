"""Step 2. Human gate. Nothing enters a register without an explicit accept."""
from typing import List

from pydantic import ValidationError

from schema import Action

EDITABLE = ["description", "owner", "side", "workstream", "due_date", "depends_on"]


def show(action: Action, index: int, total: int) -> None:
    print(f"\n[{index}/{total}] {action.description}")
    print(f"  owner: {action.owner or '(none)'} | side: {action.side} | workstream: {action.workstream}")
    print(f"  due: {action.due_date or '(none)'} | depends on: {action.depends_on or '(none)'}")
    print(f"  evidence: \"{action.evidence}\"")


def edit(action: Action) -> Action:
    print("  Press Enter to keep a value, type '-' to clear it.")
    data = action.model_dump()
    for field in EDITABLE:
        answer = input(f"  {field} [{data[field] or ''}]: ").strip()
        if answer == "-":
            data[field] = None
        elif answer:
            data[field] = answer
    try:
        return Action(**data)
    except ValidationError as err:
        print(f"  Invalid value, edit again: {err.errors()[0]['msg']}")
        return edit(action)


def review(actions: List[Action]) -> List[Action]:
    accepted: List[Action] = []
    for i, action in enumerate(actions, 1):
        show(action, i, len(actions))
        while True:
            choice = input("  [a]ccept / [e]dit / [r]eject: ").strip().lower()
            if choice == "a":
                accepted.append(action)
                break
            if choice == "r":
                break
            if choice == "e":
                action = edit(action)
                show(action, i, len(actions))
    return accepted
