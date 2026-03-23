"""Screener page — stock discovery, watchlist, top movers, sector heatmap."""

import io
import csv

import streamlit as st

from core.screener_data import (
    get_quick_stats,
    get_sector_performance,
    get_top_movers,
    get_sector_stocks,
    get_ticker_info_cached,
)
from core.database import add_to_watchlist, get_watchlist, get_runs, is_in_watchlist, remove_from_watchlist
from core.runner import get_runner
from core.theme import get_plotly_theme, get_muted_color
from views.icons import page_header
from views.screener_charts import make_candlestick_chart, make_sparkline
from views.screener_technical import make_technical_indicators_panel


def _queue_analysis(ticker: str):
    """Queue a TradingAgents analysis for a ticker."""
    from datetime import date
    runner = get_runner()
    run_id = runner.submit(ticker, date.today().isoformat())
    st.session_state["last_queued_run"] = run_id
    st.session_state["last_queued_ticker"] = ticker


def _render_analysis_history(ticker: str):
    """Show past analysis results for a ticker below the chart."""
    past_runs = get_runs(ticker=ticker, status="completed", limit=10)
    if not past_runs:
        return

    rating_colors = {
        "BUY": "#00d26a", "OVERWEIGHT": "#7dd87d", "HOLD": "#ffd700",
        "UNDERWEIGHT": "#ff8c42", "SELL": "#ff4757",
    }

    with st.expander(f"Analysis History ({len(past_runs)} past runs)", expanded=False):
        for r in past_runs:
            rating = (r.get("rating") or "N/A").upper()
            color = rating_colors.get(rating, get_muted_color())
            decision = r.get("final_decision", "") or ""
            brief = decision[:120].replace("\n", " ") + ("..." if len(decision) > 120 else "")
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-subtle);">'
                f'<div>'
                f'<span style="color:var(--text-muted); font-size:0.8rem;">{r["trade_date"]}</span>'
                f'<span style="color:{color}; font-weight:700; font-family:var(--font-mono); margin-left:10px; font-size:0.85rem;">{rating}</span>'
                f'<div style="color:var(--text-secondary); font-size:0.78rem; margin-top:2px;">{brief}</div>'
                f'</div>'
                f'<span style="color:var(--text-muted); font-family:var(--font-mono); font-size:0.75rem;">#{r["id"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if st.button("View in Results Page", key="goto_results_from_history"):
            st.session_state["view_run_id"] = past_runs[0]["id"]
            st.info("Navigate to the Results page to see full details.")


def _get_earnings_days(ticker: str) -> int | None:
    """Return days until next earnings if within 14 days, else None."""
    import yfinance as yf
    from datetime import date, timedelta
    try:
        tk = yf.Ticker(ticker)
        cal = tk.calendar
        if cal is None or cal.empty:
            return None
        earnings_date = None
        if hasattr(cal, "loc"):
            if "Earnings Date" in cal.index:
                val = cal.loc["Earnings Date"]
                if hasattr(val, "iloc"):
                    earnings_date = val.iloc[0]
                else:
                    earnings_date = val
            elif "Earnings Date" in cal.columns:
                earnings_date = cal["Earnings Date"].iloc[0]
        if earnings_date is None:
            return None
        if hasattr(earnings_date, "date"):
            earnings_date = earnings_date.date()
        elif isinstance(earnings_date, str):
            from datetime import datetime
            earnings_date = datetime.strptime(earnings_date, "%Y-%m-%d").date()
        today = date.today()
        delta = (earnings_date - today).days
        if 0 <= delta <= 14:
            return delta
    except Exception:
        pass
    return None


def render():
    st.markdown(page_header("chart", "Stock Screener", "Market Discovery & Watchlist"), unsafe_allow_html=True)

    # Quick ticker lookup — wider input, buttons stay on one line
    col1, col2, col3 = st.columns([5, 2, 2])
    with col1:
        lookup_ticker = st.text_input("Look up ticker", placeholder="e.g. AAPL", key="screener_lookup")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        lookup_btn = st.button("Get Stats", use_container_width=True)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if lookup_ticker:
            in_wl = is_in_watchlist(lookup_ticker.upper())
            if in_wl:
                if st.button("Remove from Watchlist", use_container_width=True):
                    remove_from_watchlist(lookup_ticker.upper())
                    st.rerun()
            else:
                if st.button("Add to Watchlist", use_container_width=True):
                    add_to_watchlist(lookup_ticker.upper())
                    st.rerun()

    if lookup_btn and lookup_ticker:
        stats = get_quick_stats(lookup_ticker.strip().upper())
        if "error" not in stats:
            name = stats.get("name", stats["ticker"])
            sector = stats.get("sector", "")
            industry = stats.get("industry", "")
            change = stats["change_pct"]
            delta_class = "positive" if change > 0 else "negative" if change < 0 else ""
            delta_sign = "+" if change > 0 else ""

            # Company info header
            st.markdown(f"""
            <div class="ta-card" style="margin-top: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="card-ticker" style="font-size: 1.2rem;">{name}</span>
                        <span style="color: var(--text-muted); margin-left: 8px;">({stats['ticker']})</span>
                        {'<div class="card-sector" style="margin-top: 4px;">' + sector + (' &middot; ' + industry if industry else '') + '</div>' if sector or industry else ''}
                    </div>
                    <div style="text-align: right;">
                        <div class="card-value" style="font-size: 1.3rem;">${stats['price']:.2f}</div>
                        <div class="stat-delta {delta_class}">{delta_sign}{change:.2f}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Stats grid
            rsi_val = f"{stats['rsi']}" if stats['rsi'] else "N/A"
            sma50_val = f"${stats['sma50']}" if stats['sma50'] else "N/A"
            sma200_val = f"${stats['sma200']}" if stats['sma200'] else "N/A"

            st.markdown(f"""
            <div class="stat-grid" style="margin: 12px 0;">
                <div class="stat-item">
                    <div class="stat-label">Volume</div>
                    <div class="stat-value">{stats['volume']:,.0f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">RSI (14)</div>
                    <div class="stat-value">{rsi_val}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">SMA 50</div>
                    <div class="stat-value">{sma50_val}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">SMA 200</div>
                    <div class="stat-value">{sma200_val}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Analyze {lookup_ticker.upper()}", key="analyze_lookup"):
                _queue_analysis(lookup_ticker.strip().upper())
                st.success(f"Analysis queued for {lookup_ticker.upper()}! Go to Analysis page to monitor.")

            # Candlestick price chart
            make_candlestick_chart(lookup_ticker.strip().upper())

            # Technical indicators panel
            make_technical_indicators_panel(lookup_ticker.strip().upper(), stats)

            # Analysis history for this ticker
            _render_analysis_history(lookup_ticker.strip().upper())

        else:
            st.error(f"Could not fetch data for {lookup_ticker}: {stats.get('error')}")

    # Clear queued notification
    if st.session_state.get("last_queued_ticker"):
        st.session_state.pop("last_queued_ticker")

    st.divider()

    tab_movers, tab_sectors, tab_watchlist = st.tabs(["Top Movers", "Sector Performance", "Watchlist"])

    with tab_movers:
        _render_top_movers()

    with tab_sectors:
        _render_sectors()

    with tab_watchlist:
        _render_watchlist()


def _render_mover_tab(items: list, accent: str, value_fn, key_prefix: str):
    """Render a single mover tab with full-width rows, Analyze and Watch buttons."""
    if not items:
        st.caption("No data available.")
        return

    value_cls = "positive" if accent == "green" else "negative" if accent == "red" else "neutral"
    hdr1, hdr2, hdr3, hdr4, hdr5 = st.columns([1, 5, 2, 1, 1])
    hdr1.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Ticker</span>', unsafe_allow_html=True)
    hdr2.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Company</span>', unsafe_allow_html=True)
    hdr3.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Price / Change</span>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:4px 0; border-color:var(--border-medium);">', unsafe_allow_html=True)

    for i, item in enumerate(items):
        name = item.get("name", "")
        sector = item.get("sector", "")
        ticker = item["ticker"]

        c_tick, c_name, c_price, c_btn1, c_btn2 = st.columns([1, 5, 2, 1, 1])
        with c_tick:
            st.markdown(f'<span style="font-family:var(--font-mono); font-weight:700; font-size:0.95rem; color:var(--text-primary);">{ticker}</span>', unsafe_allow_html=True)
        with c_name:
            company_line = name or "—"
            sector_line = f'<span style="color:var(--text-muted); font-size:0.75rem; text-transform:uppercase;"> · {sector}</span>' if sector else ""
            st.markdown(f'<span style="color:var(--text-secondary); font-size:0.85rem;">{company_line}{sector_line}</span>', unsafe_allow_html=True)
        with c_price:
            st.markdown(f'<span class="{value_cls}" style="font-family:var(--font-mono); font-weight:600; font-size:0.9rem;">{value_fn(item)}</span>', unsafe_allow_html=True)
        with c_btn1:
            if st.button("🔍", key=f"a_{key_prefix}_{ticker}", help=f"Analyze {ticker}", use_container_width=True):
                _queue_analysis(ticker)
                st.toast(f"Analysis queued for {ticker}")
        with c_btn2:
            if is_in_watchlist(ticker):
                st.button("★", key=f"w_{key_prefix}_{ticker}", disabled=True, help="Already watching", use_container_width=True)
            else:
                if st.button("☆", key=f"w_{key_prefix}_{ticker}", help=f"Add {ticker} to watchlist", use_container_width=True):
                    add_to_watchlist(ticker)
                    st.toast(f"{ticker} added to watchlist")
                    st.rerun()


def _render_top_movers():
    with st.spinner("Loading market data..."):
        movers = get_top_movers(8)

    if not any(movers.values()):
        st.info("No market data available. Markets may be closed.")
        return

    # Export CSV button for all movers data
    all_movers = movers.get("gainers", []) + movers.get("losers", []) + movers.get("volume", [])
    if all_movers:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["ticker", "name", "sector", "price", "change_pct", "volume", "vol_ratio"])
        writer.writeheader()
        seen = set()
        for m in all_movers:
            if m["ticker"] not in seen:
                writer.writerow(m)
                seen.add(m["ticker"])
        st.download_button("Export CSV", buf.getvalue(), file_name="top_movers.csv", mime="text/csv", key="export_movers_csv")

    tab_gain, tab_lose, tab_vol = st.tabs([
        "Top Gainers",
        "Top Losers",
        "Volume Spikes",
    ])

    with tab_gain:
        _render_mover_tab(
            movers.get("gainers", []), "green",
            lambda x: f"${x['price']:.2f}  <span class='mover-tbl-change positive'>{x['change_pct']:+.2f}%</span>",
            "g",
        )

    with tab_lose:
        _render_mover_tab(
            movers.get("losers", []), "red",
            lambda x: f"${x['price']:.2f}  <span class='mover-tbl-change negative'>{x['change_pct']:+.2f}%</span>",
            "l",
        )

    with tab_vol:
        _render_mover_tab(
            movers.get("volume", []), "cyan",
            lambda x: f"{x['vol_ratio']:.1f}x avg vol",
            "v",
        )


def _render_sectors():
    with st.spinner("Loading sector data..."):
        sectors = get_sector_performance()

    if not sectors:
        st.info("No sector data available.")
        return

    import plotly.graph_objects as go

    sector_names = [s["sector"] for s in sectors]
    changes = [s["change_pct"] for s in sectors]
    bar_colors = ["#00d26a" if c >= 0 else "#ff4757" for c in changes]

    theme = get_plotly_theme()
    fig = go.Figure(go.Bar(
        x=sector_names, y=changes,
        marker_color=bar_colors,
        text=[f"{c:+.2f}%" for c in changes],
        textposition="outside",
        textfont=dict(color=get_muted_color(), size=11),
    ))
    fig.update_layout(
        plot_bgcolor=theme["plot_bgcolor"], paper_bgcolor=theme["paper_bgcolor"],
        font=theme["font"],
        margin=dict(l=0, r=0, t=20, b=0),
        height=280,
        xaxis=dict(tickangle=-45, gridcolor=theme["gridcolor"]),
        yaxis=dict(
            gridcolor=theme["gridcolor"],
            zeroline=True, zerolinecolor=theme["zerolinecolor"],
            title="Change %",
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Sector cards with expandable drill-down
    cols = st.columns(4)
    for i, s in enumerate(sectors):
        col = cols[i % 4]
        change = s["change_pct"]
        if change > 2:
            color = "#00d26a"
            bg_gradient = "linear-gradient(135deg, rgba(0, 210, 106, 0.12) 0%, rgba(0, 210, 106, 0.04) 100%)"
        elif change > 0:
            color = "#7dd87d"
            bg_gradient = "linear-gradient(135deg, rgba(125, 216, 125, 0.08) 0%, rgba(125, 216, 125, 0.02) 100%)"
        elif change > -2:
            color = "#ff8c42"
            bg_gradient = "linear-gradient(135deg, rgba(255, 140, 66, 0.08) 0%, rgba(255, 140, 66, 0.02) 100%)"
        else:
            color = "#ff4757"
            bg_gradient = "linear-gradient(135deg, rgba(255, 71, 87, 0.12) 0%, rgba(255, 71, 87, 0.04) 100%)"

        with col:
            st.markdown(
                f"""<div class="sector-card" style="background: {bg_gradient}; border-color: {color}30;">
                    <div class="sector-name">{s['sector']}</div>
                    <div class="sector-change" style="color: {color};">{change:+.2f}%</div>
                    <div class="sector-etf">{s['etf']}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            with st.expander(f"Top stocks in {s['sector']}"):
                stocks = get_sector_stocks(s["etf"], n=5)
                if stocks:
                    for stock in stocks:
                        chg = stock["change_pct"]
                        chg_cls = "positive" if chg > 0 else "negative" if chg < 0 else ""
                        st.markdown(
                            f'<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid var(--border-subtle);">'
                            f'<span style="font-family:var(--font-mono); font-weight:600;">{stock["ticker"]}</span>'
                            f'<span style="font-family:var(--font-mono); font-size:0.85rem;" class="stat-delta {chg_cls}">{chg:+.2f}%</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    top_ticker = stocks[0]["ticker"]
                    if st.button(f"Analyze {top_ticker}", key=f"analyze_sector_{s['etf']}", use_container_width=True):
                        _queue_analysis(top_ticker)
                        st.toast(f"Analysis queued for {top_ticker}")
                else:
                    st.caption("No matching stocks in scan universe.")


def _render_watchlist():
    wl = get_watchlist()
    if not wl:
        st.info("Your watchlist is empty. Add tickers using the search above.")
        return

    for item in wl:
        info = get_ticker_info_cached(item["ticker"])
        name = info.get("name", "")
        sector = info.get("sector", "")
        industry = info.get("industry", "")

        # Get price data
        stats = get_quick_stats(item["ticker"])
        has_price = "error" not in stats

        with st.container(border=True):
            # Row 1: ticker info + price + sparkline
            col_ticker, col_company, col_price, col_spark = st.columns([1, 4, 2, 2])
            with col_ticker:
                st.markdown(f'<span style="font-family:var(--font-mono); font-weight:700; font-size:1rem; color:var(--text-primary);">{item["ticker"]}</span>', unsafe_allow_html=True)
            with col_company:
                sector_short = sector if sector else ""
                st.markdown(f'<div style="overflow:hidden; white-space:nowrap; text-overflow:ellipsis;"><span style="color:var(--text-secondary); font-size:0.85rem;">{name}</span>{" <span style=&quot;color:var(--text-muted); font-size:0.7rem; text-transform:uppercase;&quot;>· " + sector_short + "</span>" if sector_short else ""}</div>', unsafe_allow_html=True)
            with col_price:
                if has_price:
                    change = stats["change_pct"]
                    chg_color = "var(--green)" if change > 0 else "var(--red)" if change < 0 else "var(--text-secondary)"
                    earnings_days = _get_earnings_days(item["ticker"])
                    earnings_badge = ""
                    if earnings_days is not None:
                        earnings_badge = f'<div style="color:#ffd700; font-size:0.72rem; font-weight:600; margin-top:2px;">Earnings in {earnings_days} day{"s" if earnings_days != 1 else ""}</div>'
                    st.markdown(f'<div style="text-align:right; font-family:var(--font-mono);"><div style="font-weight:600; font-size:1rem;">${stats["price"]:.2f}</div><div style="color:{chg_color}; font-size:0.85rem;">{change:+.2f}%</div>{earnings_badge}</div>', unsafe_allow_html=True)
            with col_spark:
                make_sparkline(item["ticker"])

            # Row 2: action buttons
            c1, c2 = st.columns([1, 1])
            if c1.button("Analyze", key=f"analyze_wl_{item['ticker']}", help=f"Analyze {item['ticker']}", use_container_width=True):
                _queue_analysis(item["ticker"])
                st.toast(f"Analysis queued for {item['ticker']}")
            if c2.button("Remove", key=f"remove_wl_{item['ticker']}", help="Remove from watchlist", use_container_width=True):
                remove_from_watchlist(item["ticker"])
                st.rerun()
