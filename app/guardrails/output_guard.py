"""Output guard: block answers that leak internals, invent amounts or IDs, or expose PII."""
import re
from app.guardrails.input_guard import GuardResult, PII

SAFE_FALLBACK = ("I couldn't verify that safely. Please check the My Bookings page "
                 "or contact support.")
LEAK_MARKERS = ["system prompt", "api key", "as an ai language model", "internal instruction"]
AMOUNT_OR_ID = re.compile(r"#\d{4,}|(?:₹|\brs\.?)\s?\d[\d,]*")


def _norm(s: str) -> str:
    """Lowercase, drop spaces, and treat 'Rs.' and 'Rs' as the same."""
    return re.sub(r"\s", "", s.lower()).replace("rs.", "rs")


def check_output_guardrails(answer: str, facts: list[str], customer_id: str) -> GuardResult:
    flags = []
    fact_blob = _norm(" ".join(facts))

    for token in AMOUNT_OR_ID.findall(answer.lower()):
        if _norm(token) not in fact_blob:
            flags.append(f"ungrounded:{token}")

    for label, pat in PII.items():
        if label != "EMAIL" and re.search(pat, answer):
            flags.append(f"pii:{label}")

    for cid in re.findall(r"cus_[0-9a-f]{12}", answer):
        if cid != customer_id:
            flags.append("foreign_customer_id")

    low = answer.lower()
    if any(m in low for m in LEAK_MARKERS):
        flags.append("scope:leak")

    if flags:
        return GuardResult(False, SAFE_FALLBACK, flags, "blocked")
    return GuardResult(True, answer)