"""Browser-based hardware simulator — protocol broker.

A single FastAPI app that:
  - serves the panel UI at /
  - exposes a WebSocket at /hal that brokers JSON-lines protocol messages
    between connected clients

Both the Pi 5 client (running voice_pipeline.py with the overlay hooked
in) and one or more browser tabs connect to /hal. The server is
transport-only — it does not parse or validate protocol semantics. Every
message is broadcast verbatim to every OTHER connected client.

Run:
    cd overlay/sim
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8765

Then open http://localhost:8765/ in a browser. Point the Pi-side HAL
client at ws://<host>:8765/hal.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sim")

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
OVERLAY_ROOT = HERE.parent
SFX_PREVIEW = OVERLAY_ROOT / "dev_assets" / "sfx_preview"

app = FastAPI(title="mini-ai overlay simulator")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# Serve the generated SFX preview WAVs (if any) so the browser can play
# them when an `sfx` command arrives. Run tools/generate_sfx.py to create them.
if SFX_PREVIEW.exists():
    app.mount("/sfx", StaticFiles(directory=str(SFX_PREVIEW)), name="sfx")

clients: Set[WebSocket] = set()
_lock = asyncio.Lock()


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "clients": len(clients)}


@app.websocket("/hal")
async def hal_socket(ws: WebSocket):
    await ws.accept()
    async with _lock:
        clients.add(ws)
    log.info("client connected (%d total)", len(clients))
    try:
        while True:
            raw = await ws.receive_text()
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except ValueError as exc:
                    log.warning("dropping bad json: %r", exc)
                    continue
                log.info("  %s", json.dumps(msg))
                await _broadcast(line, exclude=ws)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("client error: %r", exc)
    finally:
        async with _lock:
            clients.discard(ws)
        log.info("client disconnected (%d remaining)", len(clients))


async def _broadcast(line: str, exclude: WebSocket | None = None):
    dead = []
    for c in list(clients):
        if c is exclude:
            continue
        try:
            await c.send_text(line)
        except Exception:
            dead.append(c)
    if dead:
        async with _lock:
            for d in dead:
                clients.discard(d)
