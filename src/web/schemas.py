"""Pydantic schemas for Web API."""
from enum import Enum

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    """Request body for starting a triage task."""

    issue_url: str = Field(..., description="GitHub issue URL")
    repo_path: str = Field("", description="Path to local repository clone")


class TaskStatusEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriageResponse(BaseModel):
    """Response after creating a triage task."""

    task_id: str
    status: TaskStatusEnum
    ws_url: str


class TaskDetail(BaseModel):
    """Full task status and results."""

    task_id: str
    status: TaskStatusEnum
    current_phase: str = ""
    result: dict | None = None
    errors: list[dict] = []
