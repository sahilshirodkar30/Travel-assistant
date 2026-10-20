""" Output guard for the guardrails framework. """

import re
from app.guardrails.input_guard import GuardResult,PII

SAFE_FALLBACK = ("I couldn't verify that safely. Please check the My Bookings page "
                 "or I can connect you with support.")
LEAK_MARKERS = ["system prompt", "api key", "as an ai language model", "internal instruction"]


def check_output_guardrails(answer:str,facts:list[str],customer_id:str)->GuardResult:
    flags = []

    fact_blob = " ".join(facts).lower().replace(" ","")

    for token in re.findall(r"#\d{4,}|₹\s?[\d,]+|rs\.?\s?[\d,]+",answer.lower()):
        if token.replace(" ","") not in fact_blob:
            flags.append(f"ungrounded: {token}")

    for label,pat in PII.items():
        if label != "EMAIL" and re.search(pat,answer):
            flags.append(f"pii:{label}")

    for cid in re.findall(r"cus_[0-9a-f]{12}", answer):
        if cid != customer_id:
            flags.append(f"foreign_customer_id")

    if any(m in answer.lower() for m in LEAK_MARKERS):
        flags.append("scope:leak")

    if flags:
        return GuardResult(False, SAFE_FALLBACK, flags, "blocked")

    return GuardResult(True, answer)