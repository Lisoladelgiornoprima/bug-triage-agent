"""Workflow state management."""
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """Manages the state of the bug triage workflow.

    Stores intermediate results from each agent and supports
    checkpoint/resume functionality.
    """

    status: WorkflowStatus = WorkflowStatus.PENDING
    current_phase: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)

    def update(self, key: str, value: Any) -> None:
        """Update workflow data."""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get workflow data."""
        return self.data.get(key, default)

    def add_error(self, phase: str, error: str) -> None:
        """Record an error during execution."""
        self.errors.append({"phase": phase, "error": error})

    def save_checkpoint(self, path: Path) -> None:
        """Save current state to a checkpoint file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "status": self.status.value,
                    "current_phase": self.current_phase,
                    "data": self.data,
                    "errors": self.errors,
                },
                f,
                indent=2,
                default=str,
            )

    @classmethod
    def load_checkpoint(cls, path: Path) -> "WorkflowState":
        """Load state from a checkpoint file."""
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        state = cls()
        state.status = WorkflowStatus(d["status"])
        state.current_phase = d["current_phase"]
        state.data = d["data"]
        state.errors = d["errors"]
        return state
