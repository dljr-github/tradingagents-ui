"""Screener chart helpers — candlestick, sparkline, and sector charts."""

import streamlit as st
from core.screener_data import get_price_history


def make_candlestick_chart(ticker: str):
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


def make_sparkline(ticker: str):
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
        height=60, width=120,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
