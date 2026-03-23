"""Results page — view detailed analysis results."""

import json

import streamlit as st
from core.database import get_run, get_runs


RATING_COLORS = {
    "BUY": "#00d26a",
    "OVERWEIGHT": "#7dd87d",
    "HOLD": "#ffd700",
    "UNDERWEIGHT": "#ff8c42",
    "SELL": "#ff4444",
}


def render():
    st.header("📋 Analysis Results")

    # Run selector
    run_id = st.session_state.get("view_run_id")

    completed_runs = get_runs(status="completed", limit=50)
    if not completed_runs and not run_id:
        st.info("No completed analyses yet. Start one from the Analysis page.")
        return

    # Dropdown to select a run
    run_options = {f"#{r['id']} — {r['ticker']} ({r['trade_date']}) → {r.get('rating', '?')}": r["id"] for r in completed_runs}

    if run_options:
        selected_label = st.selectbox(
            "Select Analysis Run",
            list(run_options.keys()),
            index=0 if not run_id else next(
                (i for i, rid in enumerate(run_options.values()) if rid == run_id), 0
            ),
        )
        run_id = run_options[selected_label]

    if not run_id:
        return

    run = get_run(run_id)
    if not run:
        st.error(f"Run #{run_id} not found.")
        return

    _render_run_detail(run)


def _render_run_detail(run: dict):
    # Header card
    rating = (run.get("rating") or "N/A").upper()
    color = RATING_COLORS.get(rating, "#888")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    col1.markdown(f"### {run['ticker']}")
    col2.markdown(f"**Date:** {run['trade_date']}")
    col3.markdown(f"**Completed:** {run.get('completed_at', 'N/A')}")
    col4.markdown(f"<h3 style='color: {color};'>{rating}</h3>", unsafe_allow_html=True)

    st.divider()

    # Tabs for each report section
    tabs = st.tabs([
        "Market Analysis",
        "Sentiment",
        "News",
        "Fundamentals",
        "Bull vs Bear",
        "Risk Discussion",
        "Portfolio Manager",
        "Raw JSON",
    ])

    with tabs[0]:
        _render_report(run.get("market_report"), "Market Analysis")

    with tabs[1]:
        _render_report(run.get("sentiment_report"), "Sentiment Analysis")

    with tabs[2]:
        _render_report(run.get("news_report"), "News Analysis")

    with tabs[3]:
        _render_report(run.get("fundamentals_report"), "Fundamentals Analysis")

    with tabs[4]:
        _render_debate(run.get("debate_history"))

    with tabs[5]:
        _render_risk(run.get("risk_history"))

    with tabs[6]:
        _render_report(run.get("final_decision"), "Portfolio Manager Decision")

    with tabs[7]:
        _render_raw_json(run.get("full_state_json"))


def _render_report(content: str | None, title: str):
    if not content or content.strip() == "":
        st.info(f"No {title.lower()} data available for this run.")
        return
    st.markdown(content)


def _render_debate(debate_json: str | None):
    if not debate_json:
        st.info("No debate history available.")
        return

    try:
        debate = json.loads(debate_json)
    except (json.JSONDecodeError, TypeError):
        st.markdown(str(debate_json))
        return

    col_bull, col_bear = st.columns(2)

    with col_bull:
        st.subheader("🟢 Bull Case")
        bull = debate.get("bull_history", "")
        if bull:
            st.markdown(bull)
        else:
            st.info("No bull arguments recorded.")

    with col_bear:
        st.subheader("🔴 Bear Case")
        bear = debate.get("bear_history", "")
        if bear:
            st.markdown(bear)
        else:
            st.info("No bear arguments recorded.")

    judge = debate.get("judge_decision", "")
    if judge:
        st.divider()
        st.subheader("⚖️ Research Manager Verdict")
        st.markdown(judge)


def _render_risk(risk_json: str | None):
    if not risk_json:
        st.info("No risk discussion available.")
        return

    try:
        risk = json.loads(risk_json)
    except (json.JSONDecodeError, TypeError):
        st.markdown(str(risk_json))
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🔥 Aggressive")
        st.markdown(risk.get("aggressive_history", "") or "N/A")

    with col2:
        st.subheader("🛡️ Conservative")
        st.markdown(risk.get("conservative_history", "") or "N/A")

    with col3:
        st.subheader("⚖️ Neutral")
        st.markdown(risk.get("neutral_history", "") or "N/A")

    judge = risk.get("judge_decision", "")
    if judge:
        st.divider()
        st.subheader("📋 Risk Assessment Verdict")
        st.markdown(judge)


def _render_raw_json(state_json: str | None):
    if not state_json:
        st.info("No raw state data available.")
        return

    with st.expander("Full State JSON", expanded=False):
        try:
            parsed = json.loads(state_json)
            st.json(parsed)
        except (json.JSONDecodeError, TypeError):
            st.code(state_json, language="json")
