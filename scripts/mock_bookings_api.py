"""Local stand-in for your real bookings/orders API, seeded from data/bookings/bookings.json.
  uvicorn scripts.mock_bookings_api:app --port 9000
Like a real API it enforces ownership SERVER-SIDE: another customer's booking looks like a 404.
NOTE: customer 'you@gmail.com' in data/bookings/customers.csv is a placeholder. To use your own Gmail,
set DEMO_EMAIL=your@gmail.com in .env (bookings of you@gmail.com are re-assigned to it at load)."""
import hashlib, json, os, pathlib
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()
cid = lambda e: "cus_" + hashlib.sha256(e.lower().encode()).hexdigest()[:12]
DB = {b["id"]: b for b in json.loads(pathlib.Path("data/bookings/bookings.json").read_text())}
demo = os.getenv("DEMO_EMAIL")
if demo:
    for b in DB.values():
        if b["customer_id"] == cid("you@gmail.com"):
            b["customer_id"] = cid(demo)


@app.get("/bookings/{bid}")
def get_booking(bid: str, x_customer_id: str = Header()):
    b = DB.get(bid)
    if not b or b["customer_id"] != x_customer_id:
        raise HTTPException(404)
    return b


@app.post("/bookings/{bid}/{action}")
def act(bid: str, action: str, x_customer_id: str = Header()):
    b = DB.get(bid)
    if not b or b["customer_id"] != x_customer_id:
        raise HTTPException(404)
    if action == "cancel":
        b.update(status="cancelled", refund_status="initiated", refund_eta="5-7 working days")
    return {"booking_id": bid, "action": action, "result": "ok", "refund_status": b.get("refund_status")}
