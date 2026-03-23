"""Export functions: CSV and markdown report generation."""

import csv
import io
from datetime import datetime


def export_screener_csv(data: list[dict]) -> bytes:
    """Export screener data as CSV bytes for Streamlit download_button.

    Args:
        data: List of dicts with screener row data.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    if not data:
        return b""

    output = io.StringIO()
    fieldnames = list(data[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue().encode("utf-8")


def export_analysis_report(result: dict) -> bytes:
    """Export an analysis result as a formatted markdown report.

    Args:
        result: Dict from database with analysis run data (from get_run()).

    Returns:
        UTF-8 encoded markdown bytes.
    """
    ticker = result.get("ticker", "N/A")
    trade_date = result.get("trade_date", "N/A")
    rating = result.get("rating", "N/A")
    created = result.get("created_at", "N/A")

    sections = []
    sections.append(f"# Analysis Report: {ticker}")
    sections.append(f"**Trade Date:** {trade_date}")
    sections.append(f"**Rating:** {rating}")
    sections.append(f"**Generated:** {created}")
    sections.append("")

    if result.get("market_report"):
        sections.append("## Market Analysis")
        sections.append(result["market_report"])
        sections.append("")

    if result.get("sentiment_report"):
        sections.append("## Sentiment Analysis")
        sections.append(result["sentiment_report"])
        sections.append("")

    if result.get("news_report"):
        sections.append("## News Analysis")
        sections.append(result["news_report"])
        sections.append("")

    if result.get("fundamentals_report"):
        sections.append("## Fundamentals")
        sections.append(result["fundamentals_report"])
        sections.append("")

    if result.get("debate_history"):
        sections.append("## Investment Debate")
        sections.append(result["debate_history"])
        sections.append("")

    if result.get("risk_history"):
        sections.append("## Risk Discussion")
        sections.append(result["risk_history"])
        sections.append("")

    if result.get("final_decision"):
        sections.append("## Final Decision")
        sections.append(result["final_decision"])
        sections.append("")

    sections.append("---")
    sections.append(f"*Report exported {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(sections).encode("utf-8")
