"""Screener page — stock discovery, watchlist, top movers, sector heatmap."""

import streamlit as st
from core.screener_data import (
    get_quick_stats,
    get_sector_performance,
    get_top_movers,
    get_price_history,
    get_sector_stocks,
    SECTOR_ETFS,
)
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


def _make_candlestick_chart(ticker: str):
    """Render a candlestick chart with SMA overlays and volume bars."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    hist = get_price_history(ticker, "1y")
    if hist.empty:
        st.caption("No price history available for chart.")
        return

    # Calculate SMAs
    hist["SMA50"] = hist["Close"].rolling(50).mean()
    hist["SMA200"] = hist["Close"].rolling(200).mean()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"],
        increasing_line_color="#00d26a", decreasing_line_color="#ff4757",
        increasing_fillcolor="#00d26a", decreasing_fillcolor="#ff4757",
        name="Price",
    ), row=1, col=1)

    # SMA lines
    if hist["SMA50"].notna().any():
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["SMA50"],
            line=dict(color="#00b4d8", width=1.5),
            name="SMA 50",
        ), row=1, col=1)
    if hist["SMA200"].notna().any():
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["SMA200"],
            line=dict(color="#ffd700", width=1.5),
            name="SMA 200",
        ), row=1, col=1)

    # Volume bars — color by direction
    colors = ["#00d26a" if c >= o else "#ff4757" for c, o in zip(hist["Close"], hist["Open"])]
    fig.add_trace(go.Bar(
        x=hist.index, y=hist["Volume"],
        marker_color=colors, opacity=0.5,
        name="Volume", showlegend=False,
    ), row=2, col=1)

    fig.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font=dict(color="#8b95a5", family="DM Sans, sans-serif"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=480,
        xaxis_rangeslider_visible=False,
        xaxis2=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", side="right"),
        yaxis2=dict(gridcolor="rgba(255,255,255,0.06)", side="right"),
    )

    st.plotly_chart(fig, use_container_width=True)


def _make_sparkline(ticker: str):
    """Render a small sparkline chart for 1-month price trend."""
    import plotly.graph_objects as go

    hist = get_price_history(ticker, "1mo")
    if hist.empty or len(hist) < 2:
        return

    prices = hist["Close"]
    color = "#00d26a" if float(prices.iloc[-1]) >= float(prices.iloc[0]) else "#ff4757"

    fig = go.Figure(go.Scatter(
        x=list(range(len(prices))), y=prices,
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba").replace("#00d26a", "rgba(0,210,106,0.08)").replace("#ff4757", "rgba(255,71,87,0.08)"),
    ))
    # Simpler fill approach
    fill_color = "rgba(0,210,106,0.08)" if color == "#00d26a" else "rgba(255,71,87,0.08)"
    fig.data[0].fillcolor = fill_color

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=40, width=120,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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

            # Candlestick price chart
            _make_candlestick_chart(lookup_ticker.strip().upper())

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

    # Table header
    value_cls = "positive" if accent == "green" else "negative" if accent == "red" else "neutral"
    hdr1, hdr2, hdr3, hdr4, hdr5 = st.columns([1, 5, 2, 1, 1])
    hdr1.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Ticker</span>', unsafe_allow_html=True)
    hdr2.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Company</span>', unsafe_allow_html=True)
    hdr3.markdown('<span style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Price / Change</span>', unsafe_allow_html=True)
    # hdr4 and hdr5 are icon buttons, no headers needed
    st.markdown('<hr style="margin:4px 0; border-color:var(--border-medium);">', unsafe_allow_html=True)

    for i, item in enumerate(items):
        name = item.get("name", "")
        sector = item.get("sector", "")
        ticker = item["ticker"]
        bg = "var(--bg-card)" if i % 2 == 1 else "transparent"

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

    # ── Sector bar chart ──
    import plotly.graph_objects as go

    sector_names = [s["sector"] for s in sectors]
    changes = [s["change_pct"] for s in sectors]
    bar_colors = ["#00d26a" if c >= 0 else "#ff4757" for c in changes]

    fig = go.Figure(go.Bar(
        x=sector_names, y=changes,
        marker_color=bar_colors,
        text=[f"{c:+.2f}%" for c in changes],
        textposition="outside",
        textfont=dict(color="#8b95a5", size=11),
    ))
    fig.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font=dict(color="#8b95a5", family="DM Sans, sans-serif"),
        margin=dict(l=0, r=0, t=20, b=0),
        height=280,
        xaxis=dict(tickangle=-45, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=True, zerolinecolor="rgba(255,255,255,0.15)",
            title="Change %",
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Sector cards with expandable drill-down ──
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
                    # Analyze top mover button
                    top_ticker = stocks[0]["ticker"]
                    if st.button(f"Analyze {top_ticker}", key=f"analyze_sector_{s['etf']}", use_container_width=True):
                        _queue_analysis(top_ticker)
                        st.toast(f"Analysis queued for {top_ticker}")
                else:
                    st.caption("No matching stocks in scan universe.")


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
            col_info, col_spark = st.columns([4, 1])
            with col_info:
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
            with col_spark:
                _make_sparkline(item["ticker"])

            c1, c2 = st.columns([1, 1])
            if c1.button("Analyze", key=f"analyze_wl_{item['ticker']}", help=f"Analyze {item['ticker']}", use_container_width=True):
                _queue_analysis(item["ticker"])
                st.toast(f"Analysis queued for {item['ticker']}")
            if c2.button("Remove", key=f"remove_wl_{item['ticker']}", help="Remove from watchlist", use_container_width=True):
                remove_from_watchlist(item["ticker"])
                st.rerun()
