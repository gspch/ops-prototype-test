import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from schema import Action, ActionList

try:
    from mistralai import Mistral
except ImportError:
    print("Warning: mistralai package not found. Extraction will use mock data.")
    Mistral = None

EXTRACTION_PROMPT = """You extract commitments from meeting notes of an AI program between Mistral and a
client called "the Client". Today is {today}.
Rules:
- One action per commitment someone made or should make. Ignore general statements.
- owner: the person named as doing it. If nobody is named, owner is null.
- side: "Client" or "Mistral", from the organization of the owner as given in the
  "Present" line. If owner is null, infer the side from the context.
- workstream: PLT (platform), UC (use cases), DSC (discovery), INF (client decisions).
- due_date: convert
