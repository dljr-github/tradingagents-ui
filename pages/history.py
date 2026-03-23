"""History page — browse, filter, compare past analysis runs."""

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from core.database import get_run, get_runs
from core.screener_data import get_ticker_price


RATING_COLORS = {
    "BUY": "#00d26a",
    "OVERWEIGHT": "#7dd87d",
    "HOLD": "#ffd700",
    "UNDERWEIGHT": "#ff8c42",
    "SELL": "#ff4444",
}


def render():
    st.header("📈 History")

    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_ticker = st.text_input("Ticker", key="hist_ticker").strip().upper()
        with col2:
            filter_rating = st.selectbox("Rating", ["All", "BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL"])
        with col3:
            filter_from = st.date_input("From Date", value=date.today() - timedelta(days=90), key="hist_from")
        with col4:
            filter_to = st.date_input("To Date", value=date.today(), key="hist_to")

    runs = get_runs(
        ticker=filter_ticker or None,
        rating=filter_rating if filter_rating != "All" else None,
        date_from=filter_from.isoformat() if filter_from else None,
        date_to=filter_to.isoformat() if filter_to else None,
        limit=200,
    )

    if not runs:
        st.info("No runs match your filters.")
        return

    # Build table
    rows = []
    for r in runs:
        rows.append({
            "ID": r["id"],
            "Ticker": r["ticker"],
            "Date": r["trade_date"],
            "Rating": r.get("rating") or "N/A",
            "Status": r["status"],
            "Created": r.get("created_at", "")[:19],
        })

    df = pd.DataFrame(rows)

    # Color-coded display
    tab_table, tab_accuracy, tab_compare = st.tabs(["Runs", "Accuracy Tracker", "Compare"])

    with tab_table:
        _render_runs_table(df, runs)

    with tab_accuracy:
        _render_accuracy(runs)

    with tab_compare:
        _render_compare(runs)


def _render_runs_table(df: pd.DataFrame, runs: list[dict]):
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("Run #", width="small"),
            "Rating": st.column_config.TextColumn("Rating"),
        },
    )

    # Click to view
    run_ids = [r["id"] for r in runs]
    selected_id = st.selectbox("View Run Details", run_ids, format_func=lambda x: f"#{x} — {next(r['ticker'] for r in runs if r['id'] == x)}")

    if st.button("View Results"):
        st.session_state["view_run_id"] = selected_id
        st.info(f"Navigate to the Results page to see details for Run #{selected_id}.")


def _render_accuracy(runs: list[dict]):
    st.subheader("Decision Accuracy Tracking")
    st.caption("Compares analysis ratings against actual price movements since the analysis date.")

    completed = [r for r in runs if r["status"] == "completed" and r.get("rating")]
    if not completed:
        st.info("No completed runs to track.")
        return

    accuracy_rows = []
    for r in completed:
        ticker = r["ticker"]
        rating = (r.get("rating") or "").upper()
        trade_date = r["trade_date"]

        current_price = get_ticker_price(ticker)
        if current_price is None:
            continue

        # Try to get the price on the analysis date from the full state
        analysis_price = None
        try:
            state = json.loads(r.get("full_state_json") or "{}")
            # Look for price in market report — fallback to current
        except Exception:
            pass

        if analysis_price is None:
            # Fetch historical price
            import yfinance as yf
            try:
                hist = yf.Ticker(ticker).history(start=trade_date, period="5d")
                if not hist.empty:
                    analysis_price = round(float(hist["Close"].iloc[0]), 2)
            except Exception:
                continue

        if analysis_price is None or analysis_price == 0:
            continue

        price_change_pct = ((current_price - analysis_price) / analysis_price) * 100

        # Determine if rating was correct
        bullish_ratings = {"BUY", "OVERWEIGHT"}
        bearish_ratings = {"SELL", "UNDERWEIGHT"}
        if rating in bullish_ratings:
            correct = price_change_pct > 0
        elif rating in bearish_ratings:
            correct = price_change_pct < 0
        else:
            correct = abs(price_change_pct) < 5  # HOLD is "correct" if price stayed relatively flat

        accuracy_rows.append({
            "Ticker": ticker,
            "Date": trade_date,
            "Rating": rating,
            "Price Then": f"${analysis_price}",
            "Price Now": f"${current_price}",
            "Change": f"{price_change_pct:+.2f}%",
            "Correct": "✅" if correct else "❌",
        })

    if accuracy_rows:
        df = pd.DataFrame(accuracy_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        correct_count = sum(1 for r in accuracy_rows if r["Correct"] == "✅")
        total = len(accuracy_rows)
        st.metric("Accuracy", f"{correct_count}/{total} ({correct_count/total*100:.0f}%)")
    else:
        st.info("Could not fetch price data for accuracy comparison.")


def _render_compare(runs: list[dict]):
    st.subheader("Compare Analyses")

    completed = [r for r in runs if r["status"] == "completed"]
    if len(completed) < 2:
        st.info("Need at least 2 completed runs to compare.")
        return

    options = {f"#{r['id']} — {r['ticker']} ({r['trade_date']})": r["id"] for r in completed}

    selected = st.multiselect("Select runs to compare", list(options.keys()), max_selections=4)

    if len(selected) < 2:
        st.caption("Select at least 2 runs.")
        return

    selected_ids = [options[s] for s in selected]
    selected_runs = [get_run(rid) for rid in selected_ids]
    selected_runs = [r for r in selected_runs if r]

    # Side by side comparison
    cols = st.columns(len(selected_runs))
    for i, run in enumerate(selected_runs):
        with cols[i]:
            rating = (run.get("rating") or "N/A").upper()
            color = RATING_COLORS.get(rating, "#888")
            st.markdown(f"### {run['ticker']}")
            st.caption(f"Run #{run['id']} | {run['trade_date']}")
            st.markdown(f"<h3 style='color: {color};'>{rating}</h3>", unsafe_allow_html=True)
            st.divider()

            st.markdown("**Final Decision:**")
            decision = run.get("final_decision", "N/A")
            st.markdown(decision[:1000] if decision else "N/A")
