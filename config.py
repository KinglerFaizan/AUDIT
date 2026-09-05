"""
Configuration for the Global Banking Audit Intelligence app.

Keep API keys out of GitHub. Set NEWSAPI_KEY as an environment variable,
or add API_KEY to Streamlit secrets.
"""

import os

API_KEY = os.getenv("NEWSAPI_KEY", "dea2d97bff774ce29477bd1ac8c22a32")
