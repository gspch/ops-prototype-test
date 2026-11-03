# ops-prototype-test

Meeting notes in, structured actions out, deterministic escalation, then a Program Lead brief and owner nudges. Fictitious data only. Mistral API only.

## Pipeline

| Step | File | Who decides |
|---|---|---|
| 1. Extract actions from notes | `src/extract.py` | Mistral model, structured output |
| 2. Validate each action | `src/validate.py` | Human, in the terminal |
| 3. Write to the owner's side register | `src/registers.py` | Code |
| 4. Detect late, unowned, blocked | `src/rules.py` | Code, no model |
| 5. Draft brief, digest, nudges | `src/draft.py` | Mistral model, from flags only |

`src/run.py` chains the five steps.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MISTRAL_API_KEY=your_key

python -m unittest discover tests   # rules, no network
python src/run.py --rules-only      # step 4 only, no model call
python src/run.py                   # full pipeline, interactive validation
```

Each run copies `data/register_*.csv` to `out/` and writes there. `data/` stays unchanged, so the demo replays from the same start. Outputs:

1. `out/brief_program_lead.md`
2. `out/digest_client_TO_VALIDATE.md`
3. `out/nudges.md`
4. `out/register_client.csv` and `out/register_mistral.csv`

If `MISTRAL_API_KEY` is missing or the Mistral client is not installed, the run stops. There is no fallback data.

## Configuration

`config.yaml` fixes `today` at 2026-11-06 and pins the model to `mistral-large-4-0` (a dated version, not an alias).

## Rules

| Rule | Condition | Level |
|---|---|---|
| overdue | due_date before today, not Done | nudge |
| no_owner | owner empty | nudge |
| due_soon_critical | on critical path, due within 5 working days, not Done | nudge |
| blocked_too_long | Blocked, more than 5 working days since last_update | escalate |
| cross_side_blocker | an action on the other side depends on it, not Done | escalate |
| critical_and_late | on critical path and (overdue or no owner), not Done | escalate |

Working days are counted strictly after the start date, up to and including the end date. Saturdays and Sundays are skipped.

## Expected flags on 2026-11-06

| ID | Flags |
|---|---|
| PLT-031 | overdue, critical_and_late |
| PLT-040 | overdue, no_owner, cross_side_blocker (blocks PLT-041), critical_and_late |
| PLT-041 | due_soon_critical (3 working days), blocked_too_long (7 working days) |
| PLT-020 | overdue |
| UC-008 | overdue, blocked_too_long (13 working days) |
| DSC-003 | no_owner |
| New action "book a demo with plant managers" | no_owner |
| PLT-035, INF-002, UC-010 | none |

`tests/test_rules.py` asserts this table exactly.
