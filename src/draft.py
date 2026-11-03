"""Step 5. The model drafts the brief, the Client digest and the nudges from the flags only.

Who receives a nudge is decided here in code, not by the model.
"""
import json
from typing import Dict, List

from extract import get_client
from rules import Flag

DIGEST_HEADER = "DRAFT, TO VALIDATE BEFORE SENDING"

BRIEF_PROMPT = """Write a Monday brief for the Program Lead, one page maximum, in English.
Use ONLY the flags and actions provided. Never add facts. Cite action IDs.
Sections, in this order:
1. Decisions needed from you (escalations only)
2. Top risks, five at most, most critical first
3. Late actions
4. Cross-side blockers, with the chain of what blocks what
Short sentences. No adjectives you cannot back with a flag. Markdown output."""

DIGEST_PROMPT = f"""Write a weekly digest for the Client program owner, in English.
Use ONLY the flags and actions provided. Never add facts. Cite action IDs.
Cover Client-side actions and shared dependencies only. Neutral tone.
No internal Mistral comment, no Mistral-internal action.
The first line must be exactly: {DIGEST_HEADER}
Short sentences. Markdown output."""

NUDGES_PROMPT = """Write one nudge per recipient, in English, in the order given.
For each recipient: a level-2 Markdown heading with the recipient name, then the message.
Three sentences maximum per message. Each message cites the action ID, the date and the precise ask.
When the recipient is not the owner because the action has no owner, ask them to assign one.
Use ONLY the flags and actions provided. Never add facts. Drafts only, they will not be sent automatically."""


def _complete(model: str, system: str, payload: Dict) -> str:
    resp = get_client().chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, indent=2, ensure_ascii=False)},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


def _flags_by_id(flags: List[Flag]) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {}
    for action_id, rule, level in flags:
        out.setdefault(action_id, []).append({"rule": rule, "level": level})
    return out


def _dependencies(client: List[Dict], mistral: List[Dict]) -> List[Dict]:
    sides = {row["id"]: row["side"] for row in client + mistral}
    return [{"action": row["id"], "side": row["side"], "depends_on": row["depends_on"],
             "depends_on_side": sides.get(row["depends_on"], "unknown")}
            for row in client + mistral if row.get("depends_on")]


def nudge_recipients(rows: List[Dict], flags: List[Flag], program_owner_client: str,
                     program_lead: str) -> Dict[str, List[str]]:
    """Recipient -> flagged action IDs. Unowned actions go to the side's program owner."""
    flagged = {a for a, _, _ in flags}
    recipients: Dict[str, List[str]] = {}
    for row in rows:
        if row["id"] not in flagged:
            continue
        owner = (row.get("owner") or "").strip()
        if not owner:
            owner = program_owner_client if row["side"] == "Client" else program_lead
        recipients.setdefault(owner, []).append(row["id"])
    return recipients


def draft_all(client: List[Dict], mistral: List[Dict], flags: List[Flag], cfg: Dict) -> Dict[str, str]:
    model = cfg["model"]
    by_id = _flags_by_id(flags)
    rows = client + mistral
    flagged_rows = [dict(r, flags=by_id[r["id"]]) for r in rows if r["id"] in by_id]
    deps = _dependencies(client, mistral)

    brief = _complete(model, BRIEF_PROMPT, {
        "today": str(cfg["today"]), "flagged_actions": flagged_rows, "dependencies": deps,
    })

    client_ids = {r["id"] for r in client}
    shared = [d for d in deps if d["depends_on"] in client_ids or d["action"] in client_ids]
    digest = _complete(model, DIGEST_PROMPT, {
        "today": str(cfg["today"]),
        "client_actions": [dict(r, flags=by_id.get(r["id"], [])) for r in client],
        "shared_dependencies": shared,
    })
    lines = [l for l in digest.splitlines() if l.strip().strip("*#« »") != DIGEST_HEADER]
    digest = DIGEST_HEADER + "\n\n" + "\n".join(lines).strip()

    recipients = nudge_recipients(rows, flags, cfg["program_owner_client"], cfg["program_lead"])
    nudges = _complete(model, NUDGES_PROMPT, {
        "today": str(cfg["today"]),
        "recipients": [{"name": name, "actions": [r for r in flagged_rows if r["id"] in ids]}
                       for name, ids in recipients.items()],
    })

    return {
        "brief_program_lead.md": brief,
        "digest_client_TO_VALIDATE.md": digest,
        "nudges.md": nudges,
    }
