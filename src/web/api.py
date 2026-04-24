"""REST API endpoints for triage tasks."""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.web.schemas import TaskDetail, TaskStatusEnum, TriageRequest, TriageResponse
from src.web.task_manager import task_manager

router = APIRouter(prefix="/api")


@router.post("/triage", response_model=TriageResponse, status_code=202)
async def create_triage(request: TriageRequest):
    """Create a new triage task and start execution."""
    task_id = task_manager.create_task(request.issue_url, request.repo_path)

    # Start task in background
    import asyncio

    asyncio.create_task(
        task_manager.run_triage(task_id, request.issue_url, request.repo_path)
    )

    return TriageResponse(
        task_id=task_id,
        status=TaskStatusEnum.QUEUED,
        ws_url=f"/ws/{task_id}",
    )


@router.get("/triage/{task_id}", response_model=TaskDetail)
async def get_task_status(task_id: str):
    """Get current status and results of a triage task."""
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_manager.tasks[task_id]
    return TaskDetail(
        task_id=task.task_id,
        status=task.status,
        current_phase=task.current_phase,
        result=task.result,
        errors=task.errors,
    )


@router.get("/triage/{task_id}/report")
async def download_report(task_id: str, format: str = "json"):
    """Download triage report in JSON or Markdown format."""
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_manager.tasks[task_id]
    if task.status != TaskStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Task not completed yet")

    if format == "json":
        content = json.dumps(
            {
                "issue_analysis": task.result.get("issue_analysis"),
                "code_location": task.result.get("code_location"),
                "bug_reproduction": task.result.get("bug_reproduction"),
                "fix_generation": task.result.get("fix_generation"),
                "errors": task.errors,
            },
            indent=2,
            default=str,
        )
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=triage_{task_id}.json"},
        )

    elif format == "md":
        lines = ["# Bug Triage Report\n"]
        for key, title in [
            ("issue_analysis", "Issue Analysis"),
            ("code_location", "Code Location"),
            ("bug_reproduction", "Bug Reproduction"),
            ("fix_generation", "Fix Generation"),
        ]:
            data = task.result.get(key)
            if not data:
                continue
            lines.append(f"\n## {title}\n")
            for field, value in data.items():
                if isinstance(value, (list, dict)):
                    lines.append(
                        f"**{field}**:\n```json\n{json.dumps(value, indent=2, default=str)}\n```\n"
                    )
                else:
                    lines.append(f"**{field}**: {value}\n")

        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=triage_{task_id}.md"},
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid format (use json or md)")
