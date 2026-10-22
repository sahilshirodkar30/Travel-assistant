
import time , uuid
import logfire
from app.agent.graph import build_graph
from app.auth.security import User
from app.cache import semantic_cache as cache
from app.config import get_settings
from app.guardrails.input_guard import check_input_guardrails
from app.guardrails.output_guard import check_output_guardrails,SAFE_FALLBACK
from app.hitl import approvals
from langgraph.types import Command

s = get_settings()
graph = build_graph()


async def _finish(result:dict,user:User,thread_id:str,cacheable_q:str|None):
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if payload["king"] == "human_approval":
            aid = await approvals.enqueue(thread_id,user.customer_id,payload["action"])
            return {"status": "awaiting_approval", "approval_id": aid, "thread_id": thread_id,
                    "answer": "This needs a quick check by our support team. We'll update you shortly."}
        return {"status": "needs_confirmation", "thread_id": thread_id, "action": payload["action"],
                "answer": f"Please confirm: {payload['action']['type']} booking #{payload['action']['booking_id']}?"}

    out = check_output_guardrails(result["draft"],result.get("facts",[]),user.customer_id)
    logfire.info("output_guard",ok=out.ok,flags=out.flags)
    if out.ok and cacheable_q and result.get("intent") in cache.CACHEABLE_INTENTS:
        await cache.store(cacheable_q,out.text)
    return {"status":"ok" if out.ok else "blocked","answer":out.text,"thread_id":thread_id,"intent": result.get("intent")}

    
async def handle_chat(user:User,message:str,thread_id:str|None=None) -> dict:
    thread_id = thread_id or uuid.uuid4().hex
    with logfire.span("chat pipeline" ,customer_id = user.customer_id,thread_id=thread_id):
        g = check_input_guardrails(message)
        logfire.info("input guard",ok=g.ok,flags = g.flags)
        if not g.ok:
            return {"status": "rejected", "answer": g.reason or "Sorry, I can't help with that.",
                    "thread_id": thread_id}
        cacheable = cache.is_cacheable(g.text)
        if cacheable and (hit := await cache.lookup(g.text)):
            logfire.info("cache hit")
            return {"status": "ok", "answer": hit, "cached": True, "thread_id": thread_id}
        state = {"message": g.text, "customer_id": user.customer_id, "steps": 0, "facts": [],
                 "deadline": time.monotonic() + s.request_budget_s}

        try :
            result = await graph.ainvoke(state,config={"configurable":{"thread_id":thread_id},"recursion_limit":25})

        except Exception as e:
            logfire.error("pipeline failed",error=str(e))
            return {"status":"error","answer":SAFE_FALLBACK,"thread_id":thread_id}
        return await _finish(result,user,thread_id,g.text if cacheable else None)


async def resume(user:User,thread_id:str,value) -> dict:
    cfg = {"configurable":{"thread_id":thread_id},"recursion_limit":25}
    result = await graph.ainvoke(Command(resume=value),config=cfg)
    return await _finish(result,user,thread_id,None)