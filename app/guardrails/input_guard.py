"""Input guardrails for the app."""
import re
from dataclasses import dataclass, field

MAX_LENGTH = 2000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|rules)",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"developer\s+mode",
    r"jailbreak",
    r"reveal\s+.{0,30}(prompt|key|secret|password)",
    r"act\s+as\s+(?!a\s+travel)",
    r"disregard\s+.{0,20}(rules|instructions)",
]

PII = {
    "CARD": r"\b(?:\d[ -]?){13,16}\b",
    "AADHAAR": r"\b\d{4}\s\d{4}\s\d{4}\b",
    "EMAIL": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "PHONE": r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b",
    "PASSPORT": r"\b[A-PR-WY][1-9]\d{6}\b",
}


@dataclass
class GuardResult:
    ok: bool
    text: str
    flags: list[str] = field(default_factory=list)
    reason: str = ""


def check_input_guardrails(text: str) -> GuardResult:
    text = (text or "").strip()
    if not text:
        return GuardResult(ok=False, text=text, reason="Input is empty.")

    if len(text) > MAX_LENGTH:
        return GuardResult(ok=False, text=text,
                           reason=f"Input is longer than {MAX_LENGTH} characters.")

    low = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            # Generic reason: don't reveal which pattern matched.
            return GuardResult(ok=False, text=text, flags=["injection"],
                               reason="This request can't be processed.")

    flags = []
    for label, pat in PII.items():
        if re.search(pat, text):
            flags.append(f"pii:{label}")
            text = re.sub(pat, f"[{label}]", text)

    return GuardResult(ok=True, text=text, flags=flags)