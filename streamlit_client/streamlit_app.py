"""A small UI that always talks to an LLM through the privacy middleware."""

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_URL = os.getenv("PRIVACY_API_BASE_URL", "http://127.0.0.1:8000")


def api_url(path: str) -> str:
    return f"{st.session_state.api_base_url.rstrip('/')}{path}"


def health_check() -> tuple[bool, str]:
    try:
        response = httpx.get(api_url("/health"), timeout=3)
        response.raise_for_status()
        return True, "Privacy middleware connected"
    except httpx.HTTPError:
        return False, "Privacy middleware is unavailable"


def create_session() -> str:
    response = httpx.post(api_url("/sessions"), timeout=10)
    response.raise_for_status()
    return response.json()["session_id"]


def close_session() -> None:
    session_id = st.session_state.get("privacy_session_id")
    if session_id:
        try:
            httpx.delete(api_url(f"/sessions/{session_id}"), timeout=10)
        except httpx.HTTPError:
            pass
    st.session_state.privacy_session_id = None
    st.session_state.messages = []


def send_message(content: str) -> dict:
    session_id = st.session_state.privacy_session_id
    response = httpx.post(
        api_url(f"/sessions/{session_id}/messages"),
        json={"role": "user", "content": content},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="Private LLM Chat", page_icon="🔒")
st.title("🔒 Private LLM Chat")
st.caption("PII is detected and tokenized locally before the prompt is sent to the configured LLM.")

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = DEFAULT_API_URL
if "privacy_session_id" not in st.session_state:
    st.session_state.privacy_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Connection")
    st.session_state.api_base_url = st.text_input(
        "Privacy API URL", value=st.session_state.api_base_url
    )
    connected, status_text = health_check()
    (st.success if connected else st.error)(status_text)
    st.caption(f"Configured model: {os.getenv('MODEL_NAME', 'not set')}")
    if st.button("Start new private session", disabled=not connected):
        close_session()
        try:
            st.session_state.privacy_session_id = create_session()
            st.rerun()
        except httpx.HTTPError:
            st.error("Could not create a privacy session.")
    if st.button("End session and erase mappings", disabled=not st.session_state.privacy_session_id):
        close_session()
        st.rerun()

if not st.session_state.privacy_session_id:
    st.info("Start a private session in the sidebar before sending a message.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Message the protected LLM", disabled=not st.session_state.privacy_session_id):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Protecting PII and contacting the model..."):
            try:
                result = send_message(prompt)
                answer = result["content"]
                st.write(answer)
                if result["detected_entities"]:
                    st.caption(f"Protected entities: {result['detected_entities']}")
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    st.error("This privacy session expired. Start a new session.")
                    st.session_state.privacy_session_id = None
                elif exc.response.status_code == 502:
                    st.error("The privacy API could not reach the configured LLM. Check MODEL_* values.")
                else:
                    st.error("The privacy API rejected the request.")
            except httpx.HTTPError:
                st.error("Could not reach the privacy API.")
