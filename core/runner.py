"""Analysis runner — manages TradingAgents runs via multiprocessing."""

import json
import logging
import multiprocessing as mp
import os
import signal
import time
from typing import Optional

from core.config import get_tradingagents_config, load_config
from core.database import complete_run, create_run, fail_run, update_run_status
from core.progress import progress_tracker

logger = logging.getLogger(__name__)

# Valid ratings in priority order
VALID_RATINGS = ["STRONG BUY", "BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL", "STRONG SELL"]


def _extract_rating(text: str) -> str:
    """Extract rating from analysis text without requiring an LLM call."""
    text_upper = text.upper()
    # Check for each rating keyword in the text
    for rating in VALID_RATINGS:
        if rating in text_upper:
            return rating
    # Fallback: look for common patterns
    import re
    match = re.search(r"(?:rating|recommendation|decision|signal)[:\s]*(BUY|SELL|HOLD|OVERWEIGHT|UNDERWEIGHT)", text_upper)
    if match:
        return match.group(1)
    return "HOLD"

# Directory for progress IPC files
PROGRESS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".progress")
os.makedirs(PROGRESS_DIR, exist_ok=True)


def _progress_file(run_id: int) -> str:
    return os.path.join(PROGRESS_DIR, f"run_{run_id}.json")


def _write_progress(run_id: int, data: dict):
    """Write progress to a JSON file for cross-process communication."""
    path = _progress_file(run_id)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def read_progress(run_id: int) -> Optional[dict]:
    """Read progress from a JSON file (called from Streamlit process)."""
    path = _progress_file(run_id)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def cleanup_progress(run_id: int):
    """Remove progress file after run completes."""
    try:
        os.remove(_progress_file(run_id))
    except FileNotFoundError:
        pass


def _run_analysis_worker(
    run_id: int,
    ticker: str,
    trade_date: str,
    analysts: list,
    ta_config: dict,
):
    """Worker function that runs in a separate process."""
    # Re-import inside worker process
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from core.database import complete_run, fail_run, update_run_status

    update_run_status(run_id, "running")
    _write_progress(run_id, {
        "status": "running",
        "current_step": "Initializing",
        "steps": [],
        "started_at": time.time(),
    })

    try:
        ta = TradingAgentsGraph(
            selected_analysts=analysts,
            debug=False,
            config=ta_config,
        )

        # Stream mode to capture progress
        from tradingagents.agents.utils.agent_states import AgentState
        from tradingagents.graph.propagation import Propagator

        propagator = Propagator(max_recur_limit=ta_config.get("max_recur_limit", 150))
        init_state = propagator.create_initial_state(ticker, trade_date)
        args = propagator.get_graph_args()

        steps = []
        step_names_seen = set()

        # Map state keys to step names
        STEP_MAP = {
            "market_report": "Market Analyst",
            "sentiment_report": "Social Media Analyst",
            "news_report": "News Analyst",
            "fundamentals_report": "Fundamentals Analyst",
            "investment_debate_state": None,  # handled specially
            "trader_investment_plan": "Trader",
            "risk_debate_state": None,  # handled specially
            "final_trade_decision": "Portfolio Manager",
        }

        for chunk in ta.graph.stream(init_state, **args):
            # Detect which step completed based on state changes
            step_name = None

            for key, name in STEP_MAP.items():
                if key in chunk and chunk[key]:
                    if key == "investment_debate_state":
                        debate = chunk[key]
                        speaker = debate.get("current_response", "")
                        if speaker.startswith("Bull"):
                            step_name = "Bull Researcher"
                        elif speaker.startswith("Bear"):
                            step_name = "Bear Researcher"
                        elif debate.get("judge_decision"):
                            step_name = "Research Manager"
                    elif key == "risk_debate_state":
                        risk = chunk[key]
                        speaker = risk.get("latest_speaker", "")
                        if speaker == "Aggressive":
                            step_name = "Aggressive Analyst"
                        elif speaker == "Conservative":
                            step_name = "Conservative Analyst"
                        elif speaker == "Neutral":
                            step_name = "Neutral Analyst"
                        elif speaker == "Judge":
                            step_name = "Portfolio Manager"
                    else:
                        step_name = name

            if step_name and step_name not in step_names_seen:
                step_names_seen.add(step_name)
                steps.append({
                    "name": step_name,
                    "completed_at": time.time(),
                })
                _write_progress(run_id, {
                    "status": "running",
                    "current_step": step_name,
                    "steps": steps,
                    "started_at": steps[0]["completed_at"] if steps else time.time(),
                })

        # Get final state from last chunk
        final_state = chunk

        # Extract rating from final decision text
        decision = final_state.get("final_trade_decision", "")
        rating = _extract_rating(decision) if decision else "HOLD"

        complete_run(run_id, rating, final_state)
        _write_progress(run_id, {
            "status": "completed",
            "current_step": "Done",
            "steps": steps,
            "rating": rating,
            "completed_at": time.time(),
        })
        logger.info("Run %d completed: %s → %s", run_id, ticker, rating)

    except Exception as e:
        logger.exception("Run %d failed: %s", run_id, e)
        fail_run(run_id, str(e))
        _write_progress(run_id, {
            "status": "failed",
            "error": str(e),
            "steps": steps if 'steps' in dir() else [],
        })


class AnalysisRunner:
    """Manages background TradingAgents analysis runs via multiprocessing."""

    _instance: Optional["AnalysisRunner"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._processes: dict[int, mp.Process] = {}
        self._initialized = True

    def submit(
        self,
        ticker: str,
        trade_date: str,
        analysts: list[str] | None = None,
        config_overrides: dict | None = None,
    ) -> int:
        """Submit a new analysis run. Returns the run ID."""
        cfg = load_config()
        ta_config = get_tradingagents_config(cfg, config_overrides)

        if analysts is None:
            analysts = cfg.get("analysis", {}).get(
                "default_analysts", ["market", "social", "news", "fundamentals"]
            )

        run_id = create_run(ticker, trade_date, {
            "analysts": analysts,
            "ta_config": {k: v for k, v in ta_config.items() if isinstance(v, (str, int, float, bool, list))},
        })

        proc = mp.Process(
            target=_run_analysis_worker,
            args=(run_id, ticker, trade_date, analysts, ta_config),
            daemon=True,
            name=f"analysis-{ticker}-{run_id}",
        )
        proc.start()
        self._processes[run_id] = proc
        return run_id

    def cancel(self, run_id: int):
        """Cancel a running analysis."""
        proc = self._processes.get(run_id)
        if proc and proc.is_alive():
            os.kill(proc.pid, signal.SIGTERM)
            proc.join(timeout=5)
            if proc.is_alive():
                proc.kill()
        update_run_status(run_id, "cancelled")
        _write_progress(run_id, {"status": "cancelled"})
        self._processes.pop(run_id, None)

    def is_running(self, run_id: int) -> bool:
        proc = self._processes.get(run_id)
        if proc is None:
            return False
        if proc.is_alive():
            return True
        # Process finished — clean up
        self._processes.pop(run_id, None)
        return False

    def get_progress(self, run_id: int) -> Optional[dict]:
        """Get progress for a run (reads from IPC file)."""
        return read_progress(run_id)

    def active_runs(self) -> list[int]:
        """Return list of currently active run IDs."""
        # Clean up dead processes
        dead = [rid for rid, proc in self._processes.items() if not proc.is_alive()]
        for rid in dead:
            self._processes.pop(rid, None)
        return list(self._processes.keys())


def get_runner() -> AnalysisRunner:
    return AnalysisRunner()
