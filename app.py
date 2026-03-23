"""TradingAgents UI — Streamlit entry point."""

import streamlit as st
from core.database import init_db

# Initialize database on first load
init_db()

st.set_page_config(
    page_title="TradingAgents",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Comprehensive CSS — dark fintech terminal aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Fonts ────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-primary: #0e1117;
    --bg-secondary: #1a1f2e;
    --bg-card: #161b28;
    --bg-card-hover: #1c2235;
    --bg-elevated: #252b3b;
    --border-subtle: rgba(255, 255, 255, 0.06);
    --border-medium: rgba(255, 255, 255, 0.10);
    --border-accent: rgba(0, 210, 106, 0.25);
    --text-primary: #e8eaed;
    --text-secondary: #8b95a5;
    --text-muted: #5a6577;
    --green: #00d26a;
    --green-dim: rgba(0, 210, 106, 0.15);
    --green-glow: rgba(0, 210, 106, 0.3);
    --red: #ff4757;
    --red-dim: rgba(255, 71, 87, 0.15);
    --red-glow: rgba(255, 71, 87, 0.3);
    --cyan: #00b4d8;
    --cyan-dim: rgba(0, 180, 216, 0.12);
    --gold: #ffd700;
    --gold-dim: rgba(255, 215, 0, 0.12);
    --orange: #ff8c42;
    --font-ui: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
    --shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.4);
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Global ───────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font-ui) !important;
}
.stApp {
    background: var(--bg-primary);
}

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
div[data-testid="stDecoration"] { display: none; }
/* Hide Running / Stop status indicator */
div[data-testid="stStatusWidget"] { display: none !important; }
button[kind="headerNoPadding"] { display: none !important; }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
    border-right: 1px solid var(--border-subtle);
}
section[data-testid="stSidebar"] .stRadio > label {
    display: none;
}
section[data-testid="stSidebar"] .stRadio > div {
    gap: 2px;
}
section[data-testid="stSidebar"] .stRadio > div > label {
    font-family: var(--font-ui) !important;
    font-weight: 500;
    font-size: 0.92rem;
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    transition: var(--transition);
    color: var(--text-secondary);
    border: 1px solid transparent;
    cursor: pointer;
    width: 100%;
    display: flex !important;
    align-items: center;
}
/* Hide the radio dot/circle */
section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] .stRadio > div > label > div[data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] .stRadio > div > label > span {
    flex: 1;
}
section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: var(--bg-card);
    color: var(--text-primary);
    border-color: var(--border-subtle);
}
section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked),
section[data-testid="stSidebar"] .stRadio > div [aria-checked="true"] {
    background: var(--green-dim) !important;
    color: var(--green) !important;
    border-color: var(--border-accent) !important;
}

/* ── Typography ───────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-ui) !important;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text-primary);
}
h1 { font-size: 1.75rem !important; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.1rem !important; }
p, span, div, label {
    color: var(--text-primary);
}
.stCaption, small, .stCaption p {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
.stButton > button {
    font-family: var(--font-ui) !important;
    font-weight: 500;
    font-size: 0.85rem;
    border: 1px solid var(--border-medium);
    background: var(--bg-card);
    color: var(--text-primary);
    border-radius: var(--radius-sm);
    padding: 6px 18px;
    transition: var(--transition);
    letter-spacing: 0.01em;
}
.stButton > button:hover {
    background: var(--bg-elevated);
    border-color: var(--green);
    color: var(--green);
    box-shadow: 0 0 12px var(--green-dim);
}
.stButton > button:active {
    transform: scale(0.98);
}
/* Primary button (form submit) */
.stFormSubmitButton > button,
button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #00d26a 0%, #00b85c 100%) !important;
    color: #0e1117 !important;
    font-weight: 600 !important;
    border: none !important;
    letter-spacing: 0.02em;
}
.stFormSubmitButton > button:hover,
button[kind="primaryFormSubmit"]:hover {
    box-shadow: 0 0 20px var(--green-glow) !important;
    transform: translateY(-1px);
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stDateInput > div > div > input,
.stNumberInput > div > div > input {
    font-family: var(--font-ui) !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    transition: var(--transition);
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 2px var(--cyan-dim) !important;
}
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.stDateInput label, .stNumberInput label, .stSlider label {
    font-family: var(--font-ui) !important;
    font-weight: 500;
    font-size: 0.85rem;
    color: var(--text-secondary) !important;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    padding: 4px;
    border: 1px solid var(--border-subtle);
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--font-ui) !important;
    font-weight: 500;
    font-size: 0.85rem;
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
    padding: 8px 20px;
    transition: var(--transition);
    border: none;
    background: transparent;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
    background: var(--bg-card);
}
.stTabs [aria-selected="true"] {
    background: var(--bg-card) !important;
    color: var(--green) !important;
    box-shadow: var(--shadow-card);
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ── Metrics (custom override) ────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: var(--bg-card);
    padding: 16px 20px;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
}
div[data-testid="stMetric"]:hover {
    border-color: var(--border-medium);
    box-shadow: var(--shadow-elevated);
    transform: translateY(-1px);
}
div[data-testid="stMetric"] label {
    font-family: var(--font-ui) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted) !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-family: var(--font-mono) !important;
    font-weight: 600;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] svg { display: none; }

/* ── Cards / Containers ───────────────────────────────────────────────── */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    background: var(--bg-card) !important;
    box-shadow: var(--shadow-card);
    transition: var(--transition);
}
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--border-medium) !important;
    background: var(--bg-card-hover) !important;
}

/* ── Expanders ────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    font-family: var(--font-ui) !important;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--text-secondary);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
}
.streamlit-expanderContent {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-top: none;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--green) 0%, var(--cyan) 100%) !important;
    border-radius: 4px;
}
.stProgress > div > div {
    background: var(--bg-elevated) !important;
    border-radius: 4px;
}

/* ── Sliders ──────────────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--green) !important;
}

/* ── Dataframe ────────────────────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
}

/* ── Dividers ─────────────────────────────────────────────────────────── */
hr {
    border-color: var(--border-subtle) !important;
    margin: 1.5rem 0 !important;
}

/* ── Alerts ───────────────────────────────────────────────────────────── */
.stAlert {
    border-radius: var(--radius-md) !important;
    font-family: var(--font-ui) !important;
}

/* ── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--bg-elevated); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── Rating badges ────────────────────────────────────────────────────── */
.rating-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1.4rem;
    padding: 12px 28px;
    border-radius: var(--radius-md);
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.rating-badge-lg {
    font-size: 2rem;
    padding: 16px 40px;
    border-radius: var(--radius-lg);
}
.rating-buy { background: var(--green-dim); color: var(--green); border: 1px solid var(--green); box-shadow: 0 0 20px var(--green-glow); }
.rating-overweight { background: rgba(125, 216, 125, 0.12); color: #7dd87d; border: 1px solid rgba(125, 216, 125, 0.4); }
.rating-hold { background: var(--gold-dim); color: var(--gold); border: 1px solid rgba(255, 215, 0, 0.4); }
.rating-underweight { background: rgba(255, 140, 66, 0.12); color: var(--orange); border: 1px solid rgba(255, 140, 66, 0.4); }
.rating-sell { background: var(--red-dim); color: var(--red); border: 1px solid var(--red); box-shadow: 0 0 20px var(--red-glow); }

/* ── Header bar ───────────────────────────────────────────────────────── */
.header-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 0 20px 0;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border-subtle);
}
.header-bar svg {
    flex-shrink: 0;
}
.header-bar .header-title {
    font-family: var(--font-ui);
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--text-primary);
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1;
}
.header-bar .header-sub {
    font-family: var(--font-ui);
    font-size: 0.78rem;
    font-weight: 400;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0;
    line-height: 1;
}

/* ── Styled card (HTML) ───────────────────────────────────────────────── */
.ta-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    margin-bottom: 8px;
    box-shadow: var(--shadow-card);
    transition: var(--transition);
}
.ta-card:hover {
    border-color: var(--border-medium);
    background: var(--bg-card-hover);
    transform: translateY(-1px);
}
.ta-card-accent-green { border-left: 3px solid var(--green); }
.ta-card-accent-red { border-left: 3px solid var(--red); }
.ta-card-accent-cyan { border-left: 3px solid var(--cyan); }
.ta-card-accent-gold { border-left: 3px solid var(--gold); }

.ta-card .card-ticker {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1rem;
    color: var(--text-primary);
    letter-spacing: 0.02em;
}
.ta-card .card-name {
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-top: 2px;
}
.ta-card .card-sector {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 2px;
}
.ta-card .card-value {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 1rem;
}
.ta-card .card-value.positive { color: var(--green); }
.ta-card .card-value.negative { color: var(--red); }
.ta-card .card-value.neutral { color: var(--text-secondary); }

/* ── Sector heatmap card ──────────────────────────────────────────────── */
.sector-card {
    border-radius: var(--radius-md);
    padding: 18px 16px;
    margin: 4px 0;
    border: 1px solid var(--border-subtle);
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}
.sector-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    opacity: 0.08;
    border-radius: var(--radius-md);
    z-index: 0;
}
.sector-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-elevated);
}
.sector-card .sector-name {
    font-family: var(--font-ui);
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text-primary);
    position: relative;
    z-index: 1;
}
.sector-card .sector-change {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1.3rem;
    position: relative;
    z-index: 1;
    margin: 6px 0 4px 0;
}
.sector-card .sector-etf {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-muted);
    position: relative;
    z-index: 1;
    letter-spacing: 0.04em;
}

/* ── Pipeline / stepper ───────────────────────────────────────────────── */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    position: relative;
}
.pipeline-step::before {
    content: '';
    position: absolute;
    left: 27px;
    top: 36px;
    bottom: -10px;
    width: 2px;
    background: var(--border-subtle);
}
.pipeline-step:last-child::before { display: none; }
.pipeline-node {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 0.65rem;
    font-weight: 700;
    z-index: 1;
}
.pipeline-node.done { background: var(--green); color: #0e1117; }
.pipeline-node.active { background: var(--cyan); color: #0e1117; animation: pulse 1.5s ease-in-out infinite; }
.pipeline-node.pending { background: var(--bg-elevated); color: var(--text-muted); border: 1px solid var(--border-medium); }
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0, 180, 216, 0.4); }
    50% { box-shadow: 0 0 0 6px rgba(0, 180, 216, 0); }
}
.pipeline-label {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    font-weight: 500;
}
.pipeline-label.done { color: var(--green); }
.pipeline-label.active { color: var(--cyan); }
.pipeline-label.pending { color: var(--text-muted); }

/* ── Debate panels ────────────────────────────────────────────────────── */
.debate-panel {
    border-radius: var(--radius-md);
    padding: 20px 24px;
    border: 1px solid;
    min-height: 200px;
}
.debate-bull {
    background: linear-gradient(135deg, rgba(0, 210, 106, 0.06) 0%, rgba(0, 210, 106, 0.02) 100%);
    border-color: rgba(0, 210, 106, 0.2);
}
.debate-bear {
    background: linear-gradient(135deg, rgba(255, 71, 87, 0.06) 0%, rgba(255, 71, 87, 0.02) 100%);
    border-color: rgba(255, 71, 87, 0.2);
}
.debate-panel-title {
    font-family: var(--font-ui);
    font-weight: 700;
    font-size: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-subtle);
}
.debate-bull .debate-panel-title { color: var(--green); }
.debate-bear .debate-panel-title { color: var(--red); }

/* ── Run status card ──────────────────────────────────────────────────── */
.run-status-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    box-shadow: var(--shadow-card);
}
.run-status-card .run-ticker {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1.3rem;
    color: var(--text-primary);
}
.run-status-card .run-meta {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 4px;
}
.run-elapsed {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 1.1rem;
    color: var(--cyan);
}

/* ── Sidebar branding ─────────────────────────────────────────────────── */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 16px 0;
}
.sidebar-brand .brand-icon {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--green) 0%, var(--cyan) 100%);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.sidebar-brand .brand-text {
    font-family: var(--font-ui);
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--text-primary);
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.sidebar-brand .brand-sub {
    font-size: 0.68rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
}

/* ── Filter bar ───────────────────────────────────────────────────────── */
.filter-bar {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    margin-bottom: 16px;
}

/* ── Custom stat display ──────────────────────────────────────────────── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
}
.stat-item {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    text-align: center;
    transition: var(--transition);
}
.stat-item:hover {
    border-color: var(--border-medium);
    transform: translateY(-1px);
}
.stat-label {
    font-family: var(--font-ui);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 6px;
}
.stat-value {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--text-primary);
}
.stat-delta {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.82rem;
    margin-top: 2px;
}
.stat-delta.positive { color: var(--green); }
.stat-delta.negative { color: var(--red); }

/* ── Report content ───────────────────────────────────────────────────── */
.report-content {
    font-family: var(--font-ui);
    font-size: 0.92rem;
    line-height: 1.7;
    color: var(--text-primary);
}
.report-content h1, .report-content h2, .report-content h3 {
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}
.report-content strong { color: var(--text-primary); }
.report-content code {
    font-family: var(--font-mono);
    background: var(--bg-elevated);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85em;
}

/* ── Verdict card ─────────────────────────────────────────────────────── */
.verdict-card {
    background: linear-gradient(135deg, rgba(0, 180, 216, 0.06) 0%, rgba(0, 180, 216, 0.02) 100%);
    border: 1px solid rgba(0, 180, 216, 0.2);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-top: 16px;
}
.verdict-card .verdict-title {
    font-family: var(--font-ui);
    font-weight: 700;
    font-size: 1rem;
    color: var(--cyan);
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-subtle);
}

/* ── Movers table (full-width tabbed layout) ─────────────────────────── */
.mover-tbl-header {
    display: grid;
    grid-template-columns: 70px 1fr 160px;
    gap: 8px;
    padding: 6px 14px;
    font-family: var(--font-ui);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border-medium);
    margin-bottom: 0;
}
.mover-tbl-row {
    display: grid;
    grid-template-columns: 70px 1fr 160px;
    gap: 8px;
    padding: 5px 14px;
    align-items: center;
    transition: var(--transition);
    border-radius: var(--radius-sm);
    cursor: default;
    margin: 0;
}
.mover-tbl-row:hover {
    background: var(--bg-card-hover);
}
.mover-tbl-row-alt {
    background: var(--bg-card);
}
.mover-tbl-row-alt:hover {
    background: var(--bg-card-hover);
}
.mover-tbl-row.accent-green { border-left: 3px solid var(--green); }
.mover-tbl-row.accent-red { border-left: 3px solid var(--red); }
.mover-tbl-row.accent-cyan { border-left: 3px solid var(--cyan); }

.mover-tbl-row .mover-tbl-ticker {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--text-primary);
    letter-spacing: 0.02em;
}
.mover-tbl-row .mover-tbl-company {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.mover-tbl-row .mover-tbl-sector {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.mover-tbl-row .mover-tbl-value {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.9rem;
    text-align: right;
    white-space: nowrap;
}
.mover-tbl-row .mover-tbl-value.positive { color: var(--green); }
.mover-tbl-row .mover-tbl-value.negative { color: var(--red); }
.mover-tbl-row .mover-tbl-value.neutral { color: var(--cyan); }
.mover-tbl-change {
    font-weight: 700;
    margin-left: 6px;
}
.mover-tbl-change.positive { color: var(--green); }
.mover-tbl-change.negative { color: var(--red); }

/* ── Section header with icon ────────────────────────────────────────── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 12px 0;
    padding: 0;
    font-family: var(--font-ui);
    font-weight: 600;
    font-size: 1.05rem;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}
.section-header svg {
    flex-shrink: 0;
}

/* ── Button no-wrap ──────────────────────────────────────────────────── */
.stButton > button {
    white-space: nowrap !important;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 6px 10px;
    font-size: 0.8rem;
}

/* ── Compact mover table rows (reduce Streamlit vertical gaps) ─────── */
.stTabs [data-baseweb="tab-panel"] > div > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"],
.stTabs [data-baseweb="tab-panel"] > div > div[data-testid="stVerticalBlock"] > div[data-testid="column"] {
    margin-bottom: -12px;
}
/* Tighten columns within mover rows */
.stTabs div[data-testid="stHorizontalBlock"] {
    gap: 0.25rem !important;
    align-items: center;
    margin-bottom: -8px;
}
/* Vertically center the Analyze button in its column */
.stTabs div[data-testid="stHorizontalBlock"] .stButton {
    margin-top: -4px;
}
</style>
""", unsafe_allow_html=True)

# Light theme override
if st.session_state.get("theme") == "light":
    st.markdown("""
    <style>
    :root {
        --bg-primary: #f5f6fa;
        --bg-secondary: #ebedf2;
        --bg-card: #ffffff;
        --bg-card-hover: #f0f1f5;
        --bg-elevated: #e8e9ed;
        --border-subtle: rgba(0, 0, 0, 0.08);
        --border-medium: rgba(0, 0, 0, 0.14);
        --border-accent: rgba(0, 160, 80, 0.3);
        --text-primary: #1a1a2e;
        --text-secondary: #555770;
        --text-muted: #8a8ca5;
        --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
        --shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    .stApp { background: var(--bg-primary); }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0f1f5 0%, #e8e9ed 100%);
        border-right: 1px solid var(--border-subtle);
    }
    section[data-testid="stSidebar"] .stRadio > div > label {
        color: var(--text-secondary);
    }
    section[data-testid="stSidebar"] .stRadio > div > label:hover {
        background: var(--bg-card);
        color: var(--text-primary);
    }
    .stButton > button {
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-medium);
    }
    .stButton > button:hover {
        background: var(--bg-elevated);
        color: var(--green);
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-medium) !important;
    }
    .stTextInput label, .stSelectbox label, .stMultiSelect label,
    .stDateInput label, .stNumberInput label, .stSlider label {
        color: var(--text-secondary) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-secondary);
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary);
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary);
        background: var(--bg-card);
    }
    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--green) !important;
    }
    p, span, div, label { color: var(--text-primary); }
    h1, h2, h3, h4, h5, h6 { color: var(--text-primary); }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — branding + navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
             fill="none" stroke="#0e1117" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
            <polyline points="17 6 23 6 23 12"/></svg>
        </div>
        <div>
            <div class="brand-text">TradingAgents</div>
            <div class="brand-sub">AI-Powered Analysis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Theme toggle
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"
    theme_label = "Light Mode" if st.session_state["theme"] == "dark" else "Dark Mode"
    if st.button(theme_label, key="theme_toggle", use_container_width=True):
        st.session_state["theme"] = "light" if st.session_state["theme"] == "dark" else "dark"
        st.rerun()

    st.divider()

    PAGES = {
        "Screener": "screener",
        "Analysis": "analysis",
        "Results": "results",
        "History": "history",
        "News": "news",
        "Alerts": "alerts",
        "Portfolio": "portfolio",
        "Comparison": "comparison",
        "Settings": "settings",
    }
    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    selected = PAGES[page]

# Import and render selected page
if selected == "screener":
    from views.screener import render
elif selected == "analysis":
    from views.analysis import render
elif selected == "results":
    from views.results import render
elif selected == "history":
    from views.history import render
elif selected == "news":
    from views.news import render
elif selected == "alerts":
    from views.alerts import render
elif selected == "portfolio":
    from views.portfolio import render
elif selected == "comparison":
    from views.comparison import render
elif selected == "settings":
    from views.settings import render

render()
