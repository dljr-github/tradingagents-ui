"""Theme utilities for consistent dark/light mode across all components."""

import streamlit as st


def is_light_mode() -> bool:
    return st.session_state.get("theme") == "light"


def get_plotly_theme() -> dict:
    """Return plotly layout kwargs matching current theme."""
    if is_light_mode():
        return {
            "plot_bgcolor": "#ffffff",
            "paper_bgcolor": "#f5f6fa",
            "font": dict(color="#555770", family="DM Sans, sans-serif"),
            "gridcolor": "rgba(0, 0, 0, 0.08)",
            "zerolinecolor": "rgba(0, 0, 0, 0.15)",
        }
    return {
        "plot_bgcolor": "#0e1117",
        "paper_bgcolor": "#0e1117",
        "font": dict(color="#8b95a5", family="DM Sans, sans-serif"),
        "gridcolor": "rgba(255, 255, 255, 0.06)",
        "zerolinecolor": "rgba(255, 255, 255, 0.15)",
    }


def get_text_color() -> str:
    """Primary text color for inline HTML."""
    return "#1a1a2e" if is_light_mode() else "#e8eaed"


def get_muted_color() -> str:
    """Muted/secondary text color."""
    return "#8a8ca5" if is_light_mode() else "#8b95a5"


def get_card_bg() -> str:
    """Card background color for plotly/inline."""
    return "#ffffff" if is_light_mode() else "#161b28"
