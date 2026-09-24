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
    uvicorn server:app --port 8765          # localhost only (uvicorn default)

Then open http://localhost:8765/ in a browser. Point the Pi-side HAL
client at ws://127.0.0.1:8765/hal.

Security: any /hal client can inject panel events — including
`key: ARM`, which unlocks arm-gated tools. So:
  - Browser connections must come from a page served by this simulator
    (Origin must match Host); a random web page can't drive the panel.
  - To expose the simulator on the LAN (`--host 0.0.0.0`), set
    HAL_SIM_TOKEN=<secret>; every client must then connect with
    `?token=<secret>` (open the panel at http://<host>:8765/?token=<secret>,
    and use ws://<host>:8765/hal?token=<secret> for MINI_AI_OVERLAY_HAL /
    run_scenes.py --sim).
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit
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

# Optional shared secret required on /hal (see module docstring).
HAL_SIM_TOKEN = os.environ.get("HAL_SIM_TOKEN", "")


def _authorized(ws: WebSocket) -> tuple[bool, str]:
    """Reject cross-site browser pages and, if HAL_SIM_TOKEN is set, missing tokens."""
    origin = ws.headers.get("origin")
    # Non-browser clients may omit Origin; browsers always send it.
    if origin and urlsplit(origin).netloc != ws.headers.get("host"):
        return False, f"origin {origin!r} does not match host"
    if HAL_SIM_TOKEN and not hmac.compare_digest(ws.query_params.get("token", ""), HAL_SIM_TOKEN):
        return False, "missing or wrong token"
    return True, ""


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "clients": len(clients)}


@app.websocket("/hal")
async def hal_socket(ws: WebSocket):
    ok, why = _authorized(ws)
    if not ok:
        log.warning("rejected /hal client: %s", why)
        await ws.close(code=1008)   # before accept() -> HTTP 403
        return
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
