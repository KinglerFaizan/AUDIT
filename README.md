# 🏦 Global Banking Audit Intelligence

A Streamlit application that finds and classifies **global banking news relevant to Audit departments**.

The current project is a simple CLI NewsAPI client. This version changes it into a targeted Streamlit intelligence dashboard.

## What it searches

The application runs five targeted banking-audit searches in parallel:

1. **Transformation**
   - Digital transformation
   - Core banking modernization
   - AI / GenAI
   - Automation
   - Cloud
   - Technology transformation

2. **Regulation**
   - RBI
   - Basel
   - Banking regulation
   - Prudential requirements
   - AML / KYC
   - Sanctions
   - Regulatory enforcement
   - Supervision and compliance

3. **People**
   - CEO / CFO / CRO / CISO appointments
   - Chief Audit leadership
   - Internal Audit
   - Audit Committee
   - Board and governance changes

4. **Cyber and Tech**
   - Cybersecurity
   - Ransomware
   - Data breaches
   - IT Audit
   - Technology risk
   - Cloud security
   - AI governance
   - Model risk

5. **Global Banks**
   - HSBC
   - JPMorgan Chase
   - Citi
   - Barclays
   - Deutsche Bank
   - UBS
   - BNP Paribas
   - Santander
   - Standard Chartered
   - Bank of America
   - Goldman Sachs
   - Morgan Stanley
   - Wells Fargo
   - ING
   - ICBC
   - MUFG
   - Mizuho

## Architecture

```text
                 NewsAPI indexed sources
                          |
             +------------+------------+
             |            |            |
       Transformation Regulation    People
             |            |            |
        Cyber & Tech   Global Banks   ...
             +------------+------------+
                          |
                    Deduplication
                          |
                 Audit relevance filter
                          |
                Rule-based classification
                          |
                    Streamlit dashboard
```

## Why it is faster

The five NewsAPI searches are executed concurrently with `ThreadPoolExecutor`.

The results are also cached for **5 minutes** with Streamlit's `st.cache_data`, so normal Streamlit reruns do not repeatedly call the API.

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

### 2. Install packages

```bash
pip install -r requirements.txt
```

### 3. Configure the API key

Recommended for local development:

```bash
set NEWSAPI_KEY=your_api_key
```

PowerShell:

```powershell
$env:NEWSAPI_KEY="your_api_key"
```

You can also enter the key in the Streamlit sidebar.

For Streamlit deployment, use Streamlit secrets:

```toml
API_KEY = "your_api_key"
```

**Do not commit the real API key to GitHub.**

### 4. Run

```bash
streamlit run main.py
```

## Important limitation

NewsAPI provides access to news sources indexed by NewsAPI. It does **not** mean that the application crawls literally every website on the internet.

For true internet-wide collection, the next architecture should replace/augment NewsAPI with a web extraction layer and a local database.

## Classification

The current classifier is intentionally transparent and free:

- First, targeted queries retrieve banking/audit stories.
- Audit vocabulary removes ordinary banking stories.
- Keyword scoring assigns each retained story to one of the five categories.
- No paid LLM is required.

A future version can add a local open-source model for semantic classification.

## Project structure

```text
News/
├── main.py
├── config.py
├── requirements.txt
├── README.md
└── .gitignore
```

PyCharm `.xml` / `.iml` files are IDE metadata and are not required by the Streamlit application.
