"""Settings page — configure LLM, data vendors, defaults."""

import streamlit as st
from core.config import load_config, save_config
from views.icons import icon_header


def render():
    st.markdown(icon_header("gear", "Settings"), unsafe_allow_html=True)

    cfg = load_config()

    with st.form("settings_form"):
        # LLM Configuration
        st.subheader("LLM Configuration")
        llm = cfg.get("llm", {})

        col1, col2 = st.columns(2)
        with col1:
            provider = st.selectbox(
                "Provider",
                ["claude_cli", "openai", "anthropic", "google", "ollama", "openrouter"],
                index=["claude_cli", "openai", "anthropic", "google", "ollama", "openrouter"].index(
                    llm.get("provider", "claude_cli")
                ),
            )
            quick_model = st.text_input(
                "Quick Think Model",
                value=llm.get("quick_think_model", "claude-sonnet-4-6"),
            )
            deep_model = st.text_input(
                "Deep Think Model",
                value=llm.get("deep_think_model", "claude-opus-4-6"),
            )

        with col2:
            cli_path = st.text_input(
                "Claude CLI Path",
                value=llm.get("claude_cli_path", "~/.local/bin/claude"),
            )
            cli_timeout = st.number_input(
                "CLI Timeout (seconds)",
                min_value=30,
                max_value=1200,
                value=llm.get("claude_cli_timeout", 300),
            )

        st.divider()

        # Data Configuration
        st.subheader("Data Configuration")
        data = cfg.get("data", {})

        data_options = ["yfinance", "alpha_vantage"]
        col1, col2 = st.columns(2)
        with col1:
            core_api = st.selectbox(
                "Core Stock API",
                data_options,
                index=data_options.index(data.get("core_stock_apis", "yfinance")),
            )
            tech_indicators = st.selectbox(
                "Technical Indicators",
                data_options,
                index=data_options.index(data.get("technical_indicators", "yfinance")),
            )
        with col2:
            fundamental = st.selectbox(
                "Fundamental Data",
                data_options,
                index=data_options.index(data.get("fundamental_data", "yfinance")),
            )
            news = st.selectbox(
                "News Data",
                data_options,
                index=data_options.index(data.get("news_data", "yfinance")),
            )

        st.divider()

        # Default Analysis Settings
        st.subheader("Default Analysis Settings")
        analysis = cfg.get("analysis", {})

        all_analysts = ["market", "social", "news", "fundamentals"]
        default_analysts = st.multiselect(
            "Default Analysts",
            all_analysts,
            default=analysis.get("default_analysts", all_analysts),
        )

        col1, col2 = st.columns(2)
        with col1:
            debate_rounds = st.slider(
                "Max Debate Rounds",
                min_value=1,
                max_value=3,
                value=analysis.get("max_debate_rounds", 1),
            )
        with col2:
            risk_rounds = st.slider(
                "Max Risk Discussion Rounds",
                min_value=1,
                max_value=3,
                value=analysis.get("max_risk_discuss_rounds", 1),
            )

        submitted = st.form_submit_button("Save Settings", use_container_width=True)

    if submitted:
        new_cfg = {
            "llm": {
                "provider": provider,
                "quick_think_model": quick_model,
                "deep_think_model": deep_model,
                "claude_cli_path": cli_path,
                "claude_cli_timeout": cli_timeout,
            },
            "data": {
                "core_stock_apis": core_api,
                "technical_indicators": tech_indicators,
                "fundamental_data": fundamental,
                "news_data": news,
            },
            "analysis": {
                "default_analysts": default_analysts,
                "max_debate_rounds": debate_rounds,
                "max_risk_discuss_rounds": risk_rounds,
            },
        }
        save_config(new_cfg)
        st.success("Settings saved!")
        st.rerun()

    # Show current config
    with st.expander("Current config.yaml"):
        import yaml
        st.code(yaml.dump(cfg, default_flow_style=False), language="yaml")
