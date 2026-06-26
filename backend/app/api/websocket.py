from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.progress_hub import progress_hub

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/cases/{task_id}")
async def case_progress_ws(task_id: str, websocket: WebSocket):
    await progress_hub.subscribe(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_hub.unsubscribe(task_id, websocket)
