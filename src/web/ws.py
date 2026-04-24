"""WebSocket endpoint for real-time progress updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from src.web.task_manager import task_manager

router = APIRouter()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket connection for receiving real-time triage progress."""
    await websocket.accept()
    task_manager.register_connection(task_id, websocket)

    try:
        # Keep connection alive, client will close when done
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    finally:
        task_manager.unregister_connection(task_id, websocket)
