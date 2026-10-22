"""Streamlit chat UI. Login = Google (Gmail) via st.login. Handles confirmation + approval states."""
import time
import streamlit as st
from api_client import call

st.set_page_config(page_title="Goa Travel Assistant", page_icon="🌴")
if not st.user.is_logged_in:
    st.title("🌴 Goa Travel Assistant")
    st.button("Sign in with Google", on_click=st.login, args=("google",))
    st.stop()

st.sidebar.write(f"Signed in as **{st.user.email}**")
st.sidebar.button("Log out", on_click=st.logout)
st.session_state.setdefault("history", [])
st.session_state.setdefault("thread_id", None)
st.session_state.setdefault("pending_confirm", None)

for role, text in st.session_state.history:
    st.chat_message(role).write(text)


def stream(text: str):  # answer is already guard-checked; stream it for UX
    for w in text.split(" "):
        yield w + " "
        time.sleep(0.015)


def show(resp: dict):
    st.session_state.thread_id = resp.get("thread_id")
    with st.chat_message("assistant"):
        st.write_stream(stream(resp["answer"]))
    st.session_state.history.append(("assistant", resp["answer"]))
    st.session_state.pending_confirm = resp if resp.get("status") == "needs_confirmation" else None


if pc := st.session_state.pending_confirm:
    c1, c2 = st.columns(2)
    if c1.button("✅ Confirm"):
        show(call("POST", "/chat/confirm", json={"thread_id": pc["thread_id"], "confirm": True}))
        st.rerun()
    if c2.button("❌ Cancel"):
        show(call("POST", "/chat/confirm", json={"thread_id": pc["thread_id"], "confirm": False}))
        st.rerun()

if prompt := st.chat_input("Ask about Goa, or about your booking..."):
    st.session_state.history.append(("user", prompt))
    st.chat_message("user").write(prompt)
    with st.spinner("Thinking..."):
        resp = call("POST", "/chat", json={"message": prompt, "thread_id": st.session_state.thread_id})
    show(resp)
    st.rerun() if resp.get("status") == "needs_confirmation" else None
