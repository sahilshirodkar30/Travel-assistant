"""Ops console: approve/reject high-value writes (role enforced by the API, not the UI)."""
import streamlit as st
from api_client import call

st.title("Pending approvals")
if not st.user.is_logged_in:
    st.stop()
try:
    items = call("GET", "/approvals")
except Exception:
    st.error("Ops role required.")
    st.stop()
for it in items:
    with st.container(border=True):
        a = it["action"]
        st.write(f"**{a['type']}** booking #{a['booking_id']} — ₹{a['amount_inr']} (customer {it['customer_id']})")
        c1, c2 = st.columns(2)
        if c1.button("Approve", key="a" + it["id"]):
            call("POST", f"/approvals/{it['id']}", json={"approved": True}); st.rerun()
        if c2.button("Reject", key="r" + it["id"]):
            call("POST", f"/approvals/{it['id']}", json={"approved": False}); st.rerun()
if not items:
    st.info("Nothing waiting.")
