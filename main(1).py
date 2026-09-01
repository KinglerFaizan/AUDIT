import os
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

from config import API_KEY as CONFIG_API_KEY


# ---------------------------------------------------------
# APP CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Global Banking Audit Intelligence",
    page_icon="🏦",
    layout="wide",
)

CATEGORIES = {
    "Transformation": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance") AND ("digital transformation" OR "modernization" OR "core banking" OR "automation" OR "artificial intelligence" OR "generative AI" OR "cloud")'
    },
    "Regulation": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "compliance" OR "risk" OR "governance") AND ("regulation" OR "regulatory" OR "supervision" OR "RBI" OR "Basel" OR "AML" OR "KYC" OR "sanctions" OR "prudential" OR "enforcement")'
    },
    "People": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "risk" OR "governance" OR "controls") AND ("appointed" OR "appointment" OR "CEO" OR "CFO" OR "CRO" OR "CISO" OR "chief audit" OR "internal audit" OR "audit committee" OR "board")'
    },
    "Cyber and Tech": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "IT controls" OR "risk" OR "governance") AND ("cybersecurity" OR "cyber attack" OR "ransomware" OR "data breach" OR "information security" OR "technology risk" OR "IT audit" OR "cloud security" OR "AI governance" OR "model risk")'
    },
    "Global Banks": {
        "query": '("bank" OR "banking group" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance" OR "regulatory") AND ("HSBC" OR "JPMorgan" OR "JPMorgan Chase" OR "Citi" OR "Citigroup" OR "Barclays" OR "Deutsche Bank" OR "UBS" OR "BNP Paribas" OR "Santander" OR "Standard Chartered" OR "Bank of America" OR "Goldman Sachs" OR "Morgan Stanley" OR "Wells Fargo" OR "ING" OR "ICBC" OR "MUFG" OR "Mizuho")'
    },
}

# Extra audit vocabulary is used to remove ordinary banking stories.
AUDIT_TERMS = [
    "internal audit", "external audit", "audit committee", "auditor",
    "audit finding", "audit findings", "internal control", "internal controls",
    "control weakness", "control weaknesses", "control deficiency",
    "control deficiencies", "governance", "risk management", "operational risk",
    "model risk", "compliance", "regulatory", "regulation", "supervision",
    "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
    "sanctions", "cybersecurity", "cyber security", "it audit", "technology risk",
    "data breach", "ransomware", "fraud", "misconduct", "financial crime",
]

CATEGORY_TERMS = {
    "Transformation": [
        "digital transformation", "modernization", "modernisation", "core banking",
        "automation", "artificial intelligence", "generative ai", "genai",
        "machine learning", "cloud", "digital banking", "technology transformation",
        "operating model",
    ],
    "Regulation": [
        "regulation", "regulatory", "rbi", "basel", "prudential", "supervision",
        "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
        "sanctions", "capital requirements", "regulatory capital", "compliance",
    ],
    "People": [
        "appointed", "appointment", "ceo", "cfo", "cro", "ciso", "chief audit",
        "internal audit", "audit committee", "board", "director", "chairman",
        "chairwoman", "leadership", "executive",
    ],
    "Cyber and Tech": [
        "cybersecurity", "cyber security", "cyber attack", "ransomware",
        "data breach", "information security", "technology risk", "it audit",
        "cloud security", "ai governance", "model risk", "digital", "technology",
    ],
    "Global Banks": [
        "hsbc", "jpmorgan", "jpmorgan chase", "citi", "citigroup", "barclays",
        "deutsche bank", "ubs", "bnpparibas", "bnp paribas", "santander",
        "standard chartered", "bank of america", "goldman sachs", "morgan stanley",
        "wells fargo", "ing", "icbc", "mufg", "mizuho",
    ],
}


def get_api_key():
    """Use Streamlit secrets/env first; sidebar entry is the local fallback."""
    if CONFIG_API_KEY.strip():
        return CONFIG_API_KEY.strip()

    env_key = os.getenv("NEWSAPI_KEY", "").strip()
    if env_key:
        return env_key

    try:
        secret_key = st.secrets.get("API_KEY", "")
        if secret_key:
            return str(secret_key).strip()
    except Exception:
        pass

    return ""


def normalize_text(article):
    fields = [
        article.get("title") or "",
        article.get("description") or "",
        article.get("content") or "",
    ]
    return " ".join(fields).lower()


def audit_relevance(text):
    """Simple, fast, transparent audit relevance score: 0-100."""
    score = 0
    for term in AUDIT_TERMS:
        if term in text:
            score += 5

    # Stronger signals get additional weight.
    for term in [
        "internal audit", "audit committee", "internal controls",
        "control deficiency", "regulatory enforcement", "it audit",
        "technology risk", "financial crime",
    ]:
        if term in text:
            score += 10

    return min(score, 100)


def classify_article(article):
    """Classify using transparent keyword scoring; no paid LLM is required."""
    text = normalize_text(article)
    scores = {}

    for category, terms in CATEGORY_TERMS.items():
        score = 0
        for term in terms:
            if term in text:
                score += 1
        scores[category] = score

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        best_category = "Regulation"

    return best_category, scores[best_category]


def fetch_category(category, query, api_key, from_date, page_size):
    """Fetch one category from NewsAPI."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "NewsAPI returned an error."))

    rows = []
    for article in payload.get("articles", []):
        article["_query_category"] = category
        rows.append(article)

    return rows


@st.cache_data(ttl=300, show_spinner=False)
def load_news(api_key, lookback_days, page_size):
    """
    Fetch all five targeted searches in parallel.
    Cached for 5 minutes so Streamlit reruns do not repeatedly call NewsAPI.
    """
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    all_articles = []
    errors = []

    with ThreadPoolExecutor(max_workers=len(CATEGORIES)) as executor:
        futures = {
            executor.submit(
                fetch_category,
                category,
                settings["query"],
                api_key,
                from_date,
                page_size,
            ): category
            for category, settings in CATEGORIES.items()
        }

        for future in as_completed(futures):
            category = futures[future]
            try:
                all_articles.extend(future.result())
            except Exception as exc:
                errors.append(f"{category}: {exc}")

    # Deduplicate by URL first, then by normalized title.
    unique = {}
    title_keys = set()

    for article in all_articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip().lower()
        key = url if url else title

        if not key or key in unique or title in title_keys:
            continue

        unique[key] = article
        title_keys.add(title)

    cleaned = []
    for article in unique.values():
        text = normalize_text(article)
        relevance = audit_relevance(text)

        # Only retain stories with a meaningful audit/risk/control signal.
        if relevance < 5:
            continue

        category, category_score = classify_article(article)

        source = article.get("source") or {}
        published = article.get("publishedAt") or ""

        cleaned.append({
            "category": category,
            "audit_relevance": relevance,
            "category_score": category_score,
            "title": article.get("title") or "Untitled",
            "description": article.get("description") or "",
            "source": source.get("name") or "Unknown source",
            "publishedAt": published,
            "url": article.get("url") or "",
            "author": article.get("author") or "",
        })

    cleaned.sort(key=lambda x: (x["audit_relevance"], x["publishedAt"]), reverse=True)
    return cleaned, errors


# ---------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------

st.title("🏦 Global Banking Audit Intelligence")
st.caption(
    "Targeted global banking news focused on Audit, Risk, Controls, "
    "Regulation, Cyber/Technology and Banking Leadership."
)

with st.sidebar:
    st.header("⚙️ Search settings")

    api_key = get_api_key()

    if not api_key:
        api_key = st.text_input(
            "NewsAPI key",
            type="password",
            help="Your key is used only for this Streamlit session.",
        )

    lookback_days = st.slider(
        "Look back (days)",
        min_value=1,
        max_value=7,
        value=3,
    )

    page_size = st.slider(
        "Articles per category",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
    )

    selected_categories = st.multiselect(
        "Categories",
        list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
    )

    min_relevance = st.slider(
        "Minimum audit relevance",
        min_value=5,
        max_value=50,
        value=5,
        step=5,
    )

    refresh = st.button("🔄 Fetch latest news", type="primary", use_container_width=True)

if not api_key:
    st.warning(
        "Add your NewsAPI key in the sidebar, or configure API_KEY in "
        "Streamlit secrets."
    )
    st.stop()

if refresh or "news_loaded" not in st.session_state:
    with st.spinner("Fetching targeted global audit news..."):
        articles, errors = load_news(api_key, lookback_days, page_size)

    st.session_state.news = articles
    st.session_state.news_errors = errors
    st.session_state.news_loaded = True

articles = st.session_state.get("news", [])
errors = st.session_state.get("news_errors", [])

if selected_categories:
    filtered = [
        a for a in articles
        if a["category"] in selected_categories
        and a["audit_relevance"] >= min_relevance
    ]
else:
    filtered = []

# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Audit stories", len(filtered))
m2.metric("Transformation", sum(a["category"] == "Transformation" for a in filtered))
m3.metric("Regulation", sum(a["category"] == "Regulation" for a in filtered))
m4.metric("Cyber & Tech", sum(a["category"] == "Cyber and Tech" for a in filtered))
m5.metric("Global Banks", sum(a["category"] == "Global Banks" for a in filtered))

st.divider()

if errors:
    with st.expander("⚠️ Source/API warnings"):
        for error in errors:
            st.write(error)

if not filtered:
    st.info(
        "No matching audit stories were found. Try increasing the lookback "
        "period or lowering the relevance threshold."
    )
else:
    df = pd.DataFrame(filtered)

    # Category tabs make the dashboard easier to use.
    tabs = st.tabs(["All", *selected_categories])

    def render_articles(rows):
        for article in rows:
            category = article["category"]
            relevance = article["audit_relevance"]
            title = article["title"]
            source = article["source"]
            published = article["publishedAt"]

            st.markdown(f"### {title}")
            st.caption(
                f"**{category}**  •  {source}  •  "
                f"Audit relevance: {relevance}/100  •  {published}"
            )

            if article["description"]:
                st.write(article["description"])

            if article["url"]:
                st.link_button("Read original article", article["url"])

            st.divider()

    with tabs[0]:
        render_articles(filtered)

    for tab, category in zip(tabs[1:], selected_categories):
        with tab:
            render_articles(
                [a for a in filtered if a["category"] == category]
            )

st.caption(
    "Data source: NewsAPI. This application searches NewsAPI's indexed sources; "
    "it does not literally crawl every website on the internet."
)
