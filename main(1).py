import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st

try:
    from config import API_KEY as CONFIG_API_KEY
except ImportError:
    CONFIG_API_KEY = ""


# ---------------------------------------------------------
# 1. APP CONFIGURATION & LIGHT EDITORIAL PALETTE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Audit Intelligence | Global Banking Briefing",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #F7F8FA;
        --card: #FFFFFF;
        --border: #E5E7EB;
        --text-primary: #111827;
        --text-secondary: #4B5563;
        --text-muted: #6B7280;
        --accent-blue: #2563EB;
        --accent-blue-dark: #1D4ED8;
        --up: #16A34A;
        --down: #DC2626;
        --amber: #B45309;
    }

    .stApp {
        background: var(--bg);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    #MainMenu, header[data-testid="stHeader"] { background: transparent; }

    /* ---------------- Top navigation ---------------- */
    .topnav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 2px 18px 2px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 8px;
    }
    .topnav-left { display: flex; align-items: center; gap: 18px; }

    /* ---- Emblem: deep navy tile, inner bevel, blue rim glow ---- */
    .logo-icon {
        position: relative;
        width: 62px; height: 62px;
        border-radius: 18px;
        background:
            radial-gradient(120% 120% at 28% 18%, #3B82F6 0%, #1D4ED8 42%, #14264F 100%);
        display: flex; align-items: center; justify-content: center;
        box-shadow:
            0 10px 26px rgba(29, 78, 216, 0.38),
            0 2px 5px rgba(11, 18, 32, 0.22),
            inset 0 1px 0 rgba(255, 255, 255, 0.42),
            inset 0 -2px 6px rgba(3, 10, 26, 0.45);
        flex-shrink: 0;
    }
    /* Hairline highlight ring */
    .logo-icon::after {
        content: "";
        position: absolute; inset: 0;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.20);
        pointer-events: none;
    }
    .logo-icon svg { width: 34px; height: 34px; display: block; }

    /* ---- Wordmark ---- */
    .logo-lockup { display: flex; flex-direction: column; }
    .logo-textrow { display: flex; align-items: center; gap: 12px; }
    .logo-text {
        font-weight: 900;
        font-size: 38px;
        letter-spacing: -1.5px;
        line-height: 1.02;
        color: #0B1220;
        white-space: nowrap;
    }
    /* Two-tone: "Audit" in ink, "Intelligence" in a blue gradient */
    .logo-text .lt-accent {
        background: linear-gradient(92deg, #2563EB 0%, #4F46E5 55%, #7C3AED 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #2563EB;
    }

    /* Live status pill */
    .live-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(22, 163, 74, 0.10);
        border: 1px solid rgba(22, 163, 74, 0.35);
        color: #15803D;
        font-size: 10px; font-weight: 800;
        letter-spacing: 1.2px; text-transform: uppercase;
        padding: 4px 10px; border-radius: 999px;
        white-space: nowrap;
    }
    .live-dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: #16A34A;
        box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.65);
        animation: livepulse 2s infinite;
    }
    @keyframes livepulse {
        0%   { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.60); }
        70%  { box-shadow: 0 0 0 7px rgba(22, 163, 74, 0); }
        100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
    }

    /* Strapline with a leading accent rule */
    .logo-sub {
        display: flex; align-items: center; gap: 9px;
        font-size: 11px; font-weight: 700; color: var(--text-muted);
        letter-spacing: 2.1px; text-transform: uppercase; margin-top: 7px;
    }
    .logo-rule {
        width: 30px; height: 3px; border-radius: 2px;
        background: linear-gradient(90deg, #2563EB, #7C3AED);
        flex-shrink: 0;
    }

    /* ---- Top-right principal (Pragati) block ---- */
    .topnav-user {
        display: flex; align-items: center; gap: 16px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 12px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .topnav-user-meta { text-align: right; line-height: 1.3; }
    .topnav-user-label {
        font-size: 10px; font-weight: 700; color: var(--accent-blue);
        letter-spacing: 1px; text-transform: uppercase; margin-bottom: 3px;
    }
    .topnav-user-name { font-weight: 800; font-size: 20px; color: #0B1220; letter-spacing: -0.3px; }
    .topnav-user-title { font-size: 13.5px; color: var(--text-secondary); font-weight: 500; }
    .topnav-user-stamp { font-size: 11px; color: var(--text-muted); margin-top: 4px; font-family: 'JetBrains Mono', monospace; }

    /* Avatar: object-position keeps the face centred inside the circle
       instead of cropping to the shoulders. */
    .avatar-photo {
        width: 68px; height: 68px; border-radius: 50%;
        object-fit: cover;
        object-position: center 22%;
        flex-shrink: 0;
        border: 3px solid #fff;
        box-shadow: 0 0 0 2px var(--accent-blue);
        display: block;
    }
    .avatar-circle-lg {
        width: 68px; height: 68px; border-radius: 50%;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 26px; color: #fff; flex-shrink: 0;
        box-shadow: 0 0 0 2px var(--accent-blue);
    }

    .action-caption {
        font-size: 11.5px; color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace; padding-top: 10px;
    }

    /* ---------------- Section headings ---------------- */
    .section-heading {
        font-size: 15px;
        font-weight: 700;
        color: #0B1220;
        margin: 4px 0 14px 0;
    }
    .page-title {
        font-size: 26px;
        font-weight: 800;
        color: #0B1220;
        letter-spacing: -0.5px;
        margin-bottom: 2px;
    }
    .page-subtitle {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 20px;
    }

    /* ================= TAB VISIBILITY FIX (BaseWeb-safe) ================= */
    .stTabs, div[data-testid="stTabs"] { margin-top: 4px; margin-bottom: 20px; }

    .stTabs div[data-baseweb="tab-list"],
    div[data-testid="stTabs"] [role="tablist"] {
        gap: 4px !important;
        border-bottom: 1px solid var(--border) !important;
        background: transparent !important;
    }

    .stTabs button[data-baseweb="tab"],
    .stTabs button[role="tab"],
    div[data-testid="stTabs"] button[role="tab"],
    .stTabs button[data-baseweb="tab"] *,
    .stTabs button[role="tab"] *,
    div[data-testid="stTabs"] button[role="tab"] * {
        color: #0B1220 !important;
        -webkit-text-fill-color: #0B1220 !important;
        opacity: 1 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px !important;
        text-transform: uppercase !important;
    }

    .stTabs button[data-baseweb="tab"],
    .stTabs button[role="tab"],
    div[data-testid="stTabs"] button[role="tab"] {
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        padding: 9px 18px !important;
        height: auto !important;
    }

    .stTabs button[data-baseweb="tab"]:hover,
    .stTabs button[data-baseweb="tab"]:hover *,
    .stTabs button[role="tab"]:hover,
    .stTabs button[role="tab"]:hover * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background: transparent !important;
    }

    .stTabs button[aria-selected="true"],
    .stTabs button[aria-selected="true"] *,
    div[data-testid="stTabs"] button[aria-selected="true"],
    div[data-testid="stTabs"] button[aria-selected="true"] * {
        color: #2563EB !important;
        -webkit-text-fill-color: #2563EB !important;
        font-weight: 800 !important;
    }
    .stTabs button[aria-selected="true"],
    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 3px solid #2563EB !important;
    }

    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"],
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        background-color: transparent !important;
        background-image: none !important;
        height: 0 !important;
        display: none !important;
    }
    .stTabs button:focus,
    .stTabs button:focus-visible,
    .stTabs button:active {
        outline: none !important;
        box-shadow: none !important;
        color: #2563EB !important;
        -webkit-text-fill-color: #2563EB !important;
    }
    /* ===================================================================== */

    /* ---------------- Inputs ---------------- */
    .stTextInput>div>div>input {
        background-color: #fff !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 10px !important;
        padding: 11px 16px !important;
        font-size: 14px !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }

    /* ---------------- Buttons ---------------- */
    .stButton>button {
        background: var(--accent-blue);
        color: #fff !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13.5px;
        padding: 9px 18px;
    }
    .stButton>button * { color: #fff !important; -webkit-text-fill-color: #fff !important; }
    .stButton>button:hover { background: var(--accent-blue-dark); }
    [data-testid="stDownloadButton"]>button {
        background: #fff;
        color: var(--accent-blue) !important;
        border: 1px solid var(--accent-blue);
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stDownloadButton"]>button:hover { background: #EFF6FF; }

    /* ---------------- Legible light theme inside controls ---------------- */
    [data-testid="stExpander"] {
        background: #fff !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }
    [data-testid="stExpander"] summary {
        background: #fff !important;
        color: var(--text-primary) !important;
    }
    [data-testid="stExpander"] summary:hover { color: var(--accent-blue) !important; }
    [data-testid="stExpanderDetails"] { background: #fff !important; }
    [data-testid="stExpander"] label,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] div { color: var(--text-primary) !important; }
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] { color: var(--text-secondary) !important; }
    [data-testid="stSlider"] div[data-baseweb="slider"] > div { background: #E5E7EB !important; }
    [data-testid="stSlider"] div[role="slider"] {
        background-color: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
    }
    div[data-baseweb="tag"] {
        background-color: rgba(37, 99, 235, 0.10) !important;
        border: 1px solid rgba(37, 99, 235, 0.35) !important;
        color: var(--accent-blue) !important;
    }
    div[data-baseweb="tag"] span { color: var(--accent-blue) !important; }
    div[data-baseweb="tag"] svg { fill: var(--accent-blue) !important; }

    /* ---------------- Featured Analysis hero ---------------- */
    .featured-hero {
        position: relative;
        height: 360px;
        border-radius: 16px;
        background-size: cover;
        background-position: center;
        background-color: #1E3A8A;
        overflow: hidden;
        margin-bottom: 30px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .featured-badge {
        position: absolute; top: 20px; left: 20px;
        color: #fff; font-size: 11px; font-weight: 700;
        padding: 5px 12px; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 0.5px;
        z-index: 2;
    }
    .featured-text { position: absolute; bottom: 24px; left: 28px; right: 28px; z-index: 2; }
    .featured-title {
        font-size: 27px; font-weight: 800; color: #fff; line-height: 1.28;
        margin-bottom: 8px; text-shadow: 0 2px 10px rgba(0,0,0,0.35);
    }
    .featured-meta { font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500; }
    .featured-link-overlay { position: absolute; inset: 0; z-index: 3; }

    /* ---------------- Insight cards ---------------- */
    .insight-card {
        display: flex;
        gap: 20px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        transition: box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .insight-card:hover { border-color: #D1D5DB; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
    .insight-thumb {
        width: 180px; min-width: 180px; height: 128px;
        border-radius: 10px;
        object-fit: cover;
        background-color: #EEF2F7;
        background-repeat: no-repeat;
        background-position: center;
        background-size: 52px 52px;
        border: 1px solid var(--border);
        display: block;
    }
    .insight-content { display: flex; flex-direction: column; min-width: 0; }
    .insight-meta-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .badge {
        display: inline-block; color: #fff; font-size: 10.5px; font-weight: 700;
        padding: 3px 10px; border-radius: 5px; text-transform: uppercase; letter-spacing: 0.4px;
    }
    .insight-date { font-size: 12px; color: var(--text-muted); font-weight: 500; }
    .insight-title-link { text-decoration: none; }
    .insight-title {
        font-size: 17px; font-weight: 700; color: #0B1220;
        line-height: 1.35; margin-bottom: 6px;
    }
    .insight-title-link:hover .insight-title { color: var(--accent-blue); }
    .insight-desc {
        font-size: 13.5px; color: var(--text-secondary); line-height: 1.55;
        margin-bottom: 12px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .insight-footer { display: flex; justify-content: flex-end; align-items: center; margin-top: auto; }
    .read-link {
        font-size: 12.5px; font-weight: 700; color: var(--accent-blue); text-decoration: none;
    }
    .read-link:hover { text-decoration: underline; }

    /* ---------------- Right sidebar panels ---------------- */
    .side-panel {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    .side-panel-title {
        font-size: 11px; font-weight: 700; color: var(--text-secondary);
        text-transform: uppercase; letter-spacing: 0.8px;
        margin-bottom: 14px; display: flex; align-items: center; gap: 6px;
    }
    .filter-row, .pulse-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px; color: #374151;
    }
    .filter-row:last-child, .pulse-row:last-child { border-bottom: none; }
    .filter-value { font-weight: 600; color: var(--text-primary); }
    .pulse-value { font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }

    /* ---------------- Market panel ---------------- */
    .mkt-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 9px 0; border-bottom: 1px solid #F3F4F6;
    }
    .mkt-row:last-child { border-bottom: none; }
    .mkt-name { font-size: 13px; font-weight: 600; color: #374151; }
    .mkt-sub { font-size: 10.5px; color: var(--text-muted); font-weight: 500; }
    .mkt-right { text-align: right; }
    .mkt-price { font-size: 13.5px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
    .mkt-chg { font-size: 11.5px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .mkt-up { color: var(--up); }
    .mkt-down { color: var(--down); }
    .mkt-stamp { font-size: 10.5px; color: var(--text-muted); margin-top: 12px; }

    /* ---------------- Risk radar ---------------- */
    .risk-row { padding: 8px 0; border-bottom: 1px solid #F3F4F6; }
    .risk-row:last-child { border-bottom: none; }
    .risk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .risk-name { font-size: 12.5px; font-weight: 600; color: #374151; }
    .risk-count { font-size: 11px; font-weight: 700; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }
    .risk-track { height: 6px; background: #F3F4F6; border-radius: 3px; overflow: hidden; }
    .risk-fill { height: 100%; border-radius: 3px; }

    .alert-item {
        display: block; text-decoration: none;
        padding: 9px 0; border-bottom: 1px solid #F3F4F6;
    }
    .alert-item:last-child { border-bottom: none; }
    .alert-tag {
        font-size: 9.5px; font-weight: 800; color: var(--amber);
        letter-spacing: 0.6px; text-transform: uppercase;
    }
    .alert-text {
        font-size: 12.5px; color: #0B1220; font-weight: 600; line-height: 1.4; margin-top: 3px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .alert-item:hover .alert-text { color: var(--accent-blue); }

    .cta-panel {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        border-radius: 14px;
        padding: 20px 22px 6px 22px;
        color: #fff;
        margin-bottom: -4px;
    }
    .cta-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
    .cta-desc { font-size: 12.5px; color: rgba(255,255,255,0.85); line-height: 1.5; margin-bottom: 14px; }

    .empty-state-panel {
        text-align: center; padding: 48px;
        background: var(--card); border-radius: 16px; border: 1px dashed var(--border);
        margin-top: 14px;
    }

    /* ---------------- Footer ---------------- */
    .app-footer {
        display: flex; justify-content: space-between; align-items: flex-start;
        padding-top: 22px; margin-top: 8px;
    }
    .footer-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-weight: 800; font-size: 14.5px; color: #0B1220; }
    .footer-tagline { font-size: 12px; color: var(--text-muted); max-width: 320px; line-height: 1.5; }
    .footer-links { display: flex; gap: 22px; font-size: 12.5px; color: var(--text-secondary); font-weight: 600; }
    .footer-copyright { font-size: 11.5px; color: var(--text-muted); margin-top: 18px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. BANKING AUDIT CATEGORIES & QUERIES
# ---------------------------------------------------------

CATEGORIES = {
    "Transformation": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance") AND ("digital transformation" OR "modernization" OR "core banking" OR "automation" OR "artificial intelligence" OR "generative AI" OR "cloud")',
            '("bank" OR "banking") AND ("core banking" OR "digital banking" OR "cloud migration" OR "legacy modernisation" OR "operating model")',
            '("bank" OR "lender" OR "financial services") AND ("artificial intelligence" OR "generative AI" OR "machine learning" OR "automation") AND ("risk" OR "controls" OR "governance" OR "deployment")',
        ]
    },
    "Regulation": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "compliance" OR "risk" OR "governance") AND ("regulation" OR "regulatory" OR "supervision" OR "RBI" OR "Basel" OR "AML" OR "KYC" OR "sanctions" OR "prudential" OR "enforcement")',
            '("Reserve Bank of India" OR "RBI" OR "central bank") AND ("circular" OR "guidelines" OR "penalty" OR "supervisory action" OR "master direction" OR "compliance")',
            '("bank" OR "banking") AND ("anti-money laundering" OR "AML" OR "KYC" OR "sanctions" OR "financial crime" OR "fraud" OR "enforcement action" OR "fined" OR "penalised")',
            '("bank" OR "financial institution") AND ("Basel" OR "prudential" OR "capital adequacy" OR "regulatory capital" OR "stress test" OR "supervisory review")',
        ]
    },
    "People": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "risk" OR "governance" OR "controls") AND ("appointed" OR "appointment" OR "CEO" OR "CFO" OR "CRO" OR "CISO" OR "chief audit" OR "internal audit" OR "audit committee" OR "board")',
            '("bank" OR "banking group") AND ("chief audit executive" OR "head of internal audit" OR "chief risk officer" OR "chief compliance officer" OR "audit committee chair")',
            '("bank" OR "lender") AND ("resigns" OR "steps down" OR "elevated" OR "promoted" OR "succession" OR "board appointment" OR "reshuffle")',
        ]
    },
    "Global Banks": {
        "queries": [
            '("bank" OR "banking group" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance" OR "regulatory") AND ("HSBC" OR "JPMorgan" OR "JPMorgan Chase" OR "Citi" OR "Citigroup" OR "Barclays" OR "Deutsche Bank" OR "UBS" OR "BNP Paribas" OR "Santander" OR "Standard Chartered")',
            '("Bank of America" OR "Goldman Sachs" OR "Morgan Stanley" OR "Wells Fargo" OR "ING" OR "ICBC" OR "MUFG" OR "Mizuho") AND ("audit" OR "risk" OR "compliance" OR "regulator" OR "governance" OR "controls" OR "fine")',
            '("HSBC" OR "Standard Chartered" OR "Citi" OR "Barclays" OR "Deutsche Bank" OR "UBS") AND ("investigation" OR "probe" OR "penalty" OR "settlement" OR "remediation" OR "internal review")',
        ]
    },
}

CATEGORY_DISPLAY = {
    "Transformation": "Transformation",
    "Regulation": "Regulation",
    "People": "People",
    "Global Banks": "Global Banking",
}
CATEGORY_COLORS = {
    "Transformation": "#2563EB",
    "Regulation": "#16A34A",
    "People": "#6B7280",
    "Global Banks": "#7C3AED",
}

PAGE_SIZE = 100
MAX_PAGES = 2

PRAGATI_NAME = "Pragati"
PRAGATI_TITLE = "Head of Internal Audit"

# ---------------------------------------------------------
# Pragati's portrait, embedded as a base64 JPEG so it renders
# inside the custom HTML top-nav (a local file path would not
# resolve there). Centre-cropped to a square, 240x240, ~9 KB.
# ---------------------------------------------------------
PRAGATI_PHOTO_B64 = (
    "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"
)

AUDIT_TERMS = [
    "internal audit", "external audit", "audit committee", "auditor",
    "audit finding", "audit findings", "internal control", "internal controls",
    "control weakness", "control weaknesses", "control deficiency",
    "control deficiencies", "governance", "risk management", "operational risk",
    "model risk", "compliance", "regulatory", "regulation", "supervision",
    "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
    "sanctions", "fraud", "misconduct", "financial crime",
    "bank", "banking", "lender", "rbi", "central bank", "basel", "npa",
    "asset quality", "provisioning", "capital adequacy", "credit risk",
    "liquidity", "penalty", "fined", "probe", "investigation", "whistleblower",
    "disclosure", "restatement", "irregularities", "lapses",
]

ALERT_TERMS = [
    "enforcement", "penalty", "fined", "fine", "fraud", "misconduct",
    "investigation", "probe", "money laundering", "aml", "sanctions",
    "irregularities", "lapses", "control deficiency", "restatement",
    "whistleblower", "settlement",
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
    "Global Banks": [
        "hsbc", "jpmorgan", "jpmorgan chase", "citi", "citigroup", "barclays",
        "deutsche bank", "ubs", "bnpparibas", "bnp paribas", "santander",
        "standard chartered", "bank of america", "goldman sachs", "morgan stanley",
        "wells fargo", "ing", "icbc", "mufg", "mizuho",
    ],
}


def placeholder_data_uri(hex_color="#94A3B8"):
    """
    Inline, URL-encoded newspaper SVG used as the thumbnail fallback.
    Returned as a data: URI so it needs no network call and cannot itself fail.
    """
    c = hex_color.replace("#", "%23")
    return (
        "data:image/svg+xml;charset=utf-8,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        f"stroke='{c}' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E"
        "%3Cpath d='M4 5h13a1 1 0 0 1 1 1v12a2 2 0 0 0 2 2H5a1 1 0 0 1-1-1V5z'/%3E"
        "%3Cpath d='M18 8h2a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2'/%3E"
        "%3Cpath d='M7 8h7'/%3E%3Cpath d='M7 11.5h7'/%3E"
        "%3Cpath d='M7 15h4'/%3E%3Cpath d='M13.5 15h.5'/%3E"
        "%3C/svg%3E"
    )


RISK_THEMES = {
    "Financial crime / AML": (["aml", "anti-money laundering", "money laundering", "kyc", "financial crime", "sanctions"], "#DC2626"),
    "Enforcement / penalties": (["enforcement", "penalty", "fined", "fine", "settlement", "supervisory action"], "#EA580C"),
    "Fraud & misconduct": (["fraud", "misconduct", "irregularities", "lapses", "whistleblower"], "#B45309"),
    "Credit & asset quality": (["npa", "asset quality", "provisioning", "credit risk", "bad loan", "slippage"], "#7C3AED"),
    "Technology & AI risk": (["artificial intelligence", "generative ai", "cloud", "automation", "core banking", "outage"], "#2563EB"),
}


# ---------------------------------------------------------
# 3. EXTRACTION LOGIC & SCORING FUNCTIONS
# ---------------------------------------------------------

def get_api_key():
    if CONFIG_API_KEY.strip():
        return CONFIG_API_KEY.strip()

    env_key = os.getenv("NEWSAPI_KEY", "").strip()
    if env_key:
        return env_key

    try:
        secret_key = st.secrets.get("API_KEY", "") or st.secrets.get("NEWSAPI_KEY", "")
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
    score = 0
    for term in AUDIT_TERMS:
        if term in text:
            score += 5

    for term in [
        "internal audit", "audit committee", "internal controls",
        "control deficiency", "regulatory enforcement",
        "model risk", "financial crime",
    ]:
        if term in text:
            score += 10

    return min(score, 100)


def classify_article(article):
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


def fetch_query(category, query, api_key, from_date, page_size, page):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "page": page,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=25)
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "NewsAPI returned an error."))

    articles = payload.get("articles", [])
    for article in articles:
        article["_query_category"] = category

    return articles, payload.get("totalResults", 0)


@st.cache_data(ttl=300, show_spinner=False)
def load_news(api_key, lookback_days, page_size, min_relevance):
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    jobs = []
    for category, settings in CATEGORIES.items():
        for query in settings["queries"]:
            for page in range(1, MAX_PAGES + 1):
                jobs.append((category, query, page))

    all_articles = []
    errors = []
    api_total = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_query, category, query, api_key, from_date, page_size, page):
                (category, page)
            for category, query, page in jobs
        }

        for future in as_completed(futures):
            category, page = futures[future]
            try:
                rows, total = future.result()
                all_articles.extend(rows)
                api_total = max(api_total, total)
            except Exception as exc:
                msg = str(exc)
                if page > 1 and ("upgrade" in msg.lower() or "developer" in msg.lower()):
                    continue
                errors.append(f"{category} (page {page}): {msg}")

    raw_count = len(all_articles)

    unique = {}
    title_keys = set()

    for article in all_articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip().lower()
        key = url if url else title

        if not key or key in unique or title in title_keys:
            continue

        if title.startswith("[removed]"):
            continue

        unique[key] = article
        title_keys.add(title)

    deduped_count = len(unique)

    cleaned = []
    dropped_low_relevance = 0

    for article in unique.values():
        text = normalize_text(article)
        relevance = audit_relevance(text)

        if relevance < min_relevance:
            dropped_low_relevance += 1
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
            "source": source.get("name") or "Institutional Source",
            "publishedAt": published,
            "url": article.get("url") or "",
            "author": article.get("author") or "",
            "image_url": article.get("urlToImage") or "",
        })

    cleaned.sort(key=lambda x: (x["audit_relevance"], x["publishedAt"]), reverse=True)

    stats = {
        "queries_run": len(jobs),
        "raw": raw_count,
        "deduped": deduped_count,
        "dropped_low_relevance": dropped_low_relevance,
        "kept": len(cleaned),
        "api_total_reported": api_total,
    }
    return cleaned, errors, stats


def format_relative_time(pub_date_str):
    if not pub_date_str:
        return "Recent"
    try:
        clean_str = pub_date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        now = datetime.now(timezone.utc)
        diff = now - dt
        days = diff.days
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        elif days < 7:
            return f"{days} days ago"
        elif days < 14:
            return "1 week ago"
        else:
            return f"{days // 7} weeks ago"
    except Exception:
        return pub_date_str[:10] if len(pub_date_str) >= 10 else "Recent"


def ist_now_str():
    stamp = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return stamp.strftime("%d %b %Y, %H:%M IST")


# ---------------------------------------------------------
# 3b. LIVE MARKET SNAPSHOT
# ---------------------------------------------------------

MARKET_TICKERS = [
    ("^BSESN",   "SENSEX",      "BSE 30"),
    ("^NSEI",    "NIFTY 50",    "NSE"),
    ("^NSEBANK", "BANK NIFTY",  "NSE Banks"),
    ("USDINR=X", "USD / INR",   "Spot FX"),
    ("BZ=F",     "Brent Crude", "USD/bbl"),
    ("GC=F",     "Gold",        "USD/oz"),
]

YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YF_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AuditIntel/1.0)"}


def fetch_quote(symbol):
    resp = requests.get(
        YF_CHART_URL.format(symbol=symbol),
        params={"range": "1d", "interval": "5m"},
        headers=YF_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    meta = resp.json()["chart"]["result"][0]["meta"]

    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")

    if price is None or not prev:
        raise ValueError("No price data returned")

    change = price - prev
    pct = (change / prev) * 100
    return {"price": float(price), "change": float(change), "pct": float(pct)}


@st.cache_data(ttl=180, show_spinner=False)
def load_market_snapshot():
    results = {}

    with ThreadPoolExecutor(max_workers=len(MARKET_TICKERS)) as executor:
        futures = {
            executor.submit(fetch_quote, symbol): symbol
            for symbol, _, _ in MARKET_TICKERS
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception:
                results[symbol] = None

    return results, ist_now_str()


def render_market_panel():
    quotes, stamp = load_market_snapshot()

    rows_html = ""
    for symbol, name, sub in MARKET_TICKERS:
        q = quotes.get(symbol)

        if not q:
            rows_html += (
                f'<div class="mkt-row">'
                f'<div><div class="mkt-name">{name}</div><div class="mkt-sub">{sub}</div></div>'
                f'<div class="mkt-right"><div class="mkt-price" style="color:#9CA3AF;">—</div>'
                f'<div class="mkt-chg" style="color:#9CA3AF;">unavailable</div></div>'
                f'</div>'
            )
            continue

        cls = "mkt-up" if q["pct"] >= 0 else "mkt-down"
        arrow = "▲" if q["pct"] >= 0 else "▼"
        rows_html += (
            f'<div class="mkt-row">'
            f'<div><div class="mkt-name">{name}</div><div class="mkt-sub">{sub}</div></div>'
            f'<div class="mkt-right"><div class="mkt-price">{q["price"]:,.2f}</div>'
            f'<div class="mkt-chg {cls}">{arrow} {abs(q["change"]):,.2f} ({abs(q["pct"]):.2f}%)</div></div>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📈 Live Market Snapshot</div>
        {rows_html}
        <div class="mkt-stamp">Last refreshed {stamp} · delayed data, indicative only</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# 3c. RISK RADAR + PRIORITY ALERTS
# ---------------------------------------------------------

def render_risk_radar(rows):
    if not rows:
        return

    counts = {}
    for theme, (terms, color) in RISK_THEMES.items():
        n = 0
        for row in rows:
            text = f'{row["title"]} {row["description"]}'.lower()
            if any(t in text for t in terms):
                n += 1
        counts[theme] = (n, color)

    peak = max((n for n, _ in counts.values()), default=0)
    if peak == 0:
        return

    rows_html = ""
    for theme, (n, color) in sorted(counts.items(), key=lambda x: x[1][0], reverse=True):
        width = int((n / peak) * 100) if peak else 0
        rows_html += (
            f'<div class="risk-row">'
            f'<div class="risk-head"><span class="risk-name">{theme}</span>'
            f'<span class="risk-count">{n}</span></div>'
            f'<div class="risk-track"><div class="risk-fill" style="width:{width}%; background:{color};"></div></div>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">🎯 Risk Radar · Theme Exposure</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


def render_priority_alerts(rows, limit=5):
    flagged = []
    for row in rows:
        text = f'{row["title"]} {row["description"]}'.lower()
        hits = [t for t in ALERT_TERMS if t in text]
        if hits:
            flagged.append((len(hits), row, hits[0]))

    if not flagged:
        return

    flagged.sort(key=lambda x: (x[0], x[1]["audit_relevance"]), reverse=True)

    items_html = ""
    for _, row, tag in flagged[:limit]:
        items_html += (
            f'<a class="alert-item" href="{row["url"]}" target="_blank">'
            f'<div class="alert-tag">⚠ {tag.upper()} · {row["source"]}</div>'
            f'<div class="alert-text">{row["title"]}</div>'
            f'</a>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">🚨 Priority Alerts ({len(flagged)})</div>
        {items_html}
    </div>
    """, unsafe_allow_html=True)


def render_source_panel(rows, limit=5):
    if not rows:
        return

    counter = Counter(r["source"] for r in rows)
    rows_html = "".join(
        f'<div class="pulse-row"><span>{name}</span><span class="pulse-value">{n}</span></div>'
        for name, n in counter.most_common(limit)
    )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📰 Top Sources</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# 4. TOP NAVIGATION
# ---------------------------------------------------------

# Renders the embedded portrait; falls back to the initial-letter circle only
# if the base64 constant above is somehow empty.
if PRAGATI_PHOTO_B64.strip():
    avatar_html = (
        f'<img src="data:image/jpeg;base64,{PRAGATI_PHOTO_B64}" '
        f'class="avatar-photo" alt="{PRAGATI_NAME}" />'
    )
else:
    avatar_html = f'<div class="avatar-circle-lg">{PRAGATI_NAME[:1].upper()}</div>'

# Emblem: an audit lens (magnifier) whose glass contains a rising analytics
# bar chart, framed by a scanning arc — "examine + measure + monitor".
LOGO_SVG = """
<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M26.6 8.4a13 13 0 0 1 .9 13.4" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>
  <path d="M5.2 22.6a13 13 0 0 1 .5-13.9" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>

  <circle cx="14.6" cy="14.6" r="8.2" stroke="#FFFFFF" stroke-width="2.4"/>
  <circle cx="14.6" cy="14.6" r="8.2" fill="#FFFFFF" fill-opacity="0.14"/>

  <rect x="10.7" y="15.1" width="2.25" height="4.5" rx="1.12" fill="#FFFFFF"/>
  <rect x="13.9" y="12.2" width="2.25" height="7.4" rx="1.12" fill="#FFFFFF"/>
  <rect x="17.1" y="9.6"  width="2.25" height="10"  rx="1.12" fill="#FFFFFF"/>

  <path d="M20.9 20.9 L26.4 26.4" stroke="#FFFFFF" stroke-width="3.1"
        stroke-linecap="round"/>
</svg>
"""

st.markdown(f"""
<div class="topnav">
    <div class="topnav-left">
        <div class="logo-icon">{LOGO_SVG}</div>
        <div class="logo-lockup">
            <div class="logo-textrow">
                <div class="logo-text">Audit<span class="lt-accent">&nbsp;Intelligence</span></div>
                <span class="live-pill"><span class="live-dot"></span>Live</span>
            </div>
            <div class="logo-sub"><span class="logo-rule"></span>Global Banking Risk &amp; Controls Briefing</div>
        </div>
    </div>
    <div class="topnav-user">
        <div class="topnav-user-meta">
            <div class="topnav-user-label">Prepared for</div>
            <div class="topnav-user-name">{PRAGATI_NAME}</div>
            <div class="topnav-user-title">{PRAGATI_TITLE}</div>
            <div class="topnav-user-stamp">{ist_now_str()}</div>
        </div>
        {avatar_html}
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 5. ACTION BAR — one button refreshes BOTH news and markets
# ---------------------------------------------------------

api_key = get_api_key()

act_l, act_r = st.columns([1, 4])

with act_l:
    hard_refresh = st.button("⟲  Refresh All Data", use_container_width=True, key="refresh_all")

with act_r:
    last_run = st.session_state.get("last_refresh", "not yet loaded this session")
    st.markdown(
        f'<div class="action-caption">News + market data · last pulled: {last_run}</div>',
        unsafe_allow_html=True,
    )

if hard_refresh:
    load_news.clear()
    load_market_snapshot.clear()
    st.session_state.pop("news_loaded", None)


# ---------------------------------------------------------
# 6. DATA CONTROLS
# ---------------------------------------------------------

with st.expander("⚙️  Advanced Filters & Data Controls", expanded=(not api_key)):
    if not api_key:
        api_key = st.text_input(
            "NewsAPI Key",
            type="password",
            placeholder="Enter API key...",
            help="Configurable via secrets.toml or config.py for a persistent setup.",
        )

    ctrl_a, ctrl_b = st.columns(2)

    with ctrl_a:
        lookback_days = st.slider("Lookback Window (Days)", min_value=1, max_value=30, value=7)

    with ctrl_b:
        min_relevance = st.slider(
            "Minimum Audit Relevance",
            min_value=0, max_value=40, value=5, step=5,
            help="Lower this to widen the feed; raise it to keep only high-signal stories.",
        )

    selected_categories = st.multiselect(
        "Active Categories",
        options=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        format_func=lambda c: CATEGORY_DISPLAY.get(c, c),
    )

if not api_key:
    st.info("💡 Please enter your NewsAPI key above (or configure API_KEY in Streamlit secrets) to load the briefing.")
    st.stop()


# ---------------------------------------------------------
# 7. DATA INGESTION & FILTERING
# ---------------------------------------------------------

params_key = (lookback_days, min_relevance)

if ("news_loaded" not in st.session_state) or (st.session_state.get("params_key") != params_key):
    with st.spinner("Compiling the audit intelligence briefing..."):
        articles, errors, stats = load_news(api_key, lookback_days, PAGE_SIZE, min_relevance)

    st.session_state.news = articles
    st.session_state.news_errors = errors
    st.session_state.news_stats = stats
    st.session_state.news_loaded = True
    st.session_state.params_key = params_key
    st.session_state.last_refresh = ist_now_str()

articles = st.session_state.get("news", [])
errors = st.session_state.get("news_errors", [])
stats = st.session_state.get("news_stats", {})

filtered = [a for a in articles if a["category"] in selected_categories] if selected_categories else []

with st.expander("🔎 Ingestion Diagnostics", expanded=False):
    if stats:
        st.markdown(
            f"""
            <div style="font-size:12.5px; color:#111827; line-height:1.9;">
            <b>{stats['queries_run']}</b> query/page requests sent ·
            <b>{stats['raw']}</b> articles returned by NewsAPI ·
            <b>{stats['deduped']}</b> after de-duplication ·
            <b>{stats['dropped_low_relevance']}</b> dropped below the relevance floor ·
            <b>{stats['kept']}</b> retained in the briefing
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "If 'retained' is low, lower the Minimum Audit Relevance slider or widen the "
            "lookback window. NewsAPI's free tier also caps each query at 100 results and "
            "roughly one month of history."
        )
    for err in errors:
        st.markdown(f"<div style='font-size:12px; color:#B45309;'>• {err}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 8. PAGE TITLE
# ---------------------------------------------------------

st.markdown('<div class="page-title">This week\'s briefing</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-subtitle">{len(filtered)} items &nbsp;·&nbsp; verified banking internal controls &amp; regulatory surveillance</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 9. RENDER HELPERS
# ---------------------------------------------------------

def render_featured(article):
    color = CATEGORY_COLORS.get(article["category"], "#374151")
    label = CATEGORY_DISPLAY.get(article["category"], article["category"])
    rel_time = format_relative_time(article["publishedAt"])

    if article["image_url"]:
        bg = f'linear-gradient(180deg, rgba(17,24,39,0) 35%, rgba(17,24,39,0.88) 100%), url(\'{article["image_url"]}\')'
    else:
        bg = 'linear-gradient(135deg, #1E3A8A, #2563EB)'

    st.markdown(f"""
    <div class="featured-hero" style="background-image: {bg};">
        <div class="featured-badge" style="background: {color};">{label}</div>
        <div class="featured-text">
            <div class="featured-title">{article['title']}</div>
            <div class="featured-meta">By {article['source']} &nbsp;·&nbsp; {rel_time}</div>
        </div>
        <a href="{article['url']}" target="_blank" class="featured-link-overlay"></a>
    </div>
    """, unsafe_allow_html=True)


def render_insight_card(article):
    color = CATEGORY_COLORS.get(article["category"], "#374151")
    label = CATEGORY_DISPLAY.get(article["category"], article["category"])
    rel_time = format_relative_time(article["publishedAt"])
    description_text = article["description"] or "Independent institutional briefing coverage. Select below to review the full verified source documentation."

    fallback = placeholder_data_uri(color)
    src_attr = f'src="{article["image_url"]}" ' if article["image_url"] else ""

    thumb_html = (
        f'<img class="insight-thumb" {src_attr}alt="" loading="lazy" '
        f'referrerpolicy="no-referrer" '
        f'style="background-image: url(&quot;{fallback}&quot;);" '
        f'onerror="this.onerror=null; this.removeAttribute(\'src\');" />'
    )

    st.markdown(f"""
    <div class="insight-card">
        {thumb_html}
        <div class="insight-content">
            <div class="insight-meta-row">
                <span class="badge" style="background: {color};">{label}</span>
                <span class="insight-date">{rel_time}</span>
            </div>
            <a href="{article['url']}" target="_blank" class="insight-title-link">
                <div class="insight-title">{article['title']}</div>
            </a>
            <div class="insight-desc">{description_text}</div>
            <div class="insight-footer">
                <a href="{article['url']}" target="_blank" class="read-link">Read source ↗</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_feed(rows, show_featured=True):
    if not rows:
        st.markdown("""
        <div class="empty-state-panel">
            <div style="font-size: 18px; font-weight: 700; color: #111827;">No briefing stories found</div>
            <div style="font-size: 13.5px; color: #4B5563; margin-top: 6px;">Try expanding the lookback window or lowering the relevance floor above.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if show_featured:
        st.markdown('<div class="section-heading">Featured Analysis</div>', unsafe_allow_html=True)
        render_featured(rows[0])
        rest = rows[1:]
    else:
        rest = rows

    if rest:
        st.markdown('<div class="section-heading">Latest Insights</div>', unsafe_allow_html=True)
        for art in rest:
            render_insight_card(art)


# ---------------------------------------------------------
# 10. MAIN LAYOUT
# ---------------------------------------------------------

col_main, col_side = st.columns([2.3, 1], gap="large")

with col_main:
    if not filtered:
        render_feed(filtered)
    else:
        tab_labels = ["All Insights"] + [CATEGORY_DISPLAY.get(c, c) for c in selected_categories]
        tabs = st.tabs(tab_labels)

        with tabs[0]:
            render_feed(filtered, show_featured=True)

        for tab, category in zip(tabs[1:], selected_categories):
            with tab:
                cat_rows = [a for a in filtered if a["category"] == category]
                render_feed(cat_rows, show_featured=False)

with col_side:
    render_market_panel()
    render_priority_alerts(filtered)
    render_risk_radar(filtered)
    render_source_panel(filtered)

    active_categories = ", ".join(CATEGORY_DISPLAY.get(c, c) for c in selected_categories) or "None selected"
    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">⚙️ Active Filters</div>
        <div class="filter-row"><span>Categories</span><span class="filter-value">{active_categories}</span></div>
        <div class="filter-row"><span>Lookback</span><span class="filter-value">Last {lookback_days}d</span></div>
        <div class="filter-row"><span>Relevance floor</span><span class="filter-value">{min_relevance}</span></div>
    </div>
    """, unsafe_allow_html=True)

    if filtered:
        today_count = sum(1 for a in filtered if format_relative_time(a["publishedAt"]) == "Today")
        unique_sources = len(set(a["source"] for a in filtered))
    else:
        today_count, unique_sources = 0, 0

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📊 Feed Pulse</div>
        <div class="pulse-row"><span>Total Stories</span><span class="pulse-value">{len(filtered)}</span></div>
        <div class="pulse-row"><span>Published Today</span><span class="pulse-value">{today_count}</span></div>
        <div class="pulse-row"><span>Unique Sources</span><span class="pulse-value">{unique_sources}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="cta-panel">
        <div class="cta-title">Audit Intelligence Brief</div>
        <div class="cta-desc">Export this briefing as a CSV for Audit Committee and Chief Risk Officer distribution.</div>
    </div>
    """, unsafe_allow_html=True)
    if filtered:
        df_export = pd.DataFrame(filtered)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Briefing CSV",
            data=csv,
            file_name=f"audit_intel_briefing_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_csv_sidebar",
        )


# ---------------------------------------------------------
# 11. FOOTER
# ---------------------------------------------------------

st.markdown("""
<div class="app-footer">
    <div>
        <div class="footer-brand"><span>📡</span> Audit Intelligence</div>
        <div class="footer-tagline">Curated intelligence feed for Audit Committees and Chief Risk Officers across banking and financial services.</div>
    </div>
    <div class="footer-links">
        <span>About Us</span>
        <span>Contact</span>
        <span>Privacy Policy</span>
        <span>Terms of Service</span>
    </div>
</div>
<div class="footer-copyright">© 2026 Audit Intelligence &middot; Internal tool &middot; Not for external distribution</div>
""", unsafe_allow_html=True)

