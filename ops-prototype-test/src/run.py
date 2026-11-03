"""Chains steps 1 to 5.

Registers in data/ are never modified: each run copies them to out/ and writes there,
so the demo can be replayed from the same starting point.

Usage, from the repository root:
  python src/run.py               full pipeline, interactive validation
  python src/run.py --rules-only  step 4 only, on data/, no model call
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rules import flags_from_registers  # noqa: E402
from registers import load_register  # noqa: E402

DATA, OUT = ROOT / "data", ROOT / "out"
NOTES = ["notes_platform_weekly.md", "notes_usecase_weekly.md"]


def print_flags(flags) -> None:
    print("\nFlags (deterministic rules, no model):")
    for action_id, rule, level in flags:
        print(f"  {action_id:<8} {rule:<20} {level}")


def compute_flags(client_path: Path, mistral_path: Path, cfg: dict):
    client, mistral = load_register(str(client_path)), load_register(str(mistral_path))
    flags = flags_from_registers(
        client, mistral, cfg["today"], cfg["critical_path"],
        cfg["thresholds"]["due_soon_working_days"],
        cfg["thresholds"]["blocked_escalate_working_days"],
    )
    return client, mistral, flags


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-only", action="store_true", help="run step 4 on data/ only")
    args = parser.parse_args()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    today = str(cfg["today"])

    if args.rules_only:
        print_flags(compute_flags(DATA / "register_client.csv", DATA / "register_mistral.csv", cfg)[2])
        return

    from draft import draft_all
    from extract import extract
    from registers import write_actions
    from validate import review

    OUT.mkdir(exist_ok=True)
    client_path, mistral_path = OUT / "register_client.csv", OUT / "register_mistral.csv"
    shutil.copy(DATA / "register_client.csv", client_path)
    shutil.copy(DATA / "register_mistral.csv", mistral_path)

    model_seconds = 0.0
    for name in NOTES:
        print(f"\n=== Step 1. Extract: {name} ({cfg['model']})")
        start = time.perf_counter()
        actions = extract((DATA / name).read_text(), today, cfg["model"]).actions
        model_seconds += time.perf_counter() - start
        print(f"{len(actions)} actions extracted.")

        print("=== Step 2. Validate")
        accepted = review(actions)

        print(f"\n=== Step 3. Write ({len(accepted)} accepted)")
        write_actions(accepted, str(client_path), str(mistral_path), today)

    print("\n=== Step 4. Detect")
    client, mistral, flags = compute_flags(client_path, mistral_path, cfg)
    print_flags(flags)

    print(f"\n=== Step 5. Draft ({cfg['model']})")
    start = time.perf_counter()
    outputs = draft_all(client, mistral, flags, cfg)
    model_seconds += time.perf_counter() - start
    for filename, text in outputs.items():
        (OUT / filename).write_text(text + "\n")
        print(f"  out/{filename}")

    print(f"\nDone. Model time: {model_seconds:.1f} s. Human validation time excluded.")


if __name__ == "__main__":
    main()
