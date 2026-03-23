"""Unit tests for views/icons.py."""

import pytest

from views.icons import icon, icon_header, page_header


class TestIcon:
    def test_returns_svg_string(self):
        result = icon("chart")
        assert "<svg" in result
        assert "</svg>" in result

    def test_known_icons(self):
        known = [
            "chart", "cpu", "clipboard", "clock", "gear", "trending-up",
            "trending-down", "bar-chart", "scale", "flame", "shield",
            "check-circle", "x-circle", "slash", "loader", "play", "search",
            "x", "activity", "target", "eye", "zap", "briefcase",
            "newspaper", "bell", "columns", "pie-chart",
        ]
        for name in known:
            result = icon(name)
            assert "<svg" in result, f"Icon '{name}' did not return SVG"

    def test_unknown_icon_returns_empty(self):
        result = icon("nonexistent-icon")
        assert result == ""

    def test_custom_size(self):
        result = icon("chart", size=24)
        assert 'width="24"' in result
        assert 'height="24"' in result

    def test_custom_color(self):
        result = icon("chart", color="#ff0000")
        assert 'stroke="#ff0000"' in result

    def test_default_color_is_currentcolor(self):
        result = icon("chart")
        assert 'stroke="currentColor"' in result


class TestIconHeader:
    def test_returns_html(self):
        result = icon_header("chart", "Test Header")
        assert "<div" in result
        assert "Test Header" in result
        assert "<svg" in result

    def test_level_affects_font_size(self):
        h1 = icon_header("chart", "Title", level=1)
        h3 = icon_header("chart", "Title", level=3)
        assert "1.75rem" in h1
        assert "1.1rem" in h3

    def test_default_level_is_2(self):
        result = icon_header("chart", "Title")
        assert "1.35rem" in result


class TestPageHeader:
    def test_returns_html_structure(self):
        result = page_header("chart", "My Page", "A subtitle")
        assert "header-bar" in result
        assert "header-title" in result
        assert "My Page" in result
        assert "A subtitle" in result
        assert "<svg" in result

    def test_without_subtitle(self):
        result = page_header("chart", "My Page")
        assert "header-sub" not in result

    def test_icon_colored_green(self):
        result = page_header("chart", "Title")
        assert "#00d26a" in result
