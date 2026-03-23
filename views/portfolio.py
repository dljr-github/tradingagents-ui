"""Portfolio page — track positions, P&L, and allocation."""

from datetime import date

import streamlit as st
from core.theme import get_plotly_theme
from core.portfolio import (
    add_position,
    get_positions,
    remove_position,
    calculate_portfolio_stats,
    get_portfolio_summary,
)
from views.icons import page_header


def render():
    st.markdown(page_header("briefcase", "Portfolio", "Position Tracking & P&L"), unsafe_allow_html=True)

    # Calculate stats upfront
    stats = calculate_portfolio_stats()
    summary = get_portfolio_summary()

    # Summary cards
    _render_summary(summary)

    st.divider()

    tab_positions, tab_add = st.tabs(["Positions", "Add Position"])

    with tab_positions:
        _render_positions(stats)

    with tab_add:
        _render_add_form()

    # Allocation chart
    if stats:
        st.divider()
        _render_allocation_chart(stats)


def _render_summary(summary: dict):
    total_value = summary["total_value"]
    total_pnl = summary["total_pnl"]
    total_pnl_pct = summary["total_pnl_pct"]
    best = summary.get("best_performer")
    worst = summary.get("worst_performer")

    pnl_cls = "positive" if total_pnl >= 0 else "negative"
    sign = "+" if total_pnl >= 0 else ""
    pnl_pct_cls = "positive" if total_pnl_pct >= 0 else "negative"
    sign_pct = "+" if total_pnl_pct >= 0 else ""

    row1 = st.columns(3)

    with row1[0]:
        st.markdown(f"""
        <div class="ta-card" style="text-align:center;">
            <div class="stat-label">Value</div>
            <div class="stat-value">${total_value:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with row1[1]:
        st.markdown(f"""
        <div class="ta-card" style="text-align:center;">
            <div class="stat-label">P&amp;L</div>
            <div class="stat-value {pnl_cls}">{sign}${total_pnl:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with row1[2]:
        st.markdown(f"""
        <div class="ta-card" style="text-align:center;">
            <div class="stat-label">P&amp;L %</div>
            <div class="stat-value {pnl_pct_cls}">{sign_pct}{total_pnl_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    row2 = st.columns(2)

    with row2[0]:
        if best:
            best_sign = "+" if best["pnl_pct"] >= 0 else ""
            st.markdown(f"""
            <div class="ta-card ta-card-accent-green" style="text-align:center;">
                <div class="stat-label">Best</div>
                <div class="card-ticker">{best['ticker']}</div>
                <div class="stat-delta positive">{best_sign}{best['pnl_pct']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="ta-card" style="text-align:center;">
                <div class="stat-label">Best</div>
                <div class="stat-value" style="color:var(--text-muted);">--</div>
            </div>
            """, unsafe_allow_html=True)

    with row2[1]:
        if worst:
            worst_sign = "+" if worst["pnl_pct"] >= 0 else ""
            st.markdown(f"""
            <div class="ta-card ta-card-accent-red" style="text-align:center;">
                <div class="stat-label">Worst</div>
                <div class="card-ticker">{worst['ticker']}</div>
                <div class="stat-delta negative">{worst_sign}{worst['pnl_pct']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="ta-card" style="text-align:center;">
                <div class="stat-label">Worst</div>
                <div class="stat-value" style="color:var(--text-muted);">--</div>
            </div>
            """, unsafe_allow_html=True)


def _render_positions(stats: list[dict]):
    if not stats:
        st.info("No positions yet. Add one from the 'Add Position' tab.")
        return

    # Table header
    h_tick, h_name, h_qty, h_entry, h_cur, h_pnl, h_pnl_pct, h_act = st.columns([1, 2, 1, 1, 1, 1, 1, 1])
    header_style = 'style="color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;"'
    h_tick.markdown(f'<span {header_style}>Ticker</span>', unsafe_allow_html=True)
    h_name.markdown(f'<span {header_style}>Company</span>', unsafe_allow_html=True)
    h_qty.markdown(f'<span {header_style}>Qty</span>', unsafe_allow_html=True)
    h_entry.markdown(f'<span {header_style}>Entry</span>', unsafe_allow_html=True)
    h_cur.markdown(f'<span {header_style}>Current</span>', unsafe_allow_html=True)
    h_pnl.markdown(f'<span {header_style}>P&L</span>', unsafe_allow_html=True)
    h_pnl_pct.markdown(f'<span {header_style}>P&L %</span>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:4px 0; border-color:var(--border-medium);">', unsafe_allow_html=True)

    for pos in stats:
        ticker = pos["ticker"]
        name = pos.get("name") or ticker
        qty = pos["quantity"]
        entry_price = pos["entry_price"]
        current_price = pos.get("current_price")
        pnl = pos.get("pnl")
        pnl_pct = pos.get("pnl_pct")

        pnl_cls = "positive" if pnl and pnl >= 0 else "negative" if pnl and pnl < 0 else ""
        pnl_sign = "+" if pnl and pnl >= 0 else ""
        pnl_pct_sign = "+" if pnl_pct and pnl_pct >= 0 else ""

        c_tick, c_name, c_qty, c_entry, c_cur, c_pnl, c_pnl_pct, c_act = st.columns([1, 2, 1, 1, 1, 1, 1, 1])
        c_tick.markdown(f'<span style="font-family:var(--font-mono); font-weight:700; font-size:0.95rem; color:var(--text-primary);">{ticker}</span>', unsafe_allow_html=True)
        c_name.markdown(f'<span style="color:var(--text-secondary); font-size:0.85rem;">{name}</span>', unsafe_allow_html=True)
        c_qty.markdown(f'<span style="font-family:var(--font-mono); font-size:0.9rem;">{qty:g}</span>', unsafe_allow_html=True)
        c_entry.markdown(f'<span style="font-family:var(--font-mono); font-size:0.9rem;">${entry_price:,.2f}</span>', unsafe_allow_html=True)

        if current_price is not None:
            c_cur.markdown(f'<span style="font-family:var(--font-mono); font-size:0.9rem;">${current_price:,.2f}</span>', unsafe_allow_html=True)
        else:
            c_cur.markdown('<span style="color:var(--text-muted);">--</span>', unsafe_allow_html=True)

        if pnl is not None:
            c_pnl.markdown(f'<span class="stat-delta {pnl_cls}" style="font-size:0.9rem;">{pnl_sign}${abs(pnl):,.2f}</span>', unsafe_allow_html=True)
            c_pnl_pct.markdown(f'<span class="stat-delta {pnl_cls}" style="font-size:0.9rem;">{pnl_pct_sign}{pnl_pct:.2f}%</span>', unsafe_allow_html=True)
        else:
            c_pnl.markdown('<span style="color:var(--text-muted);">--</span>', unsafe_allow_html=True)
            c_pnl_pct.markdown('<span style="color:var(--text-muted);">--</span>', unsafe_allow_html=True)

        if c_act.button("Remove", key=f"rm_pos_{pos['id']}", use_container_width=True):
            remove_position(pos["id"])
            st.rerun()


def _render_add_form():
    with st.form("add_position_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker Symbol", placeholder="e.g. AAPL").strip().upper()
            quantity = st.number_input("Quantity", min_value=0.01, value=1.0, format="%.4f")
        with col2:
            entry_price = st.number_input("Entry Price", min_value=0.01, value=100.0, format="%.2f")
            entry_date = st.date_input("Entry Date", value=date.today())

        notes = st.text_input("Notes (optional)", placeholder="e.g. Swing trade, earnings play")

        submitted = st.form_submit_button("Add Position", use_container_width=True)

    if submitted:
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return
        pos_id = add_position(
            ticker=ticker,
            quantity=quantity,
            entry_price=entry_price,
            entry_date=entry_date.isoformat(),
            notes=notes,
        )
        st.success(f"Position #{pos_id} added: {quantity:g} shares of {ticker} @ ${entry_price:.2f}")
        st.rerun()


def _render_allocation_chart(stats: list[dict]):
    import plotly.graph_objects as go

    st.markdown(
        '<div style="font-family:var(--font-ui); font-weight:600; font-size:1rem; '
        'color:var(--text-primary); margin-bottom:8px;">Portfolio Allocation</div>',
        unsafe_allow_html=True,
    )

    # Filter positions with valid market values
    valid = [s for s in stats if s.get("market_value") and s["market_value"] > 0]
    if not valid:
        st.caption("No valid market values to display allocation chart.")
        return

    labels = [s["ticker"] for s in valid]
    values = [s["market_value"] for s in valid]

    colors = [
        "#00d26a", "#00b4d8", "#ffd700", "#ff8c42", "#ff4757",
        "#7dd87d", "#9b59b6", "#3498db", "#e74c3c", "#2ecc71",
    ]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="label+percent",
        textfont=dict(size=12, family="DM Sans, sans-serif"),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    ))

    theme = get_plotly_theme()
    fig.update_layout(
        plot_bgcolor=theme["plot_bgcolor"],
        paper_bgcolor=theme["paper_bgcolor"],
        font=theme["font"],
        margin=dict(l=0, r=0, t=20, b=20),
        height=360,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5, font=dict(size=11),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
