
from typing import TypedDict

class AgentState(TypedDict,total = False):
    message: str          # PII-masked user text
    customer_id: str      # from verified token
    intent: str
    tier: str
    steps: int            # step limit counter
    deadline: float       # monotonic time budget
    facts: list[str]      # everything the answer may be grounded on
    pending_write: dict | None
    draft: str