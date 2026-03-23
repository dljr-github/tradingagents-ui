"""Progress tracking for TradingAgents analysis runs."""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


# Well-known graph node names mapped to friendly labels
NODE_LABELS = {
    "Market Analyst": "Market Analysis",
    "tools_market": "Market Analysis (tools)",
    "Msg Clear Market": "Market Analysis (done)",
    "Social Media Analyst": "Sentiment Analysis",
    "tools_social": "Sentiment Analysis (tools)",
    "Msg Clear Social": "Sentiment Analysis (done)",
    "News Analyst": "News Analysis",
    "tools_news": "News Analysis (tools)",
    "Msg Clear News": "News Analysis (done)",
    "Fundamentals Analyst": "Fundamentals Analysis",
    "tools_fundamentals": "Fundamentals Analysis (tools)",
    "Msg Clear Fundamentals": "Fundamentals Analysis (done)",
    "Bull Researcher": "Bull/Bear Debate (Bull)",
    "Bear Researcher": "Bull/Bear Debate (Bear)",
    "Research Manager": "Research Manager",
    "Trader": "Trader Decision",
    "Aggressive Analyst": "Risk Discussion (Aggressive)",
    "Conservative Analyst": "Risk Discussion (Conservative)",
    "Neutral Analyst": "Risk Discussion (Neutral)",
    "Portfolio Manager": "Portfolio Manager",
}

# Ordered phases for progress bar
PHASES = [
    "Market Analysis",
    "Sentiment Analysis",
    "News Analysis",
    "Fundamentals Analysis",
    "Bull/Bear Debate",
    "Research Manager",
    "Trader Decision",
    "Risk Discussion",
    "Portfolio Manager",
]


@dataclass
class StepInfo:
    node: str
    label: str
    started: float
    completed: Optional[float] = None
    output_preview: str = ""


@dataclass
class RunProgress:
    run_id: int
    steps: list[StepInfo] = field(default_factory=list)
    current_step: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    finished: bool = False
    error: Optional[str] = None

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def current_phase(self) -> Optional[str]:
        if not self.current_step:
            return None
        label = NODE_LABELS.get(self.current_step, self.current_step)
        for phase in PHASES:
            if label.startswith(phase):
                return phase
        return label

    @property
    def phase_index(self) -> int:
        phase = self.current_phase
        if phase is None:
            return 0
        for i, p in enumerate(PHASES):
            if phase.startswith(p) or p.startswith(phase):
                return i
        return 0

    @property
    def progress_fraction(self) -> float:
        if self.finished:
            return 1.0
        return min(0.95, (self.phase_index + 0.5) / len(PHASES))


class ProgressTracker:
    """Thread-safe progress store polled by Streamlit."""

    def __init__(self):
        self._runs: dict[int, RunProgress] = {}
        self._lock = threading.Lock()

    def start_run(self, run_id: int):
        with self._lock:
            self._runs[run_id] = RunProgress(run_id=run_id)

    def on_node_start(self, run_id: int, node_name: str):
        with self._lock:
            prog = self._runs.get(run_id)
            if prog:
                prog.current_step = node_name
                label = NODE_LABELS.get(node_name, node_name)
                prog.steps.append(StepInfo(node=node_name, label=label, started=time.time()))

    def on_node_end(self, run_id: int, node_name: str, output: str = ""):
        with self._lock:
            prog = self._runs.get(run_id)
            if prog and prog.steps:
                prog.steps[-1].completed = time.time()
                prog.steps[-1].output_preview = str(output)[:500]

    def finish_run(self, run_id: int, error: Optional[str] = None):
        with self._lock:
            prog = self._runs.get(run_id)
            if prog:
                prog.finished = True
                prog.error = error

    def get_progress(self, run_id: int) -> Optional[RunProgress]:
        with self._lock:
            return self._runs.get(run_id)

    def get_all_active(self) -> list[RunProgress]:
        with self._lock:
            return [p for p in self._runs.values() if not p.finished]

    def cleanup(self, run_id: int):
        with self._lock:
            self._runs.pop(run_id, None)


# Singleton shared across threads
progress_tracker = ProgressTracker()


class ProgressCallback:
    """LangGraph-compatible callback that feeds into ProgressTracker."""

    def __init__(self, run_id: int):
        self.run_id = run_id

    def on_chain_start(self, serialized=None, inputs=None, **kwargs):
        name = ""
        if serialized:
            name = serialized.get("name", "") or serialized.get("id", [""])[-1]
        tags = kwargs.get("tags", [])
        # LangGraph tags nodes with graph:step:<name>
        for tag in tags:
            if tag.startswith("graph:step:"):
                name = tag.split("graph:step:")[-1]
                break
        if name and name in NODE_LABELS:
            progress_tracker.on_node_start(self.run_id, name)

    def on_chain_end(self, outputs=None, **kwargs):
        prog = progress_tracker.get_progress(self.run_id)
        if prog and prog.current_step:
            preview = ""
            if outputs:
                preview = str(outputs)[:500]
            progress_tracker.on_node_end(self.run_id, prog.current_step, preview)

    def on_chain_error(self, error=None, **kwargs):
        progress_tracker.finish_run(self.run_id, error=str(error))
