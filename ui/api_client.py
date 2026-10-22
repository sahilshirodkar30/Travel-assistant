"""Thin HTTP client used by Streamlit pages."""
import requests
import streamlit as st

BASE = st.secrets["api"]["base_url"]


def token() -> str:
    if "token" not in st.session_state:
        r = requests.post(f"{BASE}/auth/exchange", timeout=10, json={
            "email": st.user.email, "email_verified": bool(st.user.get("email_verified")),
            "internal_key": st.secrets["api"]["internal_key"]})
        r.raise_for_status()
        st.session_state.token = r.json()["access_token"]
    return st.session_state.token


def call(method: str, path: str, **kw):
    r = requests.request(method, BASE + path, headers={"Authorization": f"Bearer {token()}"}, timeout=60, **kw)
    if r.status_code == 429:
        return {"status": "error", "answer": "You're sending messages too fast. Please wait a moment."}
    if r.status_code == 503:
        return {"status": "error", "answer": "We're very busy right now. Please retry in a few seconds."}
    r.raise_for_status()
    return r.json()
