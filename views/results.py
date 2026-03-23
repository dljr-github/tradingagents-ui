"""Results page — view detailed analysis results."""

import json

import streamlit as st
from core.database import get_run, get_runs
from views.icons import icon, icon_header, page_header


RATING_COLORS = {
    "BUY": "#00d26a",
    "OVERWEIGHT": "#7dd87d",
    "HOLD": "#ffd700",
    "UNDERWEIGHT": "#ff8c42",
    "SELL": "#ff4757",
}


def render():
    st.markdown(page_header("clipboard", "Analysis Results", "Detailed Reports & Decisions"), unsafe_allow_html=True)

    # Run selector
    run_id = st.session_state.get("view_run_id")

    completed_runs = get_runs(status="completed", limit=50)
    if not completed_runs and not run_id:
        st.info("No completed analyses yet. Start one from the Analysis page.")
        return

    run_options = {f"#{r['id']} -- {r['ticker']} ({r['trade_date']}) -> {r.get('rating', '?')}": r["id"] for r in completed_runs}

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
    rating = (run.get("rating") or "N/A").upper()
    color = RATING_COLORS.get(rating, "#888")
    rating_cls = rating.lower().replace(" ", "")

    # Header with prominent rating badge
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0; margin-bottom: 8px;">
        <div>
            <div style="font-family: var(--font-mono); font-weight: 700; font-size: 1.6rem; color: var(--text-primary);">
                {run['ticker']}
            </div>
            <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">
                {run['trade_date']} &middot; Completed {run.get('completed_at', 'N/A')[:19] if run.get('completed_at') else 'N/A'}
            </div>
        </div>
        <div class="rating-badge rating-badge-lg rating-{rating_cls}">{rating}</div>
    </div>
    """, unsafe_allow_html=True)

    # Export Report button
    report_lines = [
        f"Analysis Report — {run['ticker']} ({run['trade_date']})",
        f"Rating: {rating}",
        "=" * 60,
        "\n--- Market Report ---",
        run.get("market_report", "N/A") or "N/A",
        "\n--- Sentiment Report ---",
        run.get("sentiment_report", "N/A") or "N/A",
        "\n--- News Report ---",
        run.get("news_report", "N/A") or "N/A",
        "\n--- Fundamentals Report ---",
        run.get("fundamentals_report", "N/A") or "N/A",
        "\n--- Final Decision ---",
        run.get("final_decision", "N/A") or "N/A",
    ]
    st.download_button(
        "Export Report",
        "\n".join(report_lines),
        file_name=f"report_{run['ticker']}_{run['trade_date']}.txt",
        mime="text/plain",
        key="export_result_report",
    )

    st.divider()

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
    st.markdown(f'<div class="report-content">{""}</div>', unsafe_allow_html=True)
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
        bull_svg = icon("trending-up", color="#00d26a")
        st.markdown(f"""
        <div class="debate-panel debate-bull">
            <div class="debate-panel-title">{bull_svg} Bull Case</div>
        </div>
        """, unsafe_allow_html=True)
        bull = debate.get("bull_history", "")
        if bull:
            st.markdown(bull)
        else:
            st.info("No bull arguments recorded.")

    with col_bear:
        bear_svg = icon("trending-down", color="#ff4757")
        st.markdown(f"""
        <div class="debate-panel debate-bear">
            <div class="debate-panel-title">{bear_svg} Bear Case</div>
        </div>
        """, unsafe_allow_html=True)
        bear = debate.get("bear_history", "")
        if bear:
            st.markdown(bear)
        else:
            st.info("No bear arguments recorded.")

    judge = debate.get("judge_decision", "")
    if judge:
        scale_svg = icon("scale", color="#00b4d8")
        st.markdown(f"""
        <div class="verdict-card">
            <div class="verdict-title">{scale_svg} Research Manager Verdict</div>
        </div>
        """, unsafe_allow_html=True)
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
        flame_svg = icon("flame", color="#ff8c42")
        st.markdown(f"""
        <div class="ta-card ta-card-accent-gold">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--orange); font-weight: 600;">
                {flame_svg} Aggressive
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(risk.get("aggressive_history", "") or "N/A")

    with col2:
        shield_svg = icon("shield", color="#00b4d8")
        st.markdown(f"""
        <div class="ta-card ta-card-accent-cyan">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--cyan); font-weight: 600;">
                {shield_svg} Conservative
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(risk.get("conservative_history", "") or "N/A")

    with col3:
        scale_svg = icon("scale", color="#ffd700")
        st.markdown(f"""
        <div class="ta-card" style="border-left: 3px solid var(--gold);">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--gold); font-weight: 600;">
                {scale_svg} Neutral
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(risk.get("neutral_history", "") or "N/A")

    judge = risk.get("judge_decision", "")
    if judge:
        clip_svg = icon("clipboard", color="#00b4d8")
        st.markdown(f"""
        <div class="verdict-card">
            <div class="verdict-title">{clip_svg} Risk Assessment Verdict</div>
        </div>
        """, unsafe_allow_html=True)
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
