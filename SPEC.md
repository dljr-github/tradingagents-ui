# TradingAgents UI — Specification

## Overview
A Streamlit-based trading workstation that wraps the TradingAgents framework.
Discover stocks → Analyze with AI agents → Review decisions → Track history.

## Stack
- **Frontend:** Streamlit
- **Backend:** Python (background threads for analysis runs)
- **Database:** SQLite (run history, watchlist)
- **Data:** yfinance (screener + market data)
- **AI Engine:** TradingAgents (pip install from fork: dljr-github/TradingAgents)
- **Python:** 3.13, conda env `tradingagents-ui`

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Streamlit App                   │
├──────────┬──────────┬───────────┬───────────────┤
│ Screener │ Analysis │  Results  │    History     │
│   Page   │   Page   │   Page    │     Page      │
├──────────┴──────────┴───────────┴───────────────┤
│              Analysis Runner Service             │
│  (ThreadPoolExecutor — parallel ticker runs)     │
├─────────────────────────────────────────────────┤
│    TradingAgents    │   yfinance   │   SQLite    │
└─────────────────────┴──────────────┴─────────────┘
```

## Pages

### 1. 📊 Screener (Home)
- **Top Movers** — gainers, losers, volume spikes (yfinance)
- **Sector Heatmap** — S&P 500 sectors with daily performance
- **Watchlist** — user's saved tickers (SQLite)
- **Quick Stats** per ticker: price, % change, volume, RSI, 50/200 SMA
- **"Analyze" button** on each ticker → queues TradingAgents run

### 2. 🤖 Analysis 
- **Active Runs** — shows all running analyses with real-time progress
  - Progress bar / step indicator: Market → Social → News → Fundamentals → Bull/Bear Debate → Research Manager → Trader → Risk Discussion → Portfolio Manager
  - Elapsed time per step
  - Cancel button
- **New Analysis** — ticker input + date picker + config options
- **Config Sidebar:**
  - LLM provider (claude_cli)
  - Model selection for quick_think / deep_think
  - Analyst toggles (market, social, news, fundamentals)
  - Debate rounds (1-3)
  - Risk discussion rounds (1-3)

### 3. 📋 Results
- **Header Card** — ticker, date, final rating (Buy/Overweight/Hold/Underweight/Sell) with color coding
- **Tabs:**
  - **Market Analysis** — full technical report
  - **Sentiment** — social media analysis
  - **News** — macro/news report
  - **Fundamentals** — valuation & financial data
  - **Bull vs Bear Debate** — side-by-side debate history
  - **Risk Discussion** — aggressive/conservative/neutral arguments
  - **Portfolio Manager** — final synthesis & decision
- **Key Levels Table** — support/resistance levels extracted from reports
- **Raw JSON** — expandable full state dump

### 4. 📈 History
- **Table** of all past runs: ticker, date, decision, rating, timestamp
- **Filters:** by ticker, date range, rating
- **Click to view** full results
- **Accuracy Tracking** — compare decision vs actual price movement (fetch current price via yfinance)
- **Compare Mode** — select 2+ runs to view side-by-side

### 5. ⚙️ Settings
- **LLM Config** — Claude CLI as primary provider. Model selection per role (quick_think: Sonnet, deep_think: Opus). CLI path, timeout.
- **Data Config** — data vendors (yfinance by default)
- **Default Analysts** — which to include by default
- **Saved to** `config.yaml`

## Data Model (SQLite)

### `runs` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| ticker | TEXT | Stock ticker |
| trade_date | TEXT | Analysis date |
| created_at | TIMESTAMP | When run was started |
| completed_at | TIMESTAMP | When run finished |
| status | TEXT | pending/running/completed/failed/cancelled |
| rating | TEXT | Buy/Overweight/Hold/Underweight/Sell |
| config_json | TEXT | Config used for this run |
| market_report | TEXT | Market analyst report |
| sentiment_report | TEXT | Social/sentiment report |
| news_report | TEXT | News report |
| fundamentals_report | TEXT | Fundamentals report |
| debate_history | TEXT | Bull/Bear debate |
| risk_history | TEXT | Risk discussion |
| final_decision | TEXT | Portfolio manager decision |
| full_state_json | TEXT | Complete state dump |

### `watchlist` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| ticker | TEXT UNIQUE | Stock ticker |
| added_at | TIMESTAMP | When added |
| notes | TEXT | Optional notes |

## Analysis Runner

- Uses `concurrent.futures.ThreadPoolExecutor` for parallel runs
- Each run gets a unique ID, stored in SQLite with status updates
- Custom LangGraph callback captures progress per node
- Progress stored in a shared dict (thread-safe) for Streamlit to poll
- Results saved to SQLite on completion

## Progress Tracking

Custom callback that hooks into LangGraph's node execution:
```python
class ProgressCallback:
    def __init__(self, run_id):
        self.run_id = run_id
        self.steps = []
        self.current_step = None
        self.start_time = None
    
    def on_node_start(self, node_name):
        self.current_step = node_name
        self.steps.append({"node": node_name, "started": time.time()})
    
    def on_node_end(self, node_name, output):
        self.steps[-1]["completed"] = time.time()
        self.steps[-1]["output_preview"] = str(output)[:500]
```

## File Structure
```
tradingagents-ui/
├── app.py                    # Streamlit entry point + page routing
├── pages/
│   ├── screener.py           # Stock screener / home
│   ├── analysis.py           # Run & monitor analyses
│   ├── results.py            # View analysis results
│   ├── history.py            # Historical runs
│   └── settings.py           # Configuration
├── core/
│   ├── runner.py             # Analysis runner (ThreadPoolExecutor)
│   ├── database.py           # SQLite operations
│   ├── screener_data.py      # yfinance screener queries
│   ├── progress.py           # Progress tracking callback
│   └── config.py             # Config management
├── config.yaml               # User config
├── requirements.txt
├── pyproject.toml
├── README.md
└── .gitignore
```

## Design
- Dark theme (Streamlit dark mode)
- Color-coded ratings: Buy=green, Sell=red, Hold=yellow
- Responsive layout
- Minimal custom CSS — leverage Streamlit components
