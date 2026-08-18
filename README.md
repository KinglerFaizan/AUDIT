# 🛡️ Audit Intel — Streamlit MVP

An attractive, simple end-to-end demo for an audit-intelligence feed.

## What the MVP does

**RSS → dedup → AI classification → 3-sentence summary → leadership feed → like/dislike signal**

- Audit-first taxonomy: Audit / Transformation / Workflow / Process
- Live RSS scan from banking/audit-focused Google News feeds
- Claude classification + summarization when `ANTHROPIC_API_KEY` is configured
- Demo fallback works without an API key
- SQLite stores reaction signals locally
- Streamlit UI is designed for a leadership demo

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Optional local secrets:

```bash
mkdir .streamlit
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then replace the placeholder API key in `.streamlit/secrets.toml`.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Open https://share.streamlit.io
3. Create app → select the repository → `app.py`.
4. In Advanced settings → Secrets, paste:

```toml
ANTHROPIC_API_KEY = "your-key"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
```

5. Deploy.

If you do not add the API key, the app still runs in demo/fallback mode.

## Important

This is an MVP/demo, not a production banking system. Do not put confidential bank data, credentials, customer data, internal documents, or private access logs in the public repository or public demo.
