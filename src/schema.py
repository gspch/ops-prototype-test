from typing import Literal, Optional
from pydantic import BaseModel

class Action(BaseModel):
    description: str
    owner: Optional[str]          # None when the notes name no owner
    side: Literal["Client", "Mistral"]
    workstream: Literal["PLT", "UC", "DSC", "INF"]
    due_date: Optional[str]       # ISO date, None if not stated
    depends_on: Optional[str]     # an existing ID only if the notes cite it
    evidence: str                 # the short line of the notes it comes from

class ActionList(BaseModel):
    actions: list[Action]
