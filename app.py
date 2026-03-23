"""TradingAgents UI — Streamlit entry point."""

import streamlit as st
from core.database import init_db

# Initialize database on first load
init_db()

st.set_page_config(
    page_title="TradingAgents",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .rating-buy { color: #00d26a; font-weight: bold; }
    .rating-overweight { color: #7dd87d; font-weight: bold; }
    .rating-hold { color: #ffd700; font-weight: bold; }
    .rating-underweight { color: #ff8c42; font-weight: bold; }
    .rating-sell { color: #ff4444; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    div[data-testid="stMetric"] { background: rgba(28, 34, 48, 0.6); padding: 12px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# Navigation — plain text labels (no emojis)
PAGES = {
    "Screener": "screener",
    "Analysis": "analysis",
    "Results": "results",
    "History": "history",
    "Settings": "settings",
}

with st.sidebar:
    st.title("TradingAgents")
    st.caption("AI-Powered Trading Analysis")
    st.divider()
    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    selected = PAGES[page]

# Import and render selected page
if selected == "screener":
    from views.screener import render
elif selected == "analysis":
    from views.analysis import render
elif selected == "results":
    from views.results import render
elif selected == "history":
    from views.history import render
elif selected == "settings":
    from views.settings import render

render()
