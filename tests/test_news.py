"""Unit tests for core/news.py."""

import time
from unittest.mock import MagicMock, patch

import pytest

from core import news


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear news cache before each test."""
    news.clear_news_cache()
    yield
    news.clear_news_cache()


class TestGetNews:
    def test_returns_list_of_dicts(self):
        fake_html = """
        <html><body>
        <table id="news-table">
            <tr>
                <td>Mar-20-25 10:30AM</td>
                <td><a href="https://example.com/1">Apple beats earnings expectations</a>
                    <span>Reuters</span></td>
            </tr>
            <tr>
                <td>09:15AM</td>
                <td><a href="https://example.com/2">Apple stock drops on weak guidance</a>
                    <span>Bloomberg</span></td>
            </tr>
        </table>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            results = news.get_news("AAPL")

        assert len(results) == 2
        for item in results:
            assert "title" in item
            assert "url" in item
            assert "source" in item
            assert "published" in item
            assert "sentiment_hint" in item

    def test_caching(self):
        fake_html = """
        <html><body>
        <table id="news-table">
            <tr>
                <td>Mar-20-25 10:30AM</td>
                <td><a href="https://example.com/1">Test headline</a><span>Test</span></td>
            </tr>
        </table>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp) as mock_get:
            news.get_news("AAPL")
            news.get_news("AAPL")  # should hit cache
            assert mock_get.call_count == 1

    def test_max_items(self):
        rows = ""
        for i in range(30):
            rows += f'<tr><td>10:{i:02d}AM</td><td><a href="https://example.com/{i}">News {i}</a><span>Src</span></td></tr>\n'
        fake_html = f'<html><body><table id="news-table">{rows}</table></body></html>'
        mock_resp = MagicMock()
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            results = news.get_news("AAPL", max_items=5)
        assert len(results) == 5

    def test_finviz_fails_falls_back_to_yahoo(self):
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Yahoo headline",
                link="https://yahoo.com/1",
                published="Mon, 20 Mar 2025 10:00:00 GMT",
            )
        ]
        mock_feed.entries[0].get = lambda k, d="": {"title": "Yahoo headline", "link": "https://yahoo.com/1"}.get(k, d)

        with patch("requests.get", side_effect=Exception("Finviz blocked")), \
             patch("feedparser.parse", return_value=mock_feed):
            results = news.get_news("AAPL")

        assert len(results) == 1
        assert results[0]["title"] == "Yahoo headline"
        assert results[0]["source"] == "Yahoo Finance"

    def test_both_sources_fail(self):
        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("requests.get", side_effect=Exception("fail")), \
             patch("feedparser.parse", return_value=mock_feed):
            results = news.get_news("AAPL")
        assert results == []


class TestClearNewsCache:
    def test_clear_specific_ticker(self):
        news._news_cache["AAPL"] = (time.time(), [{"title": "test"}])
        news._news_cache["MSFT"] = (time.time(), [{"title": "test2"}])
        news.clear_news_cache("AAPL")
        assert "AAPL" not in news._news_cache
        assert "MSFT" in news._news_cache

    def test_clear_all(self):
        news._news_cache["AAPL"] = (time.time(), [{"title": "test"}])
        news._news_cache["MSFT"] = (time.time(), [{"title": "test2"}])
        news.clear_news_cache()
        assert len(news._news_cache) == 0


class TestSentimentHint:
    def test_bullish(self):
        assert news._sentiment_hint("Apple stock surges on strong earnings beat") == "bullish"

    def test_bearish(self):
        assert news._sentiment_hint("Stock crashes after fraud investigation announced") == "bearish"

    def test_neutral(self):
        assert news._sentiment_hint("Apple to hold annual event next week") == "neutral"

    def test_mixed_defaults_to_count(self):
        # More bullish words than bearish
        assert news._sentiment_hint("Stock surges and rallies despite some decline") == "bullish"
