# AI Student Assistant — Final Internship Project

An AI-powered assistant for university students that answers questions and,
when a student needs to submit a formal request, automatically logs it to
Google Sheets and sends email notifications via n8n.

Uses **Groq** (free tier, no billing required) as the AI Agent, running
Meta's `llama-3.3-70b-versatile` model.

## Architecture

```
Student
  ↓
Streamlit UI (app.py)
  ↓
AI Agent (Groq API) — answers questions, detects & collects request details
  ↓ (only when a request is detected)
n8n Webhook
  ↓
Append row to Google Sheets
  ↓
Send confirmation email to student + notification email to admin
```

## 1. Get a free Groq API key

1. Go to https://console.groq.com/keys
2. Sign in (Google account works, no billing needed for the free tier).
3. Click **Create API Key**, copy it.
4. Copy `.env.example` to `.env` and paste it in as `GROQ_API_KEY`.

Groq's free tier has generous per-minute/per-day rate limits — plenty for
testing and demoing a class project.

## 2. Set up n8n (no server needed)

1. Sign up for a free account at https://n8n.io (n8n Cloud) — or run
   `npx n8n` locally if you prefer self-hosting.
2. In the n8n editor, click **Import from File** (or **Import from URL**)
   and import `n8n_student_request_workflow.json` from this folder.
3. Open the **Append to Google Sheets** node:
   - Click "Create new credential" and connect your Google account.
   - Create a new Google Sheet with a header row: `Name | Email | Type | Details | Timestamp`.
   - Paste that sheet into the "Document" field.
4. Open both email nodes (**Send Confirmation Email**, **Notify Admin**):
   - Add SMTP credentials (Gmail works: use an "App Password", not your
     normal password — see https://support.google.com/mail/answer/185833).
   - Set `admin@example.com` to your own email so you receive notifications.
5. Click on the **Webhook** node → copy the "Production URL" (or "Test URL"
   while building). This is your `N8N_WEBHOOK_URL`.
6. Paste that URL into your `.env` file.
7. **Activate** the workflow (toggle in the top-right of the n8n editor) so
   the production webhook stays listening.

## 3. Run the Streamlit app

```bash
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here             # or use a .env loader
export N8N_WEBHOOK_URL=your_webhook_url_here
streamlit run app.py
```

Running on Google Colab instead? See `COLAB_SETUP.md`.

## 4. Try it out

- Ask a normal question: *"When is the add/drop deadline?"* → the agent
  answers directly, no automation triggered.
- Ask to submit a request: *"I need to request my transcript"* → the agent
  will ask for your name, email, and details, then automatically send that
  data to n8n. You should see:
  - A new row appear in your Google Sheet
  - A confirmation email land in the student's inbox
  - A notification email land in the admin inbox
  - A green "✅ Automation triggered" banner in the Streamlit app

## 5. Screenshots to capture for your report

1. The Streamlit UI mid-conversation
2. A request being collected by the AI Agent
3. The n8n workflow canvas (all 4 nodes, workflow active)
4. The Google Sheet with a new row added
5. The confirmation email received
6. The final "automation triggered" success message in the app

## Notes for extending

- Swap Google Sheets for SQLite/MySQL/PostgreSQL/MongoDB in n8n if you want
  the "optional advanced component" credit.
- You could add an NLP step (e.g. sentiment analysis on "Details") before
  the Google Sheets node for extra advanced-component credit.
- The system prompt in `app.py` is where you customize the assistant for a
  different domain (Healthcare, E-commerce, etc.) if you change your mind.

## Why Groq instead of Gemini?

The Gemini free-tier API was intermittently rejecting brand-new projects
with an access-denied error — a widespread, ongoing issue on Google's side
unrelated to anything in this project. Groq's API is OpenAI-compatible,
free, requires no billing setup, and has been stable for this use case, so
the assistant now calls Groq's `llama-3.3-70b-versatile` model instead. If
you'd rather use Gemini once Google resolves the issue, swap the `groq`
client calls in `app.py` back to `google-generativeai` — the system prompt
and app logic don't need to change.
