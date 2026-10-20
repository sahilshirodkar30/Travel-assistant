"""Commerce tools. customer_id is injected from the VERIFIED token, never from the LLM.
Every read/write re-checks ownership (defence in depth)."""
import httpx
from app.config import get_settings

s = get_settings()


def _headers(customer_id: str):
    return {"X-Api-Key": s.bookings_api_key, "X-Customer-Id": customer_id}


async def get_booking(customer_id: str, booking_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{s.bookings_api_url}/bookings/{booking_id}", headers=_headers(customer_id))
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if data.get("customer_id") != customer_id:
        raise PermissionError("Booking does not belong to this customer")
    return data


def booking_to_fact(b: dict) -> str:
    return (f"Booking #{b['id']} ({b['type']}, {b['title']}) status={b['status']}; "
            f"amount=₹{b['amount_inr']}; refund_status={b.get('refund_status','none')}; "
            f"refund_eta={b.get('refund_eta','n/a')}")


async def execute_write(customer_id: str, action: dict) -> dict:
    """action = {'type':'cancel'|'refund','booking_id':..,'amount_inr':..}. Only called after confirmation/approval."""
    async with httpx.AsyncClient(timeout=8) as c:
        r = await c.post(f"{s.bookings_api_url}/bookings/{action['booking_id']}/{action['type']}",
                         headers=_headers(customer_id), json=action)
    r.raise_for_status()
    return r.json()
