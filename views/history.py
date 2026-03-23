"""History page — browse, filter, compare past analysis runs."""

import csv
import io
import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from core.database import get_run, get_runs
from core.screener_data import get_ticker_price
from views.icons import icon, icon_header, page_header


RATING_COLORS = {
    "BUY": "#00d26a",
    "OVERWEIGHT": "#7dd87d",
    "HOLD": "#ffd700",
    "UNDERWEIGHT": "#ff8c42",
    "SELL": "#ff4757",
}


def render():
    st.markdown(page_header("clock", "History", "Past Analyses & Accuracy"), unsafe_allow_html=True)

    # Compact inline filters
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_ticker = st.text_input("Ticker", key="hist_ticker").strip().upper()
    with col2:
        filter_rating = st.selectbox("Rating", ["All", "BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL"])
    with col3:
        filter_from = st.date_input("From Date", value=date.today() - timedelta(days=90), key="hist_from")
    with col4:
        filter_to = st.date_input("To Date", value=date.today(), key="hist_to")
    st.markdown('</div>', unsafe_allow_html=True)

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

    tab_table, tab_accuracy, tab_compare = st.tabs(["Runs", "Accuracy Tracker", "Compare"])

    with tab_table:
        _render_runs_table(df, runs)

    with tab_accuracy:
        _render_accuracy(runs)

    with tab_compare:
        _render_compare(runs)


def _render_runs_table(df: pd.DataFrame, runs: list[dict]):
    # Export CSV for runs table
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button("Export CSV", buf.getvalue(), file_name="analysis_history.csv", mime="text/csv", key="export_history_csv")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("Run #", width="small"),
            "Rating": st.column_config.TextColumn("Rating"),
        },
    )

    run_ids = [r["id"] for r in runs]
    selected_id = st.selectbox(
        "View Run Details",
        run_ids,
        format_func=lambda x: f"#{x} -- {next(r['ticker'] for r in runs if r['id'] == x)}",
    )

    col_view, col_export = st.columns(2)
    with col_view:
        if st.button("View Results"):
            st.session_state["view_run_id"] = selected_id
            st.info(f"Navigate to the Results page to see details for Run #{selected_id}.")
    with col_export:
        run_detail = get_run(selected_id)
        if run_detail:
            report_lines = [
                f"Analysis Report — {run_detail['ticker']} ({run_detail['trade_date']})",
                f"Rating: {run_detail.get('rating', 'N/A')}",
                f"Status: {run_detail['status']}",
                "=" * 60,
                "\n--- Market Report ---",
                run_detail.get("market_report", "N/A") or "N/A",
                "\n--- Sentiment Report ---",
                run_detail.get("sentiment_report", "N/A") or "N/A",
                "\n--- News Report ---",
                run_detail.get("news_report", "N/A") or "N/A",
                "\n--- Fundamentals Report ---",
                run_detail.get("fundamentals_report", "N/A") or "N/A",
                "\n--- Final Decision ---",
                run_detail.get("final_decision", "N/A") or "N/A",
            ]
            report_text = "\n".join(report_lines)
            st.download_button(
                "Export Report",
                report_text,
                file_name=f"report_{run_detail['ticker']}_{run_detail['trade_date']}.txt",
                mime="text/plain",
                key="export_run_report",
            )


def _render_accuracy(runs: list[dict]):
    st.markdown(icon_header("target", "Decision Accuracy", level=3), unsafe_allow_html=True)
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

        analysis_price = None
        try:
            json.loads(r.get("full_state_json") or "{}")
        except Exception:
            pass

        if analysis_price is None:
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

        bullish_ratings = {"BUY", "OVERWEIGHT"}
        bearish_ratings = {"SELL", "UNDERWEIGHT"}
        if rating in bullish_ratings:
            correct = price_change_pct > 0
        elif rating in bearish_ratings:
            correct = price_change_pct < 0
        else:
            correct = abs(price_change_pct) < 5

        accuracy_rows.append({
            "Ticker": ticker,
            "Date": trade_date,
            "Rating": rating,
            "Price Then": f"${analysis_price}",
            "Price Now": f"${current_price}",
            "Change": f"{price_change_pct:+.2f}%",
            "Correct": "Yes" if correct else "No",
        })

    if accuracy_rows:
        df = pd.DataFrame(accuracy_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        correct_count = sum(1 for r in accuracy_rows if r["Correct"] == "Yes")
        total = len(accuracy_rows)
        pct = correct_count / total * 100 if total else 0

        # Custom accuracy display
        acc_color = "#00d26a" if pct >= 60 else "#ffd700" if pct >= 40 else "#ff4757"
        st.markdown(f"""
        <div class="ta-card" style="display: inline-flex; align-items: center; gap: 16px; margin-top: 8px;">
            <div>
                <div class="stat-label">Accuracy</div>
                <div class="stat-value" style="color: {acc_color}; font-size: 1.4rem;">
                    {correct_count}/{total} ({pct:.0f}%)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Could not fetch price data for accuracy comparison.")


def _render_compare(runs: list[dict]):
    st.markdown(icon_header("eye", "Compare Analyses", level=3), unsafe_allow_html=True)

    completed = [r for r in runs if r["status"] == "completed"]
    if len(completed) < 2:
        st.info("Need at least 2 completed runs to compare.")
        return

    options = {f"#{r['id']} -- {r['ticker']} ({r['trade_date']})": r["id"] for r in completed}

    selected = st.multiselect("Select runs to compare", list(options.keys()), max_selections=4)

    if len(selected) < 2:
        st.caption("Select at least 2 runs.")
        return

    selected_ids = [options[s] for s in selected]
    selected_runs = [get_run(rid) for rid in selected_ids]
    selected_runs = [r for r in selected_runs if r]

    cols = st.columns(len(selected_runs))
    for i, run in enumerate(selected_runs):
        with cols[i]:
            rating = (run.get("rating") or "N/A").upper()
            rating_cls = rating.lower().replace(" ", "")

            st.markdown(f"""
            <div class="ta-card" style="text-align: center; padding: 20px;">
                <div style="font-family: var(--font-mono); font-weight: 700; font-size: 1.3rem; color: var(--text-primary);">
                    {run['ticker']}
                </div>
                <div style="color: var(--text-muted); font-size: 0.8rem; margin: 4px 0 12px 0;">
                    Run #{run['id']} &middot; {run['trade_date']}
                </div>
                <div class="rating-badge rating-{rating_cls}" style="margin-bottom: 12px;">
                    {rating}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Final Decision:**")
            decision = run.get("final_decision", "N/A")
            st.markdown(decision[:1000] if decision else "N/A")
