"""Portfolio tracker: manage positions and calculate P&L."""

import logging
from datetime import datetime
from typing import Optional

from core.database import get_db
from core.screener_data import get_ticker_price

logger = logging.getLogger(__name__)


def add_position(
    ticker: str,
    quantity: float,
    entry_price: float,
    entry_date: Optional[str] = None,
    notes: str = "",
) -> int:
    """Add a new position. Returns the position ID."""
    if entry_date is None:
        entry_date = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO positions (ticker, quantity, entry_price, entry_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker.upper(), quantity, entry_price, entry_date, notes),
        )
        return cur.lastrowid


def update_position(
    position_id: int,
    quantity: Optional[float] = None,
    entry_price: Optional[float] = None,
    entry_date: Optional[str] = None,
    notes: Optional[str] = None,
):
    """Update fields on an existing position."""
    updates = []
    params = []
    if quantity is not None:
        updates.append("quantity = ?")
        params.append(quantity)
    if entry_price is not None:
        updates.append("entry_price = ?")
        params.append(entry_price)
    if entry_date is not None:
        updates.append("entry_date = ?")
        params.append(entry_date)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    if not updates:
        return

    params.append(position_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE positions SET {', '.join(updates)} WHERE id = ?",
            params,
        )


def remove_position(position_id: int):
    """Remove a position by ID."""
    with get_db() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))


def get_positions(ticker: Optional[str] = None) -> list[dict]:
    """Get all positions, optionally filtered by ticker."""
    query = "SELECT * FROM positions"
    params = []
    if ticker:
        query += " WHERE ticker = ?"
        params.append(ticker.upper())
    query += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def calculate_portfolio_stats() -> list[dict]:
    """For each position, get current price and calculate P&L.

    Returns list of dicts with position data plus:
    current_price, market_value, cost_basis, pnl, pnl_pct
    """
    positions = get_positions()
    results = []

    for pos in positions:
        current_price = get_ticker_price(pos["ticker"])
        cost_basis = pos["quantity"] * pos["entry_price"]

        if current_price is not None:
            market_value = pos["quantity"] * current_price
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis != 0 else 0.0
        else:
            market_value = None
            pnl = None
            pnl_pct = None

        results.append({
            **pos,
            "current_price": current_price,
            "market_value": round(market_value, 2) if market_value is not None else None,
            "cost_basis": round(cost_basis, 2),
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        })

    return results


def get_portfolio_summary() -> dict:
    """Get aggregate portfolio stats.

    Returns dict with: total_invested, total_value, total_pnl, total_pnl_pct,
    best_performer, worst_performer, position_count
    """
    stats = calculate_portfolio_stats()
    if not stats:
        return {
            "total_invested": 0,
            "total_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "best_performer": None,
            "worst_performer": None,
            "position_count": 0,
        }

    total_invested = sum(s["cost_basis"] for s in stats)
    total_value = sum(s["market_value"] for s in stats if s["market_value"] is not None)
    total_pnl = total_value - total_invested if total_value else 0
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested != 0 else 0

    # Best/worst by P&L %
    with_pnl = [s for s in stats if s["pnl_pct"] is not None]
    best = max(with_pnl, key=lambda s: s["pnl_pct"]) if with_pnl else None
    worst = min(with_pnl, key=lambda s: s["pnl_pct"]) if with_pnl else None

    return {
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "best_performer": {"ticker": best["ticker"], "pnl_pct": best["pnl_pct"]} if best else None,
        "worst_performer": {"ticker": worst["ticker"], "pnl_pct": worst["pnl_pct"]} if worst else None,
        "position_count": len(stats),
    }
