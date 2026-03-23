"""Configuration management — loads/saves config.yaml."""

from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_DEFAULTS = {
    "llm": {
        "provider": "claude_cli",
        "quick_think_model": "claude-sonnet-4-6",
        "deep_think_model": "claude-opus-4-6",
        "claude_cli_path": "~/.local/bin/claude",
        "claude_cli_timeout": 300,
    },
    "data": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },
    "analysis": {
        "default_analysts": ["market", "social", "news", "fundamentals"],
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
    },
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            user_cfg = yaml.safe_load(f) or {}
        return _deep_merge(_DEFAULTS, user_cfg)
    return _DEFAULTS.copy()


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def get_tradingagents_config(cfg: dict, overrides: dict | None = None) -> dict:
    """Convert our config.yaml into the dict TradingAgents expects."""
    from tradingagents.default_config import DEFAULT_CONFIG

    ta_cfg = DEFAULT_CONFIG.copy()
    llm = cfg.get("llm", {})
    data = cfg.get("data", {})
    analysis = cfg.get("analysis", {})

    ta_cfg["llm_provider"] = llm.get("provider", "claude_cli")
    ta_cfg["quick_think_llm"] = llm.get("quick_think_model", "claude-sonnet-4-6")
    ta_cfg["deep_think_llm"] = llm.get("deep_think_model", "claude-opus-4-6")
    ta_cfg["claude_cli_path"] = llm.get("claude_cli_path", "~/.local/bin/claude")
    ta_cfg["claude_cli_timeout"] = llm.get("claude_cli_timeout", 300)
    ta_cfg["max_debate_rounds"] = analysis.get("max_debate_rounds", 1)
    ta_cfg["max_risk_discuss_rounds"] = analysis.get("max_risk_discuss_rounds", 1)

    ta_cfg["data_vendors"] = {
        "core_stock_apis": data.get("core_stock_apis", "yfinance"),
        "technical_indicators": data.get("technical_indicators", "yfinance"),
        "fundamental_data": data.get("fundamental_data", "yfinance"),
        "news_data": data.get("news_data", "yfinance"),
    }

    if overrides:
        ta_cfg.update(overrides)

    return ta_cfg


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
