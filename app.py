"""
AI Student Assistant
---------------------
A simple Streamlit app that:
1. Lets a student chat with an AI Agent about courses/university services.
2. Detects when the student wants to submit a formal "request" (e.g. transcript,
   meeting with advisor, complaint) and collects the needed details.
3. Sends that request to an n8n webhook, which stores it in Google Sheets and
   sends an email notification.

Uses Groq's API (free tier, no billing required) as the AI Agent.

Run with:
    streamlit run app.py
"""

import os
import json
import requests
import streamlit as st
from groq import Groq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Get a free Groq API key at https://console.groq.com/keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")  # e.g. https://your-n8n.app.n8n.cloud/webhook/student-request

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are the AI Student Assistant for a university.

You help students with:
- General questions about courses, registration, deadlines, and university services
  (answer from general knowledge and common sense; you don't have a live database,
  so be clear when something needs to be confirmed with the registrar's office).
- Recommending which office/department a student should contact for a given issue.
- Detecting when a student wants to submit a formal REQUEST that needs to be
  logged and routed to an office. Examples of requests: transcript request,
  meeting with an academic advisor, course withdrawal, complaint, ID card reissue.

When you detect the student wants to submit a request, you must:
1. Politely collect: student name, student email, request type, and a short
   description of what they need.
2. Once you have ALL four fields, respond with a normal helpful message AND
   include, on its own line at the very end of your reply, a JSON object
   wrapped exactly like this (no extra text on that line):
   ###REQUEST_JSON### {"name": "...", "email": "...", "type": "...", "details": "..."}

If the student is just asking a question (not submitting a request), answer
normally and do NOT include the ###REQUEST_JSON### line.

Keep answers concise and friendly.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client():
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys")
        st.stop()
    return Groq(api_key=GROQ_API_KEY)


def call_agent(client, history):
    """Call the AI Agent with the full chat history and return its reply text."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


def extract_request_json(reply_text):
    """If the agent embedded a ###REQUEST_JSON### payload, pull it out."""
    marker = "###REQUEST_JSON###"
    if marker not in reply_text:
        return reply_text, None
    visible, payload = reply_text.split(marker, 1)
    try:
        data = json.loads(payload.strip())
        return visible.strip(), data
    except json.JSONDecodeError:
        return reply_text, None


def send_to_n8n(data):
    """POST the collected request to the n8n webhook. Returns (ok, message)."""
    if not N8N_WEBHOOK_URL:
        return False, "N8N_WEBHOOK_URL is not configured."
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=data, timeout=10)
        if resp.status_code in (200, 201):
            return True, "Request sent to n8n successfully."
        return False, f"n8n returned status {resp.status_code}: {resp.text[:200]}"
    except requests.RequestException as e:
        return False, f"Could not reach n8n webhook: {e}"


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Student Assistant", page_icon="🎓", layout="centered")
st.title("🎓 AI Student Assistant")
st.caption("Ask about courses, deadlines, or submit a request to the university office.")

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": ..., "content": ...}
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []  # what we show in the chat UI
if "last_automation_status" not in st.session_state:
    st.session_state.last_automation_status = None

# Render chat history
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Show status of the last automation attempt, if any
if st.session_state.last_automation_status:
    ok, message = st.session_state.last_automation_status
    if ok:
        st.success(f"✅ Automation triggered: {message}")
    else:
        st.warning(f"⚠️ Automation not completed: {message}")

user_input = st.chat_input("Type your question or request here...")

if user_input:
    # Show and store the user's message
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    client = get_client()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            raw_reply = call_agent(client, st.session_state.messages)
            visible_reply, request_data = extract_request_json(raw_reply)
            st.markdown(visible_reply)

    st.session_state.messages.append({"role": "assistant", "content": raw_reply})
    st.session_state.display_messages.append({"role": "assistant", "content": visible_reply})

    # If the agent collected a complete request, fire the n8n automation
    if request_data:
        ok, message = send_to_n8n(request_data)
        st.session_state.last_automation_status = (ok, message)
        st.rerun()

with st.sidebar:
    st.header("About")
    st.write(
        "This assistant answers general student questions and, when you ask to "
        "submit a request (e.g. transcript, advisor meeting, complaint), it will "
        "collect your details and automatically log them via an n8n workflow "
        "(saved to Google Sheets + email confirmation)."
    )
    if st.button("Reset conversation"):
        st.session_state.messages = []
        st.session_state.display_messages = []
        st.session_state.last_automation_status = None
        st.rerun()
