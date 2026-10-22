"""LangGraph orchestrator: classify -> route -> tools/RAG -> (confirm -> approval -> write) -> draft.
Enforces a step limit and a time budget. interrupt() pauses the graph for human-in-the-loop."""
import re, time
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver
from app.agent.intents import classify_intent
from app.agent.state import AgentState
from app.config import get_settings
from app.llm.gateway import generate
from app.llm.router import Tier, pick_tier
from app.rag.retriever import retriever
from app.tools import bookings, weather

s = get_settings()
SYSTEM = ("You are a friendly Goa travel assistant. Answer ONLY from FACTS. If FACTS are empty or "
          "insufficient, say you can't verify it. Never invent booking ids, amounts or dates. "
          "Mention 'last verified' dates when present. Keep it under 120 words.")
BOOKING_ID = re.compile(r"#?\b(\d{4,10})\b")


def _bump(state, **upd):
    return {"steps": state["steps"] + 1, **upd}


def over_budget(state) -> bool:
    return state["steps"] >= s.max_agent_steps or time.monotonic() > state["deadline"]


async def classify(state):
    intent = await classify_intent(state["message"])
    return _bump(state, intent=intent, tier=pick_tier(intent, state["message"]).value)


def route(state):
    if over_budget(state):
        return "draft"
    return {"booking_lookup": "fetch_booking", "refund_status": "fetch_booking",
            "booking_change": "propose_write", "place_info": "retrieve", "itinerary": "retrieve",
            "live_info": "live"}.get(state["intent"], "draft")


async def fetch_booking(state):
    m = BOOKING_ID.search(state["message"])
    if not m:
        return _bump(state, facts=["No booking number found in the message; ask the user for it."])
    b = await bookings.get_booking(state["customer_id"], m.group(1))
    fact = bookings.booking_to_fact(b) if b else f"No booking #{m.group(1)} found on this account."
    return _bump(state, facts=[fact])


async def retrieve_node(state):
    return _bump(state, facts=await retriever(state["message"]))


def after_retrieve(state):
    return "live" if state["intent"] == "itinerary" and not over_budget(state) else "draft"


async def live(state):
    try:
        w = await weather.goa_weather()
    except Exception:
        w = "Live weather unavailable right now."
    return _bump(state, facts=state.get("facts", []) + [w])


async def propose_write(state):
    m = BOOKING_ID.search(state["message"])
    if not m:
        return _bump(state, facts=["Ask the user which booking number to cancel."], pending_write=None)
    b = await bookings.get_booking(state["customer_id"], m.group(1))
    if not b:
        return _bump(state, facts=[f"No booking #{m.group(1)} on this account."], pending_write=None)
    action = {"type": "cancel", "booking_id": b["id"], "amount_inr": b["amount_inr"]}
    return _bump(state, pending_write=action, facts=[bookings.booking_to_fact(b)])


def next_after_propose(state):
    return "user_confirm" if state.get("pending_write") else "draft"


def user_confirm(state):
    ok = interrupt({"kind": "user_confirm", "action": state["pending_write"]})
    if not ok:
        return _bump(state, pending_write=None, facts=state["facts"] + ["User declined; nothing was changed."])
    return _bump(state)


def next_after_confirm(state):
    if not state.get("pending_write"):
        return "draft"
    return "human_approval" if state["pending_write"]["amount_inr"] > s.approval_threshold_inr else "execute"


def human_approval(state):
    decision = interrupt({"kind": "human_approval", "action": state["pending_write"]})
    if not decision.get("approved"):
        return _bump(state, pending_write=None,
                     facts=state["facts"] + ["Support declined this request; a human will follow up."])
    return _bump(state)


async def execute(state):
    if not state.get("pending_write"):
        return _bump(state)
    res = await bookings.execute_write(state["customer_id"], state["pending_write"])
    return _bump(state, facts=state["facts"] + [f"Action done: {res}"])


async def draft(state):
    facts = "\n".join(state.get("facts", [])) or "(none)"
    msgs = [SystemMessage(content=SYSTEM), HumanMessage(content=f"FACTS:\n{facts}\n\nUSER: {state['message']}")]
    tier = Tier(state.get("tier", "medium"))
    return {"draft": await generate(msgs, tier)}


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    for name, fn in [("classify", classify), ("fetch_booking", fetch_booking), ("retrieve", retrieve_node),
                     ("live", live), ("propose_write", propose_write), ("user_confirm", user_confirm),
                     ("human_approval", human_approval), ("execute", execute), ("draft", draft)]:
        g.add_node(name, fn)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route)
    g.add_edge("fetch_booking", "draft")
    g.add_conditional_edges("retrieve", after_retrieve)
    g.add_edge("live", "draft")
    g.add_conditional_edges("propose_write", next_after_propose)
    g.add_conditional_edges("user_confirm", next_after_confirm)
    g.add_edge("human_approval", "execute")
    g.add_edge("execute", "draft")
    g.add_edge("draft", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())  # prod: AsyncPostgresSaver (POSTGRES_URL)
