"""Screener page — stock discovery, watchlist, top movers, sector heatmap."""

import streamlit as st
from core.screener_data import get_quick_stats, get_sector_performance, get_top_movers
from core.database import add_to_watchlist, get_watchlist, is_in_watchlist, remove_from_watchlist
from core.runner import get_runner
from views.icons import icon_header


def _rating_color(change_pct: float) -> str:
    if change_pct > 0:
        return "green"
    elif change_pct < 0:
        return "red"
    return "gray"


def _queue_analysis(ticker: str):
    """Queue a TradingAgents analysis for a ticker."""
    from datetime import date
    runner = get_runner()
    run_id = runner.submit(ticker, date.today().isoformat())
    st.session_state["last_queued_run"] = run_id
    st.session_state["last_queued_ticker"] = ticker


def render():
    st.markdown(icon_header("chart", "Stock Screener"), unsafe_allow_html=True)

    # Quick ticker lookup
    col1, col2, col3 = st.columns([3, 1, 1])
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
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Price", f"${stats['price']}", f"{stats['change_pct']:+.2f}%")
            c2.metric("Volume", f"{stats['volume']:,.0f}")
            c3.metric("RSI (14)", f"{stats['rsi']}" if stats['rsi'] else "N/A")
            c4.metric("SMA 50", f"${stats['sma50']}" if stats['sma50'] else "N/A")
            c5.metric("SMA 200", f"${stats['sma200']}" if stats['sma200'] else "N/A")

            if st.button(f"Analyze {lookup_ticker.upper()}", key="analyze_lookup"):
                _queue_analysis(lookup_ticker.strip().upper())
                st.success(f"Analysis queued for {lookup_ticker.upper()}! Go to Analysis page to monitor.")
        else:
            st.error(f"Could not fetch data for {lookup_ticker}: {stats.get('error')}")

    # Notify if something was just queued
    if st.session_state.get("last_queued_ticker"):
        ticker = st.session_state.pop("last_queued_ticker")

    st.divider()

    # Layout: Top Movers | Sector Heatmap
    tab_movers, tab_sectors, tab_watchlist = st.tabs(["Top Movers", "Sector Performance", "Watchlist"])

    with tab_movers:
        _render_top_movers()

    with tab_sectors:
        _render_sectors()

    with tab_watchlist:
        _render_watchlist()


def _render_top_movers():
    with st.spinner("Loading market data..."):
        movers = get_top_movers(8)

    if not any(movers.values()):
        st.info("No market data available. Markets may be closed.")
        return

    col_gain, col_lose, col_vol = st.columns(3)

    with col_gain:
        st.markdown(icon_header("trending-up", "Top Gainers", level=3), unsafe_allow_html=True)
        for item in movers.get("gainers", []):
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown(f"**{item['ticker']}**")
                c2.markdown(f"${item['price']} ({item['change_pct']:+.2f}%)")
                if c3.button("Analyze", key=f"analyze_g_{item['ticker']}", help=f"Analyze {item['ticker']}"):
                    _queue_analysis(item["ticker"])
                    st.toast(f"Analysis queued for {item['ticker']}")

    with col_lose:
        st.markdown(icon_header("trending-down", "Top Losers", level=3), unsafe_allow_html=True)
        for item in movers.get("losers", []):
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown(f"**{item['ticker']}**")
                c2.markdown(f"${item['price']} ({item['change_pct']:+.2f}%)")
                if c3.button("Analyze", key=f"analyze_l_{item['ticker']}", help=f"Analyze {item['ticker']}"):
                    _queue_analysis(item["ticker"])
                    st.toast(f"Analysis queued for {item['ticker']}")

    with col_vol:
        st.markdown(icon_header("bar-chart", "Volume Spikes", level=3), unsafe_allow_html=True)
        for item in movers.get("volume", []):
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown(f"**{item['ticker']}**")
                c2.markdown(f"{item['vol_ratio']:.1f}x avg vol")
                if c3.button("Analyze", key=f"analyze_v_{item['ticker']}", help=f"Analyze {item['ticker']}"):
                    _queue_analysis(item["ticker"])
                    st.toast(f"Analysis queued for {item['ticker']}")


def _render_sectors():
    with st.spinner("Loading sector data..."):
        sectors = get_sector_performance()

    if not sectors:
        st.info("No sector data available.")
        return

    # Simple heatmap using columns
    cols = st.columns(4)
    for i, s in enumerate(sectors):
        col = cols[i % 4]
        change = s["change_pct"]
        if change > 0:
            color = "#00d26a"
        elif change < 0:
            color = "#ff4444"
        else:
            color = "#888"
        col.markdown(
            f"""<div style="background: rgba(28,34,48,0.8); border-left: 4px solid {color};
            padding: 12px; margin: 4px 0; border-radius: 4px;">
            <b>{s['sector']}</b><br>
            <span style="color: {color}; font-size: 1.2em;">{change:+.2f}%</span><br>
            <small>{s['etf']}</small></div>""",
            unsafe_allow_html=True,
        )


def _render_watchlist():
    wl = get_watchlist()
    if not wl:
        st.info("Your watchlist is empty. Add tickers using the search above.")
        return

    for item in wl:
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
            c1.markdown(f"**{item['ticker']}**")
            c2.caption(item.get("notes") or "")
            if c3.button("Analyze", key=f"analyze_wl_{item['ticker']}", help=f"Analyze {item['ticker']}"):
                _queue_analysis(item["ticker"])
                st.toast(f"Analysis queued for {item['ticker']}")
            if c4.button("Remove", key=f"remove_wl_{item['ticker']}", help="Remove from watchlist"):
                remove_from_watchlist(item["ticker"])
                st.rerun()
