
import json,re
from langchain_core.messages import HumanMessage,SystemMessage
from app.llm.gateway import generate
from app.llm.router import Tier

INTENTS = ["booking_lookup", "refund_status", "booking_change", "place_info",
           "live_info", "itinerary", "chitchat"]
PROMPT = ("Classify the Goa-travel user message into exactly one of: " + ", ".join(INTENTS) +
          '. Reply ONLY JSON: {"intent": "<one>"}')


def _rules(text:str) -> str:
    t = text.lower()
    if "refund" in t: return "refund_status"
    if re.search(r"cancel|change|modify", t): return "booking_change"
    if re.search(r"#\d+|booking|order", t): return "booking_lookup"
    if re.search(r"weather|rain|today|now|open", t): return "live_info"
    if re.search(r"itinerary|plan|\d+ ?days?", t): return "itinerary"
    return "place_info"


async def classify_intent(text:str) -> str:
    try:
        raw = await generate([SystemMessage(content=PROMPT),HumanMessage(content=text)],Tier.SMALL)
        intent = json.loads(re.search(r"\{.*\}", raw, re.S).group())["intent"]
        return intent if intent in INTENTS else _rules(text)
    except Exception:
        return _rules(text)