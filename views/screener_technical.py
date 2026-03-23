"""Screener technical indicators — MACD, Bollinger Bands, ATR panel."""

import streamlit as st
from core.screener_data import get_indicator_series, get_price_history
from core.theme import get_plotly_theme, get_text_color


def make_technical_indicators_panel(ticker: str, stats: dict):
    """Render MACD chart, Bollinger Bands, and ATR in an expander."""
    import plotly.graph_objects as go

    series = get_indicator_series(ticker)
    if not series:
        return

    with st.expander("Technical Indicators", expanded=False):
        # MACD Chart
        macd_line = series.get("macd_line")
        signal_line = series.get("signal_line")
        macd_hist = series.get("macd_histogram")

        if macd_line is not None and not macd_line.empty:
            st.markdown('<div style="color:var(--text-secondary); font-weight:600; font-size:0.85rem; margin-bottom:4px;">MACD (12, 26, 9)</div>', unsafe_allow_html=True)
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(
                x=macd_line.index, y=macd_line,
                line=dict(color="#00b4d8", width=1.5), name="MACD",
            ))
            fig_macd.add_trace(go.Scatter(
                x=signal_line.index, y=signal_line,
                line=dict(color="#ff8c42", width=1.5), name="Signal",
            ))
            hist_colors = ["#00d26a" if v >= 0 else "#ff4757" for v in macd_hist]
            fig_macd.add_trace(go.Bar(
                x=macd_hist.index, y=macd_hist,
                marker_color=hist_colors, name="Histogram", opacity=0.6,
            ))
            theme = get_plotly_theme()
            fig_macd.update_layout(
                plot_bgcolor=theme["plot_bgcolor"], paper_bgcolor=theme["paper_bgcolor"],
                font=theme["font"],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
                margin=dict(l=0, r=0, t=10, b=0), height=250,
                xaxis=dict(gridcolor=theme["gridcolor"]),
                yaxis=dict(gridcolor=theme["gridcolor"], side="right"),
            )
            st.plotly_chart(fig_macd, use_container_width=True)

        # Bollinger Bands overlaid on price
        bb_upper = series.get("bb_upper")
        bb_middle = series.get("bb_middle")
        bb_lower = series.get("bb_lower")

        if bb_upper is not None and not bb_upper.empty:
            hist = get_price_history(ticker, "1y")
            if not hist.empty:
                st.markdown('<div style="color:var(--text-secondary); font-weight:600; font-size:0.85rem; margin: 8px 0 4px 0;">Bollinger Bands (20, 2)</div>', unsafe_allow_html=True)
                fig_bb = go.Figure()
                fig_bb.add_trace(go.Scatter(
                    x=hist.index, y=hist["Close"],
                    line=dict(color=get_text_color(), width=1.5), name="Price",
                ))
                fig_bb.add_trace(go.Scatter(
                    x=bb_upper.index, y=bb_upper,
                    line=dict(color="#00b4d8", width=1, dash="dot"), name="Upper",
                ))
                fig_bb.add_trace(go.Scatter(
                    x=bb_middle.index, y=bb_middle,
                    line=dict(color="#ffd700", width=1), name="Middle",
                ))
                fig_bb.add_trace(go.Scatter(
                    x=bb_lower.index, y=bb_lower,
                    line=dict(color="#00b4d8", width=1, dash="dot"), name="Lower",
                    fill="tonexty", fillcolor="rgba(0,180,216,0.05)",
                ))
                fig_bb.update_layout(
                    plot_bgcolor=theme["plot_bgcolor"], paper_bgcolor=theme["paper_bgcolor"],
                    font=theme["font"],
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
                    margin=dict(l=0, r=0, t=10, b=0), height=280,
                    xaxis=dict(gridcolor=theme["gridcolor"]),
                    yaxis=dict(gridcolor=theme["gridcolor"], side="right"),
                )
                st.plotly_chart(fig_bb, use_container_width=True)

        # ATR value display
        atr = stats.get("atr")
        if atr is not None:
            st.markdown(f"""
            <div class="stat-grid" style="margin: 8px 0;">
                <div class="stat-item">
                    <div class="stat-label">ATR (14)</div>
                    <div class="stat-value">${atr}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">MACD</div>
                    <div class="stat-value">{stats.get('macd_line', 'N/A')}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">BB Upper</div>
                    <div class="stat-value">${stats.get('bb_upper', 'N/A')}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">BB Lower</div>
                    <div class="stat-value">${stats.get('bb_lower', 'N/A')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
