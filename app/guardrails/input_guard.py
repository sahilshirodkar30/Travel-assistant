"""Input guardrails for the app."""

import re
from dataclasses import dataclass,field

INJECTION_PATTERNS = [r"ignore (all |any )?(previous|prior|above) (instructions|rules)", r"system prompt",
             r"you are now", r"developer mode", r"jailbreak", r"reveal .{0,30}(prompt|key|secret|password)",
             r"act as (?!a travel)", r"disregard .{0,20}(rules|instructions)"]

PII = {
    "CARD": r"\b(?:\d[ -]?){13,16}\b",
    "AADHAAR": r"\b\d{4}\s\d{4}\s\d{4}\b",
    "EMAIL": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "PHONE": r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b",
    "PASSPORT": r"\b[A-PR-WY][1-9]\d{6}\b",
}

MAX_lENGTH = 2000

@dataclass
class GuardResult:
    ok:bool
    text:str
    flags:list[str] = field(default_factory=list)
    reason:str=""


def check_input_guardrails(text:str)->GuardResult:
    text = (text or "").strip()
    if not text:
        return GuardResult(ok=False, text=text, reason="Input is empty")

    if len(text) > MAX_lENGTH:
        return GuardResult(ok=False, text=text, reason=f"Input exceeds maximum length of {MAX_lENGTH} characters")

    low = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return GuardResult(ok=False, text=text,flags=["injection"],reason=f"Input contains injection pattern: {pat}")

    flags = []
    for label,pat in PII.items():
        if re.search(pat,text):
            flags.append(f"pii:{label}")
            text = re.sub(pat,f"[{label}]",text)

    return GuardResult(True,text=text,flags=flags)