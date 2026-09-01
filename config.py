"""
Configuration for the Global Banking Audit Intelligence app.

Keep API keys out of GitHub. Set NEWSAPI_KEY as an environment variable,
or add API_KEY to Streamlit secrets.
"""

import os

API_KEY = os.getenv("NEWSAPI_KEY", "1186ffb930c54389982ecd79cb9b5fae")
