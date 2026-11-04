"""Authenticated, read-only live telemetry socket."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import SessionDep
from app.core.security import decode_access_token
from app.core.settings import get_settings
from app.db.models import User
from app.realtime.hub import RealtimeHub


router = APIRouter()


@router.websocket("/ws/measurements")
async def measurements_socket(websocket: WebSocket, session: SessionDep) -> None:
    settings = get_settings()
    if websocket.headers.get("origin") not in settings.allowed_origins:
        raise WebSocketException(code=1008, reason="Origin not allowed")
    protocols = [part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    if "gridwatch" not in protocols:
        raise WebSocketException(code=1008, reason="Unsupported protocol")

    await websocket.accept(subprotocol="gridwatch")
    try:
        frame = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        if not isinstance(frame, dict) or frame.get("type") != "auth" or not isinstance(frame.get("token"), str):
            raise ValueError("Invalid authentication frame")
        user_id = decode_access_token(frame["token"], settings)
    except WebSocketDisconnect:
        return
    except (ValueError, asyncio.TimeoutError):
        await websocket.close(code=1008, reason="Invalid credentials")
        return
    user = await run_in_threadpool(session.get, User, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=1008, reason="Invalid credentials")
        return

    hub: RealtimeHub = websocket.app.state.realtime_hub
    hub.clients.add(websocket)
    try:
        await websocket.send_json({"type": "ready"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(websocket)
