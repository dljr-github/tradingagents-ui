"""Analysis page — run and monitor TradingAgents analyses."""

import time
from datetime import date, timedelta

import streamlit as st
from core.config import load_config
from core.database import get_active_runs, get_run
from core.runner import get_runner, read_progress
from views.icons import icon, icon_header, page_header

# Expected steps in order for progress bar
ALL_STEPS = [
    "Market Analyst", "Social Media Analyst", "News Analyst", "Fundamentals Analyst",
    "Bull Researcher", "Bear Researcher", "Research Manager", "Trader",
    "Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Portfolio Manager",
]


def render():
    st.markdown(page_header("cpu", "Analysis", "Run & Monitor Agents"), unsafe_allow_html=True)

    tab_active, tab_new = st.tabs(["Active Runs", "New Analysis"])

    with tab_active:
        _render_active_runs()

    with tab_new:
        _render_new_analysis()


def _build_pipeline_html(steps_done: set, current_step: str, status: str) -> str:
    """Build HTML for the pipeline stepper visualization."""
    html_parts = ['<div style="margin: 12px 0 8px 0;">']
    for i, step_name in enumerate(ALL_STEPS):
        if step_name in steps_done:
            node_cls = "done"
            label_cls = "done"
            node_content = icon("check-circle").replace('width="14"', 'width="10"').replace('height="14"', 'height="10"')
        elif step_name == current_step and status == "running":
            node_cls = "active"
            label_cls = "active"
            node_content = ""
        else:
            node_cls = "pending"
            label_cls = "pending"
            node_content = f'<span style="font-size:0.6rem;">{i + 1}</span>'

        is_last = i == len(ALL_STEPS) - 1
        html_parts.append(
            f'<div class="pipeline-step" {"" if not is_last else "style=padding-bottom:0;"}>'
            f'<div class="pipeline-node {node_cls}">{node_content}</div>'
            f'<span class="pipeline-label {label_cls}">{step_name}</span>'
            f'</div>'
        )
    html_parts.append('</div>')
    return ''.join(html_parts)


def _render_active_runs():
    db_active = get_active_runs()
    runner = get_runner()

    if not db_active:
        st.info("No active analyses. Start one from the 'New Analysis' tab or the Screener page.")
        return

    st.caption("Auto-refreshing every 5 seconds while runs are active...")

    has_running = False

    for run in db_active:
        run_id = run["id"]
        prog = read_progress(run_id)
        still_running = runner.is_running(run_id)

        # Status card
        status_label = run["status"].title()
        elapsed_html = ""
        if prog and prog.get("started_at"):
            elapsed = time.time() - prog["started_at"]
            mins, secs = divmod(int(elapsed), 60)
            elapsed_html = f'<span class="run-elapsed">{mins}m {secs}s</span>'

        st.markdown(f"""
        <div class="run-status-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="run-ticker">{run['ticker']}</div>
                    <div class="run-meta">Run #{run_id} &middot; {run['trade_date']} &middot; {status_label}</div>
                </div>
                <div style="text-align: right;">
                    {elapsed_html}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if still_running:
            has_running = True
            if st.button("Cancel", key=f"cancel_{run_id}"):
                runner.cancel(run_id)
                st.rerun()

        # Progress
        if prog:
            steps_done = prog.get("steps", [])
            step_names_done = {s["name"] for s in steps_done}
            fraction = len(step_names_done) / len(ALL_STEPS) if ALL_STEPS else 0
            current = prog.get("current_step", "Initializing...")
            status = prog.get("status", "running")

            if status == "completed":
                st.progress(1.0, text=f"Completed -- Rating: {prog.get('rating', 'N/A')}")
            elif status == "failed":
                st.error(f"Failed: {prog.get('error', 'Unknown error')}")
            elif status == "cancelled":
                st.warning("Cancelled")
            else:
                st.progress(min(fraction, 0.99), text=f"{current} ({fraction:.0%})")

            # Pipeline stepper
            with st.expander("Pipeline Details", expanded=(status == "running")):
                st.markdown(
                    _build_pipeline_html(step_names_done, current, status),
                    unsafe_allow_html=True,
                )
        elif run["status"] == "pending":
            st.progress(0.0, text="Waiting to start...")

        if run["status"] == "completed":
            rating = run.get("rating", "N/A")
            rating_cls = (rating or "").lower().replace(" ", "")
            st.markdown(
                f'<div style="margin: 8px 0;"><span class="rating-badge rating-{rating_cls}">{rating}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

    if has_running:
        time.sleep(5)
        st.rerun()


def _render_new_analysis():
    cfg = load_config()
    analysis_cfg = cfg.get("analysis", {})
    llm_cfg = cfg.get("llm", {})

    with st.form("new_analysis_form"):
        st.markdown(icon_header("target", "Configure Analysis", level=3), unsafe_allow_html=True)
        st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker Symbol", placeholder="e.g. NVDA").strip().upper()
        with col2:
            trade_date = st.date_input(
                "Analysis Date",
                value=date.today() - timedelta(days=1),
                max_value=date.today(),
            )

        st.markdown("---")
        st.markdown(icon_header("cpu", "Model Settings", level=4), unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            quick_model = st.text_input(
                "Quick Think Model (Analysts/Debaters)",
                value=llm_cfg.get("quick_think_model", "claude-sonnet-4-6"),
            )
            deep_model = st.text_input(
                "Deep Think Model (Research Manager/Portfolio Manager)",
                value=llm_cfg.get("deep_think_model", "claude-opus-4-6"),
            )

        with col_b:
            all_analysts = ["market", "social", "news", "fundamentals"]
            default_analysts = analysis_cfg.get("default_analysts", all_analysts)
            selected_analysts = st.multiselect(
                "Analysts",
                all_analysts,
                default=default_analysts,
            )
            debate_rounds = st.slider(
                "Debate Rounds",
                min_value=1,
                max_value=3,
                value=analysis_cfg.get("max_debate_rounds", 1),
            )
            risk_rounds = st.slider(
                "Risk Discussion Rounds",
                min_value=1,
                max_value=3,
                value=analysis_cfg.get("max_risk_discuss_rounds", 1),
            )

        submitted = st.form_submit_button("Start Analysis", use_container_width=True)

    if submitted:
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return
        if not selected_analysts:
            st.error("Please select at least one analyst.")
            return

        overrides = {
            "llm_provider": "claude_cli",
            "quick_think_llm": quick_model,
            "deep_think_llm": deep_model,
            "max_debate_rounds": debate_rounds,
            "max_risk_discuss_rounds": risk_rounds,
        }

        runner = get_runner()
        run_id = runner.submit(
            ticker=ticker,
            trade_date=trade_date.isoformat(),
            analysts=selected_analysts,
            config_overrides=overrides,
        )
        st.success(f"Analysis #{run_id} started for {ticker} on {trade_date}!")
        st.rerun()
