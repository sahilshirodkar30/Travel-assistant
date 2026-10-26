"""API gateway (FastAPI): identity, rate limits, load shedding, chat + HITL endpoints."""
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from app.auth import routes as auth_routes
from app.auth.security import User, current_user, require_ops
from app.gateway.load_shed import admit
from app.gateway.rate_limit import rate_limit_ip, rate_limit_user
from app.hitl import approvals
from app.observability.setup import setup
from app.services import chat_service

app = FastAPI(title="Goa Travel Assistant", dependencies=[Depends(rate_limit_ip)])
setup(app)
app.include_router(auth_routes.router)


class ChatIn(BaseModel):
    message: str = Field(max_length=2000)
    thread_id: str | None = None


class ConfirmIn(BaseModel):
    thread_id: str
    confirm: bool


class DecisionIn(BaseModel):
    approved: bool


@app.get("/healthz")
def health():
    return {"ok": True}


@app.post("/chat", dependencies=[Depends(rate_limit_user)])
async def chat(body: ChatIn, user: User = Depends(current_user)):
    async with admit():
        return await chat_service.handle_chat(user, body.message, body.thread_id)


@app.post("/chat/confirm", dependencies=[Depends(rate_limit_user)])
async def confirm(body: ConfirmIn, user: User = Depends(current_user)):
    return await chat_service.resume(user, body.thread_id, body.confirm)


@app.get("/approvals")
async def pending(_: User = Depends(require_ops)):
    return await approvals.list_pending()


@app.post("/approvals/{aid}")
async def decide(aid: str, body: DecisionIn, ops: User = Depends(require_ops)):
    item = await approvals.pop(aid)
    if not item:
        return {"error": "not found"}
    owner = User(email="", customer_id=item["customer_id"], role="user")
    return await chat_service.resume(owner, item["thread_id"], {"approved": body.approved, "by": ops.email})


# @app.post("/auth/google")
# def login(body: GoogleLogin):  # body.id_token comes from the frontend's Google sign-in
#     email = verify_google_login(body.id_token)
#     return {"access_token": create_token(email), "token_type": "bearer"}