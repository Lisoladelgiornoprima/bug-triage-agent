"""Task manager: bridges Coordinator with WebSocket for async execution."""
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from anthropic import Anthropic
from fastapi import WebSocket
from loguru import logger

from src.config import config
from src.core.coordinator import Coordinator
from src.tools.github_client import GitHubClient
from src.web.schemas import TaskStatusEnum


@dataclass
class TaskInfo:
    """Stores state for a single triage task."""

    task_id: str
    status: TaskStatusEnum = TaskStatusEnum.QUEUED
    current_phase: str = ""
    result: dict[str, Any] | None = None
    errors: list[dict] = field(default_factory=list)


class TaskManager:
    """Manages triage tasks, bridging sync Coordinator to async WebSocket."""

    def __init__(self):
        self.tasks: dict[str, TaskInfo] = {}
        self.connections: dict[str, list[WebSocket]] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.loop: asyncio.AbstractEventLoop | None = None

    def create_task(self, issue_url: str, repo_path: str) -> str:
        """Create a new triage task and return its ID."""
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = TaskInfo(task_id=task_id)
        return task_id

    async def run_triage(self, task_id: str, issue_url: str, repo_path: str):
        """Run triage in a thread pool, bridging progress to WebSocket."""
        self.loop = asyncio.get_event_loop()
        task = self.tasks[task_id]
        task.status = TaskStatusEnum.RUNNING

        def on_progress(agent_name: str, event: str, detail: str):
            """Progress callback from Coordinator, bridge to WebSocket."""
            asyncio.run_coroutine_threadsafe(
                self._broadcast(
                    task_id,
                    {
                        "type": "progress",
                        "agent": agent_name,
                        "event": event,
                        "detail": detail,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ),
                self.loop,
            )

        try:
            # Initialize clients
            anthropic_client = Anthropic(api_key=config.anthropic_api_key)
            github_client = GitHubClient(token=config.github_token)

            # Create coordinator with progress callback
            coordinator = Coordinator(
                anthropic_client=anthropic_client,
                github_client=github_client,
                repo_path=repo_path if repo_path else None,
                on_progress=on_progress,
            )

            # Run in thread pool (coordinator.run is sync)
            state = await self.loop.run_in_executor(
                self.executor, coordinator.run, issue_url
            )

            # Update task with results
            task.status = (
                TaskStatusEnum.COMPLETED
                if state.status.value == "completed"
                else TaskStatusEnum.FAILED
            )
            task.result = state.data
            task.errors = state.errors

            # Broadcast completion
            await self._broadcast(
                task_id,
                {
                    "type": "done",
                    "status": task.status.value,
                    "result": task.result,
                    "errors": task.errors,
                },
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            task.status = TaskStatusEnum.FAILED
            task.errors.append({"phase": "system", "error": str(e)})
            await self._broadcast(
                task_id, {"type": "error", "message": str(e)}
            )

    async def _broadcast(self, task_id: str, message: dict):
        """Broadcast message to all WebSocket connections for this task."""
        if task_id not in self.connections:
            return

        dead_connections = []
        for ws in self.connections[task_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.connections[task_id].remove(ws)

    def register_connection(self, task_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a task."""
        if task_id not in self.connections:
            self.connections[task_id] = []
        self.connections[task_id].append(websocket)

    def unregister_connection(self, task_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        if task_id in self.connections and websocket in self.connections[task_id]:
            self.connections[task_id].remove(websocket)


# Global singleton
task_manager = TaskManager()

