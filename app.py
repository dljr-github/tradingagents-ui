"""TradingAgents UI — Streamlit entry point."""

from pathlib import Path

import streamlit as st
from core.database import init_db

# Initialize database on first load
init_db()

st.set_page_config(
    page_title="TradingAgents",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load CSS from static files
# ---------------------------------------------------------------------------
_STATIC = Path(__file__).parent / "static"

st.markdown(
    f"<style>{(_STATIC / 'style.css').read_text()}</style>",
    unsafe_allow_html=True,
)

if st.session_state.get("theme") == "light":
    st.markdown(
        f"<style>{(_STATIC / 'style_light.css').read_text()}</style>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Sidebar — branding + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
             fill="none" stroke="#0e1117" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
            <polyline points="17 6 23 6 23 12"/></svg>
        </div>
        <div>
            <div class="brand-text">TradingAgents</div>
            <div class="brand-sub">AI-Powered Analysis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Theme toggle
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"
    theme_label = "Light Mode" if st.session_state["theme"] == "dark" else "Dark Mode"
    if st.button(theme_label, key="theme_toggle", use_container_width=True):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

    st.divider()

    PAGES = {
        "Screener": "screener",
        "Analysis": "analysis",
        "Results": "results",
        "History": "history",
        "News": "news",
        "Alerts": "alerts",
        "Portfolio": "portfolio",
        "Comparison": "comparison",
        "Settings": "settings",
    }
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
elif selected == "news":
    from views.news import render
elif selected == "alerts":
    from views.alerts import render
elif selected == "portfolio":
    from views.portfolio import render
elif selected == "comparison":
    from views.comparison import render
elif selected == "settings":
    from views.settings import render

render()
