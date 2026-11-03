"""Step 1. Notes in, structured actions out, through the Mistral API only."""
import os

from schema import ActionList

try:
    from mistralai.client import Mistral  # mistralai 2.x
except ImportError:
    try:
        from mistralai import Mistral  # mistralai 1.x
    except ImportError as exc:
        raise SystemExit("mistralai is not installed. Run: pip install -r requirements.txt") from exc

EXTRACTION_PROMPT = """You extract commitments from meeting notes of an AI program between Mistral and a
client called "the Client". Today is {today}.
Rules:
- One action per commitment someone made or should make. Ignore general statements.
- owner: the person named as doing it. If nobody is named, owner is null.
- side: "Client" or "Mistral", from the organization of the owner as given in the
  "Present" line. If owner is null, infer the side from the context.
- workstream: PLT (platform), UC (use cases), DSC (discovery), INF (client decisions).
- due_date: convert any stated date to YYYY-MM-DD using the meeting date. Null if none.
- depends_on: only an ID written in the notes (for example PLT-040). Never invent one.
- Skip items that only mention an existing ID without a new commitment.
- evidence: copy the shortest line of the notes that supports the action."""

_client = None


def get_client() -> "Mistral":
    global _client
    if _client is None:
        key = os.environ.get("MISTRAL_API_KEY")
        if not key:
            raise SystemExit("MISTRAL_API_KEY is not set. No extraction without the Mistral API.")
        _client = Mistral(api_key=key)
    return _client


def extract(notes: str, today: str, model: str) -> ActionList:
    resp = get_client().chat.parse(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT.format(today=today)},
            {"role": "user", "content": notes},
        ],
        response_format=ActionList,
        temperature=0,
        top_p=1,
    )
    message = resp.choices[0].message
    parsed = getattr(message, "parsed", None)
    if parsed is None:
        # Validate the raw JSON against the schema; raises if the model broke it.
        parsed = ActionList.model_validate_json(message.content)
    return parsed
