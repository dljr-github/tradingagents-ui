"""Screener page — stock discovery, watchlist, top movers, sector heatmap."""

import streamlit as st
from core.screener_data import get_quick_stats, get_sector_performance, get_top_movers
from core.database import add_to_watchlist, get_watchlist, is_in_watchlist, remove_from_watchlist
from core.runner import get_runner
from views.icons import page_header


def _queue_analysis(ticker: str):
    """Queue a TradingAgents analysis for a ticker."""
    from datetime import date
    runner = get_runner()
    run_id = runner.submit(ticker, date.today().isoformat())
    st.session_state["last_queued_run"] = run_id
    st.session_state["last_queued_ticker"] = ticker


def render():
    st.markdown(page_header("chart", "Stock Screener", "Market Discovery & Watchlist"), unsafe_allow_html=True)

    # Quick ticker lookup — wider input, buttons stay on one line
    col1, col2, col3 = st.columns([5, 1, 2])
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
                        <div class="card-value" style="font-size: 1.3rem;">${stats['price']}</div>
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
    """Render a single mover tab with full-width rows and inline Analyze buttons."""
    if not items:
        st.caption("No data available.")
        return

    # Table header
    value_cls = "positive" if accent == "green" else "negative" if accent == "red" else "neutral"
    st.markdown("""
    <div class="mover-tbl-header">
        <div class="mover-tbl-ticker">Ticker</div>
        <div class="mover-tbl-company">Company</div>
        <div class="mover-tbl-sector">Sector</div>
        <div class="mover-tbl-value">Price / Change</div>
    </div>""", unsafe_allow_html=True)

    for i, item in enumerate(items):
        name = item.get("name", "")
        sector = item.get("sector", "")
        row_class = "mover-tbl-row-alt" if i % 2 == 1 else ""

        col_info, col_btn = st.columns([8, 2], gap="small")
        with col_info:
            st.markdown(f"""
            <div class="mover-tbl-row {row_class} accent-{accent}">
                <div class="mover-tbl-ticker">{item['ticker']}</div>
                <div class="mover-tbl-company">{name or '—'}</div>
                <div class="mover-tbl-sector">{sector or '—'}</div>
                <div class="mover-tbl-value {value_cls}">{value_fn(item)}</div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            if st.button("Analyze", key=f"analyze_{key_prefix}_{item['ticker']}", help=f"Analyze {item['ticker']}", use_container_width=True):
                _queue_analysis(item["ticker"])
                st.toast(f"Analysis queued for {item['ticker']}")


def _render_top_movers():
    with st.spinner("Loading market data..."):
        movers = get_top_movers(8)

    if not any(movers.values()):
        st.info("No market data available. Markets may be closed.")
        return

    tab_gain, tab_lose, tab_vol = st.tabs([
        "Top Gainers",
        "Top Losers",
        "Volume Spikes",
    ])

    with tab_gain:
        _render_mover_tab(
            movers.get("gainers", []), "green",
            lambda x: f"${x['price']}  <span class='mover-tbl-change positive'>{x['change_pct']:+.2f}%</span>",
            "g",
        )

    with tab_lose:
        _render_mover_tab(
            movers.get("losers", []), "red",
            lambda x: f"${x['price']}  <span class='mover-tbl-change negative'>{x['change_pct']:+.2f}%</span>",
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

        col.markdown(
            f"""<div class="sector-card" style="background: {bg_gradient}; border-color: {color}30;">
                <div class="sector-name">{s['sector']}</div>
                <div class="sector-change" style="color: {color};">{change:+.2f}%</div>
                <div class="sector-etf">{s['etf']}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_watchlist():
    from core.screener_data import get_ticker_info_cached, get_quick_stats

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
        price_html = ""
        notes = item.get("notes")
        if notes:
            price_html = f'<div style="color: var(--text-secondary); font-size: 0.85rem;">{notes}</div>'
        else:
            stats = get_quick_stats(item["ticker"])
            if "error" not in stats:
                change = stats["change_pct"]
                delta_class = "positive" if change > 0 else "negative" if change < 0 else ""
                price_html = f"""
                <div style="text-align: right;">
                    <div class="card-value" style="font-size: 1.1rem;">${stats['price']}</div>
                    <div class="stat-delta {delta_class}">{change:+.2f}%</div>
                </div>"""

        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span class="card-ticker">{item['ticker']}</span>
                    {f'<span class="card-name" style="margin-left: 8px;">{name}</span>' if name else ''}
                    {f'<div class="card-sector">{sector}{" &middot; " + industry if industry else ""}</div>' if sector or industry else ''}
                </div>
                {price_html}
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1])
            if c1.button("Analyze", key=f"analyze_wl_{item['ticker']}", help=f"Analyze {item['ticker']}", use_container_width=True):
                _queue_analysis(item["ticker"])
                st.toast(f"Analysis queued for {item['ticker']}")
            if c2.button("Remove", key=f"remove_wl_{item['ticker']}", help="Remove from watchlist", use_container_width=True):
                remove_from_watchlist(item["ticker"])
                st.rerun()
