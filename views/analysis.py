"""Analysis page — run and monitor TradingAgents analyses."""

import time
from datetime import date, timedelta

import streamlit as st
from core.config import load_config
from core.database import get_active_runs, get_run
from core.runner import get_runner, read_progress
from views.icons import icon_header

# Expected steps in order for progress bar
ALL_STEPS = [
    "Market Analyst", "Social Media Analyst", "News Analyst", "Fundamentals Analyst",
    "Bull Researcher", "Bear Researcher", "Research Manager", "Trader",
    "Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Portfolio Manager",
]


def render():
    st.markdown(icon_header("cpu", "Analysis"), unsafe_allow_html=True)

    tab_active, tab_new = st.tabs(["Active Runs", "New Analysis"])

    with tab_active:
        _render_active_runs()

    with tab_new:
        _render_new_analysis()


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

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.subheader(f"{run['ticker']} — {run['trade_date']}")
                st.caption(f"Run #{run_id} | Status: {run['status']}")

            with col2:
                if prog and prog.get("started_at"):
                    elapsed = time.time() - prog["started_at"]
                    mins, secs = divmod(int(elapsed), 60)
                    st.metric("Elapsed", f"{mins}m {secs}s")
                else:
                    st.metric("Status", run["status"].title())

            with col3:
                if still_running:
                    has_running = True
                    if st.button("Cancel", key=f"cancel_{run_id}"):
                        runner.cancel(run_id)
                        st.rerun()

            # Progress bar
            if prog:
                steps_done = prog.get("steps", [])
                step_names_done = {s["name"] for s in steps_done}
                fraction = len(step_names_done) / len(ALL_STEPS) if ALL_STEPS else 0
                current = prog.get("current_step", "Initializing...")
                status = prog.get("status", "running")

                if status == "completed":
                    st.progress(1.0, text=f"Completed — Rating: {prog.get('rating', 'N/A')}")
                elif status == "failed":
                    st.error(f"Failed: {prog.get('error', 'Unknown error')}")
                elif status == "cancelled":
                    st.warning("Cancelled")
                else:
                    st.progress(min(fraction, 0.99), text=f"{current} ({fraction:.0%})")

                # Step timeline
                if steps_done:
                    with st.expander("Step Details"):
                        for step in steps_done:
                            st.text(f"  {step['name']}")
                        if status == "running" and current not in step_names_done:
                            st.text(f"  {current}...")
            elif run["status"] == "pending":
                st.progress(0.0, text="Waiting to start...")

            # Link to results if completed
            if run["status"] == "completed":
                st.success(f"Completed! Rating: {run.get('rating', 'N/A')}")

    # Auto-refresh while running
    if has_running:
        time.sleep(5)
        st.rerun()


def _render_new_analysis():
    cfg = load_config()
    analysis_cfg = cfg.get("analysis", {})
    llm_cfg = cfg.get("llm", {})

    with st.form("new_analysis_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker Symbol", placeholder="e.g. NVDA").strip().upper()
        with col2:
            trade_date = st.date_input(
                "Analysis Date",
                value=date.today() - timedelta(days=1),
                max_value=date.today(),
            )

        st.subheader("Configuration")

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
