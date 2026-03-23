"""Alerts page — create, manage, and view triggered price alerts."""

import streamlit as st
from core.alerts import create_alert, get_alerts, delete_alert, toggle_alert
from views.icons import icon, page_header


METRIC_OPTIONS = {
    "Price": "price",
    "RSI": "rsi",
    "Change %": "change_pct",
    "Volume": "volume",
}

OPERATOR_OPTIONS = {
    "Above": "above",
    "Below": "below",
}


def render():
    st.markdown(page_header("bell", "Alerts", "Price & Indicator Notifications"), unsafe_allow_html=True)

    tab_create, tab_active, tab_triggered = st.tabs(["Create Alert", "Active Alerts", "Triggered"])

    with tab_create:
        _render_create_form()

    with tab_active:
        _render_active_alerts()

    with tab_triggered:
        _render_triggered_alerts()


def _render_create_form():
    with st.form("create_alert_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker Symbol", placeholder="e.g. NVDA").strip().upper()
            metric_label = st.selectbox("Metric", list(METRIC_OPTIONS.keys()))
        with col2:
            operator_label = st.selectbox("Condition", list(OPERATOR_OPTIONS.keys()))
            threshold = st.number_input("Threshold", value=0.0, format="%.2f")

        submitted = st.form_submit_button("Create Alert", use_container_width=True)

    if submitted:
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return
        metric = METRIC_OPTIONS[metric_label]
        operator = OPERATOR_OPTIONS[operator_label]
        try:
            alert_id = create_alert(ticker, metric, operator, threshold)
            st.success(f"Alert #{alert_id} created: {ticker} {metric_label} {operator_label} {threshold}")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def _render_active_alerts():
    alerts = get_alerts()
    active = [a for a in alerts if a.get("triggered_at") is None]

    if not active:
        st.info("No active alerts. Create one from the 'Create Alert' tab.")
        return

    # Reverse mappings for display
    metric_display = {v: k for k, v in METRIC_OPTIONS.items()}
    operator_display = {v: k for k, v in OPERATOR_OPTIONS.items()}

    for alert in active:
        enabled = bool(alert["enabled"])
        ticker = alert["ticker"]
        metric = metric_display.get(alert["metric"], alert["metric"])
        operator = operator_display.get(alert["operator"], alert["operator"])
        threshold = alert["threshold"]

        opacity = "1" if enabled else "0.5"
        status_color = "var(--green)" if enabled else "var(--text-muted)"
        status_text = "Active" if enabled else "Paused"

        st.markdown(f"""
        <div class="ta-card" style="opacity:{opacity};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="card-ticker">{ticker}</span>
                    <span style="color:var(--text-secondary); font-size:0.85rem; margin-left:8px;">
                        {metric} {operator} {threshold:,.2f}
                    </span>
                </div>
                <span style="font-family:var(--font-mono); font-size:0.75rem; color:{status_color};
                             font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">
                    {status_text}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            toggle_label = "Pause" if enabled else "Enable"
            if st.button(toggle_label, key=f"toggle_{alert['id']}", use_container_width=True):
                toggle_alert(alert["id"])
                st.rerun()
        with col2:
            if st.button("Delete", key=f"delete_{alert['id']}", use_container_width=True):
                delete_alert(alert["id"])
                st.rerun()


def _render_triggered_alerts():
    alerts = get_alerts()
    triggered = [a for a in alerts if a.get("triggered_at") is not None]

    if not triggered:
        st.info("No alerts have been triggered yet.")
        return

    metric_display = {v: k for k, v in METRIC_OPTIONS.items()}
    operator_display = {v: k for k, v in OPERATOR_OPTIONS.items()}

    for alert in triggered:
        ticker = alert["ticker"]
        metric = metric_display.get(alert["metric"], alert["metric"])
        operator = operator_display.get(alert["operator"], alert["operator"])
        threshold = alert["threshold"]
        triggered_at = alert["triggered_at"][:19] if alert["triggered_at"] else "Unknown"

        st.markdown(f"""
        <div class="ta-card ta-card-accent-gold">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="card-ticker">{ticker}</span>
                    <span style="color:var(--text-secondary); font-size:0.85rem; margin-left:8px;">
                        {metric} {operator} {threshold:,.2f}
                    </span>
                </div>
                <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--gold);
                             font-weight:600;">
                    {triggered_at}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Dismiss", key=f"dismiss_{alert['id']}", use_container_width=True):
            delete_alert(alert["id"])
            st.rerun()
