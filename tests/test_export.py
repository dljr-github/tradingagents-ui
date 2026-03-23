"""Unit tests for core/export.py."""

import csv
import io

import pytest

from core.export import export_analysis_report, export_screener_csv


class TestExportScreenerCsv:
    def test_valid_csv(self):
        data = [
            {"ticker": "AAPL", "price": 190.5, "change_pct": 1.2},
            {"ticker": "MSFT", "price": 420.0, "change_pct": -0.5},
        ]
        result = export_screener_csv(data)
        assert isinstance(result, bytes)

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(result.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["ticker"] == "AAPL"
        assert rows[1]["price"] == "420.0"

    def test_empty_data(self):
        result = export_screener_csv([])
        assert result == b""

    def test_single_row(self):
        data = [{"ticker": "AAPL", "price": 190.5}]
        result = export_screener_csv(data)
        reader = csv.DictReader(io.StringIO(result.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 1

    def test_headers_match_keys(self):
        data = [{"ticker": "AAPL", "price": 190.5, "rsi": 55.0, "sma50": 185.0}]
        result = export_screener_csv(data)
        reader = csv.DictReader(io.StringIO(result.decode("utf-8")))
        assert set(reader.fieldnames) == {"ticker", "price", "rsi", "sma50"}


class TestExportAnalysisReport:
    def test_formatted_text(self):
        result_data = {
            "ticker": "AAPL",
            "trade_date": "2025-03-15",
            "rating": "BUY",
            "created_at": "2025-03-15 10:00:00",
            "market_report": "Bullish market conditions.",
            "sentiment_report": "Positive sentiment overall.",
            "news_report": "Good news today.",
            "fundamentals_report": "Strong fundamentals.",
            "debate_history": '{"round1": "buy"}',
            "risk_history": '{"risk": "low"}',
            "final_decision": "BUY with high confidence.",
        }
        result = export_analysis_report(result_data)
        assert isinstance(result, bytes)

        text = result.decode("utf-8")
        assert "# Analysis Report: AAPL" in text
        assert "**Rating:** BUY" in text
        assert "## Market Analysis" in text
        assert "Bullish market conditions." in text
        assert "## Sentiment Analysis" in text
        assert "## News Analysis" in text
        assert "## Fundamentals" in text
        assert "## Investment Debate" in text
        assert "## Risk Discussion" in text
        assert "## Final Decision" in text
        assert "BUY with high confidence." in text

    def test_missing_sections(self):
        result_data = {
            "ticker": "MSFT",
            "trade_date": "2025-03-15",
            "rating": "HOLD",
            "created_at": "2025-03-15",
        }
        result = export_analysis_report(result_data)
        text = result.decode("utf-8")
        assert "# Analysis Report: MSFT" in text
        assert "## Market Analysis" not in text  # no market_report

    def test_defaults_for_missing_keys(self):
        result = export_analysis_report({})
        text = result.decode("utf-8")
        assert "N/A" in text
