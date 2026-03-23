"""Alerts system: price and indicator alerts with SQLite persistence."""

import logging
from datetime import datetime
from typing import Optional

from core.database import get_db
from core.screener_data import get_quick_stats

logger = logging.getLogger(__name__)

VALID_METRICS = {"price", "rsi", "change_pct", "volume"}
VALID_OPERATORS = {"above", "below", "crosses_above", "crosses_below"}

# Track previous values for crosses_above/crosses_below detection
_prev_values: dict[str, dict[str, float]] = {}


def create_alert(
    ticker: str,
    metric: str,
    operator: str,
    threshold: float,
) -> int:
    """Create a new alert. Returns the alert ID."""
    if metric not in VALID_METRICS:
        raise ValueError(f"Invalid metric: {metric}. Must be one of {VALID_METRICS}")
    if operator not in VALID_OPERATORS:
        raise ValueError(f"Invalid operator: {operator}. Must be one of {VALID_OPERATORS}")

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO alerts (ticker, metric, operator, threshold, enabled)
               VALUES (?, ?, ?, ?, 1)""",
            (ticker.upper(), metric, operator, threshold),
        )
        return cur.lastrowid


def get_alerts(
    ticker: Optional[str] = None,
    enabled_only: bool = False,
) -> list[dict]:
    """Get all alerts, optionally filtered by ticker and enabled status."""
    query = "SELECT * FROM alerts WHERE 1=1"
    params = []
    if ticker:
        query += " AND ticker = ?"
        params.append(ticker.upper())
    if enabled_only:
        query += " AND enabled = 1"
    query += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def delete_alert(alert_id: int):
    """Delete an alert by ID."""
    with get_db() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))


def toggle_alert(alert_id: int) -> bool:
    """Toggle an alert's enabled status. Returns new enabled state."""
    with get_db() as conn:
        row = conn.execute("SELECT enabled FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise ValueError(f"Alert {alert_id} not found")
        new_state = 0 if row["enabled"] else 1
        conn.execute("UPDATE alerts SET enabled = ? WHERE id = ?", (new_state, alert_id))
        return bool(new_state)


def trigger_alert(alert_id: int):
    """Mark an alert as triggered with current timestamp."""
    with get_db() as conn:
        conn.execute(
            "UPDATE alerts SET triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert_id),
        )


def _get_metric_value(stats: dict, metric: str) -> Optional[float]:
    """Extract a metric value from quick stats."""
    if "error" in stats:
        return None
    mapping = {
        "price": "price",
        "rsi": "rsi",
        "change_pct": "change_pct",
        "volume": "volume",
    }
    val = stats.get(mapping.get(metric))
    return float(val) if val is not None else None


def _evaluate_condition(
    current: float,
    operator: str,
    threshold: float,
    prev: Optional[float],
) -> bool:
    """Evaluate whether an alert condition is met."""
    if operator == "above":
        return current > threshold
    elif operator == "below":
        return current < threshold
    elif operator == "crosses_above":
        if prev is None:
            return False
        return prev <= threshold and current > threshold
    elif operator == "crosses_below":
        if prev is None:
            return False
        return prev >= threshold and current < threshold
    return False


def check_alerts() -> list[dict]:
    """Evaluate all enabled alerts against current data.

    Returns list of triggered alert dicts.
    """
    alerts = get_alerts(enabled_only=True)
    if not alerts:
        return []

    # Group alerts by ticker to minimize API calls
    by_ticker: dict[str, list[dict]] = {}
    for alert in alerts:
        by_ticker.setdefault(alert["ticker"], []).append(alert)

    triggered = []
    for ticker, ticker_alerts in by_ticker.items():
        stats = get_quick_stats(ticker)
        if "error" in stats:
            logger.warning("Could not get stats for %s: %s", ticker, stats.get("error"))
            continue

        for alert in ticker_alerts:
            metric = alert["metric"]
            current = _get_metric_value(stats, metric)
            if current is None:
                continue

            # Get previous value for cross detection
            prev_key = f"{ticker}:{metric}"
            prev = _prev_values.get(ticker, {}).get(metric)

            if _evaluate_condition(current, alert["operator"], alert["threshold"], prev):
                trigger_alert(alert["id"])
                triggered.append({
                    **dict(alert),
                    "current_value": current,
                })

        # Update previous values for this ticker
        _prev_values[ticker] = {
            "price": _get_metric_value(stats, "price"),
            "rsi": _get_metric_value(stats, "rsi"),
            "change_pct": _get_metric_value(stats, "change_pct"),
            "volume": _get_metric_value(stats, "volume"),
        }

    return triggered
