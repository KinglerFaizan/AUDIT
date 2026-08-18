
import os
import re
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    import trafilatura
except Exception:
    trafilatura = None

try:
    import anthropic
except Exception:
    anthropic = None

st.set_page_config(
    page_title="Audit Intel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / CSS
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at 80% 0%, rgba(37,99,235,.10), transparent 28%),
            radial-gradient(circle at 0% 20%, rgba(16,185,129,.07), transparent 25%),
            #07111f;
        color: #e8eef7;
    }
    [data-testid="stSidebar"] {
        background: #081525;
        border-right: 1px solid rgba(255,255,255,.08);
    }
    .block-container { max-width: 1180px; padding-top: 1.5rem; }
    .hero {
        padding: 24px 28px;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(15,32,55,.95), rgba(8,20,35,.88));
        box-shadow: 0 20px 60px rgba(0,0,0,.25);
        margin-bottom: 18px;
    }
    .eyebrow { color:#7dd3fc; font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
    .hero h1 { margin: 4px 0 5px; font-size: 40px; line-height:1.05; }
    .hero p { color:#a9b8ca; margin:0; font-size:16px; }
    .metric {
        border:1px solid rgba(255,255,255,.08);
        background:rgba(255,255,255,.035);
        border-radius:16px;
        padding:14px 16px;
    }
    .metric .v { font-size:25px; font-weight:800; }
    .metric .l { color:#91a2b7; font-size:12px; }
    .chip {
        display:inline-block; padding:5px 9px; border-radius:999px;
        font-size:11px; font-weight:800; margin-right:5px;
        border:1px solid rgba(255,255,255,.08);
    }
    .chip-audit { background:#0c2742; color:#7dd3fc; }
    .chip-transform { background:#102d25; color:#6ee7b7; }
    .chip-workflow { background:#2b2110; color:#fcd34d; }
    .chip-process { background:#2a1727; color:#f9a8d4; }
    .source { color:#8ea2b8; font-size:12px; font-weight:700; }
    .card {
        border:1px solid rgba(255,255,255,.09);
        border-radius:20px;
        background:linear-gradient(145deg, rgba(16,31,51,.95), rgba(9,20,34,.96));
        padding:20px 22px 16px;
        margin:0 0 14px;
        box-shadow:0 12px 35px rgba(0,0,0,.16);
    }
    .card h3 { margin:8px 0 7px; font-size:21px; }
    .summary { color:#c4d0df; font-size:14px; line-height:1.55; }
    .tiny { color:#72849a; font-size:11px; }
    .ai-badge {
        display:inline-flex; gap:6px; align-items:center;
        padding:4px 8px; border-radius:999px;
        background:rgba(124,58,237,.13); color:#c4b5fd;
        border:1px solid rgba(167,139,250,.18); font-size:10px; font-weight:800;
    }
    .section-title { font-size:18px; font-weight:800; margin:12px 0 10px; }
    div.stButton > button {
        border-radius:12px; border:1px solid rgba(255,255,255,.12);
        background:#102238; color:#eaf2fb; font-weight:700;
    }
    div.stButton > button:hover { border-color:#38bdf8; color:white; }
    .footer-note { color:#687c93; font-size:11px; margin-top:18px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Demo data
# -----------------------------
DEMO_ARTICLES = [
    {
        "title": "Banking audit teams accelerate AI-enabled control testing",
        "source": "Banking Technology Review",
        "category": "Transformation",
        "summary": "Large banks are moving repetitive control testing toward AI-assisted workflows, with audit teams focusing more on exception review and judgment. The shift is strongest where evidence collection and documentation can be standardized.",
        "url": "https://example.com/audit-ai",
        "published": "Demo • Today",
    },
    {
        "title": "ServiceNow expands workflow automation for financial operations",
        "source": "ServiceNow",
        "category": "Workflow",
        "summary": "Workflow platforms are increasingly being used to connect intake, approvals, evidence and remediation across control processes. The practical audit opportunity is to reduce handoffs while preserving traceability.",
        "url": "https://www.servicenow.com/",
        "published": "Demo • Yesterday",
    },
    {
        "title": "Banks modernize internal audit operating models",
        "source": "Banking Conclave",
        "category": "Process",
        "summary": "Internal audit functions are redesigning operating models around data-driven risk assessment, centralized evidence and faster issue remediation. Transformation programs are also changing the skills expected from audit professionals.",
        "url": "https://example.com/internal-audit",
        "published": "Demo • 2 days ago",
    },
    {
        "title": "Agentic AI emerges as a priority for audit transformation",
        "source": "AI & Risk Journal",
        "category": "Transformation",
        "summary": "Agentic systems are being explored for multi-step audit tasks such as evidence gathering, policy comparison and exception triage. Governance, human approval and auditability remain the key adoption constraints.",
        "url": "https://example.com/agentic-ai-audit",
        "published": "Demo • 3 days ago",
    },
    {
        "title": "Regulators emphasize traceability as AI use expands in banking",
        "source": "Risk & Compliance Monitor",
        "category": "Audit",
        "summary": "As banks expand AI use, audit and compliance teams are paying greater attention to model decisions, evidence lineage and control ownership. This creates demand for workflows that can explain what happened and why.",
        "url": "https://example.com/ai-controls",
        "published": "Demo • 4 days ago",
    },
    {
        "title": "Digital evidence collection cuts manual audit effort",
        "source": "Financial Services Tech",
        "category": "Workflow",
        "summary": "Automated evidence collection can reduce repetitive requests across control owners and give auditors a more consistent evidence trail. Integration with existing workflow systems is a major implementation consideration.",
        "url": "https://example.com/evidence",
        "published": "Demo • 5 days ago",
    },
]

# Google News RSS is used as a resilient demo-friendly live source.
SOURCE_GROUPS = {
    "Audit": [
        ("Audit + Banking", "https://news.google.com/rss/search?q=" + quote_plus("banking internal audit AI") + "&hl=en-IN&gl=IN&ceid=IN:en"),
        ("Agentic AI + Audit", "https://news.google.com/rss/search?q=" + quote_plus("agentic AI audit banking") + "&hl=en-IN&gl=IN&ceid=IN:en"),
    ],
    "Transformation": [
        ("Bank Transformation", "https://news.google.com/rss/search?q=" + quote_plus("bank digital transformation AI") + "&hl=en-IN&gl=IN&ceid=IN:en"),
        ("Workflow + Banking", "https://news.google.com/rss/search?q=" + quote_plus("banking workflow automation ServiceNow") + "&hl=en-IN&gl=IN&ceid=IN:en"),
    ],
}

CATEGORIES = ["All", "Audit", "Transformation", "Workflow", "Process"]

# -----------------------------
# Helpers
# -----------------------------
def get_secret(name, default=""):
    try:
        value = st.secrets.get(name, "")
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)

def db_conn():
    conn = sqlite3.connect("audit_intel.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            item_id TEXT PRIMARY KEY,
            reaction TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn

def get_reactions():
    conn = db_conn()
    rows = conn.execute("SELECT item_id, reaction FROM reactions").fetchall()
    conn.close()
    return {k: v for k, v in rows}

def save_reaction(item_id, reaction):
    conn = db_conn()
    conn.execute(
        "INSERT INTO reactions(item_id,reaction,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(item_id) DO UPDATE SET reaction=excluded.reaction, updated_at=excluded.updated_at",
        (item_id, reaction, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()

def item_id(item):
    return hashlib.sha1((item.get("url","") + item.get("title","")).encode()).hexdigest()[:12]

def clean_text(text):
    text = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()

def fetch_rss(feed_url, source_name, limit=5):
    parsed = feedparser.parse(feed_url)
    items = []
    for entry in parsed.entries[:limit]:
        title = clean_text(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        published = entry.get("published", "") or entry.get("updated", "")
        if title and link:
            items.append({
                "title": title,
                "source": source_name,
                "url": link,
                "raw_text": summary,
                "published": published,
            })
    return items

def classify_heuristic(text):
    t = text.lower()
    if any(x in t for x in ["workflow", "servicenow", "automation", "evidence collection"]):
        return "Workflow"
    if any(x in t for x in ["internal audit", "audit", "control testing", "assurance"]):
        return "Audit"
    if any(x in t for x in ["process", "operating model", "remediation"]):
        return "Process"
    return "Transformation"

def heuristic_summary(text, title):
    text = clean_text(text)
    if not text:
        return f"{title}. The item is relevant to banking transformation and audit intelligence."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    usable = [s.strip() for s in sentences if len(s.strip()) > 25]
    if usable:
        return " ".join(usable[:3])[:650]
    return text[:650]

def llm_analyze(title, source, text):
    api_key = get_secret("ANTHROPIC_API_KEY")
    model = get_secret("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    if not api_key or anthropic is None:
        return classify_heuristic(title + " " + text), heuristic_summary(text, title), False

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""
You are an audit-intelligence analyst for a large bank.

Classify this item into exactly ONE category:
Audit, Transformation, Workflow, Process.

Priority rule: Audit is the dominant funnel. Use Audit when the item is materially about internal audit, controls, assurance, testing, evidence, audit operating model, or audit technology.

Return ONLY valid JSON:
{{"category":"...", "title":"short improved title", "summary":"3 concise sentences for a senior banking leader"}}

SOURCE: {source}
TITLE: {title}
CONTENT:
{text[:8000]}
"""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=350,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        data = json.loads(raw)
        category = data.get("category", "Transformation")
        if category not in CATEGORIES[1:]:
            category = "Transformation"
        return category, data.get("summary", heuristic_summary(text, title)), True
    except Exception:
        return classify_heuristic(title + " " + text), heuristic_summary(text, title), False

def live_scan(max_per_source=4):
    raw = []
    for group, sources in SOURCE_GROUPS.items():
        for name, url in sources:
            try:
                raw.extend(fetch_rss(url, name, max_per_source))
            except Exception:
                pass

    # Deduplicate by URL.
    seen = set()
    unique = []
    for x in raw:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        unique.append(x)

    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    for x in unique[:12]:
        category, summary, ai_used = llm_analyze(x["title"], x["source"], x["raw_text"])
        results.append({
            "title": x["title"],
            "source": x["source"],
            "category": category,
            "summary": summary,
            "url": x["url"],
            "published": x["published"] or "Recent",
            "ai_used": ai_used,
        })
    return results

def load_demo():
    return [dict(x, ai_used=False) for x in DEMO_ARTICLES]

# -----------------------------
# Session state
# -----------------------------
if "items" not in st.session_state:
    st.session_state["feed_items"] = load_demo()
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

reactions = get_reactions()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 🛡️ Audit Intel")
    st.caption("AI-powered audit transformation feed")
    st.divider()

    st.markdown("### Feed")
    selected = st.radio("View", CATEGORIES, index=0, label_visibility="collapsed")

    st.markdown("### Scan controls")
    max_items = st.slider("Items per source", 2, 6, 4)
    if st.button("🔎 Run live intelligence scan", use_container_width=True, type="primary"):
        with st.spinner("Scanning sources → classifying → summarizing..."):
            fresh = live_scan(max_items)
        if fresh:
            st.session_state["feed_items"] = fresh + st.session_state["feed_items"]
            st.session_state["feed_items"] = st.session_state["feed_items"][:30]
            st.session_state.last_scan = datetime.now().strftime("%d %b %Y, %H:%M")
            st.success(f"Added {len(fresh)} fresh items.")
        else:
            st.warning("Live sources returned no items. Demo feed is still available.")

    if st.button("♻️ Reset to demo feed", use_container_width=True):
        st.session_state["feed_items"] = load_demo()
        st.session_state.last_scan = None
        st.rerun()

    st.divider()
    api_ready = bool(get_secret("ANTHROPIC_API_KEY"))
    st.markdown("### System status")
    st.write("🟢 RSS ingestion")
    st.write("🟢 Deduplication")
    st.write(("🟢" if api_ready else "🟡") + (" Claude AI" if api_ready else " Demo AI fallback"))
    st.write("🟢 Reaction signals")

    st.divider()
    st.caption("MVP • 90-day relevance window • Audit-first funnel")

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero">
  <div class="eyebrow">AUDIT INTELLIGENCE • MVP</div>
  <h1>What’s changing in banking audit?</h1>
  <p>A curated, AI-assisted feed of transformation, workflow and process intelligence — built for leadership scanning.</p>
</div>
""", unsafe_allow_html=True)

items = st.session_state["feed_items"]
filtered = items if selected == "All" else [x for x in items if x["category"] == selected]

# Metrics
c1, c2, c3, c4 = st.columns(4)
metrics = [
    ("v", len(items), "Items in feed"),
    ("v", sum(1 for x in items if x["category"] == "Audit"), "Audit signals"),
    ("v", sum(1 for x in items if x.get("ai_used")), "AI analyzed"),
    ("v", len([1 for x in reactions.values() if x == "like"]), "Likes captured"),
]
for col, (_, value, label) in zip([c1,c2,c3,c4], metrics):
    with col:
        st.markdown(f'<div class="metric"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Intel feed</div>', unsafe_allow_html=True)
if st.session_state.last_scan:
    st.caption(f"Last live scan: {st.session_state.last_scan}")

# -----------------------------
# Feed cards
# -----------------------------
if not filtered:
    st.info("No items in this category yet. Run a live scan or reset the demo feed.")
else:
    for i, item in enumerate(filtered):
        iid = item_id(item)
        reaction = reactions.get(iid)
        cat = item["category"].lower()
        chip_class = "chip-audit" if cat == "audit" else "chip-transform" if cat == "transformation" else "chip-workflow" if cat == "workflow" else "chip-process"
        ai = '<span class="ai-badge">✦ CLAUDE ANALYZED</span>' if item.get("ai_used") else '<span class="ai-badge">◌ DEMO ANALYSIS</span>'
        st.markdown(f"""
        <div class="card">
          <div>
            <span class="chip {chip_class}">{item["category"]}</span>
            {ai}
          </div>
          <h3>{item["title"]}</h3>
          <div class="source">◉ {item["source"]} &nbsp;•&nbsp; {item.get("published","Recent")}</div>
          <p class="summary">{item["summary"]}</p>
        </div>
        """, unsafe_allow_html=True)

        b1, b2, b3, b4 = st.columns([0.08, 0.08, 0.15, 0.69])
        with b1:
            if st.button("♥", key=f"like_{iid}", help="More like this"):
                save_reaction(iid, "like")
                reactions[iid] = "like"
                st.rerun()
        with b2:
            if st.button("×", key=f"dis_{iid}", help="Less like this"):
                save_reaction(iid, "dislike")
                reactions[iid] = "dislike"
                st.rerun()
        with b3:
            st.link_button("Read source ↗", item["url"])
        with b4:
            if reaction:
                st.caption(f"Signal captured: **{reaction}**")

st.markdown("""
<div class="footer-note">
MVP architecture: RSS → dedup → Claude classification/summarization → feed → reaction signal.
For production, move SQLite to Postgres and schedule ingestion. Do not place bank-confidential data or credentials in a public repository.
</div>
""", unsafe_allow_html=True)
