# Hardware simulator — mini-ai overlay

A browser-based stand-in for the RP2040 + control panel. Speaks the
same JSON-lines protocol as the real firmware (see
`overlay/docs/HAL_PROTOCOL.md`), so the Pi 5 side cannot tell the
difference.

```
┌──────────────┐      WebSocket /hal       ┌──────────────┐
│   Pi 5       │ ◄────────────────────────►│   Browser    │
│ voice_       │      (JSON-lines)         │   panel UI   │
│ pipeline.py  │                           │              │
└──────────────┘                           └──────────────┘
                       ▲
                       │  routed by server.py
                       │  (any client → all other clients)
```

## Running

```bash
cd overlay/sim
pip install -r requirements.txt
uvicorn server:app --port 8765
```

Open http://localhost:8765/ in any modern browser. Point the Pi-side
HAL client at `ws://127.0.0.1:8765/hal`.

### Exposing it on the LAN

Any client of `/hal` can inject panel events — including turning the
safety key to `ARM`, which unlocks arm-gated tools. The server rejects
browser connections from pages it didn't serve (Origin ≠ Host). Before
binding to the network, also set a shared token:

```bash
HAL_SIM_TOKEN=some-secret uvicorn server:app --host 0.0.0.0 --port 8765
```

Then open `http://<host>:8765/?token=some-secret` and point the HAL
client (`MINI_AI_OVERLAY_HAL`, `run_scenes.py --sim`) at
`ws://<host>:8765/hal?token=some-secret`.

## What's simulated

- 10 toggle switches (click to flip; emits `switch` events)
- PTT button (mousedown / mouseup → `ptt` 1 / 0 events)
- PIR motion (click to toggle)
- MT-301 key switch (dropdown: SAFE / ARM → `key` events)
- 50-LED grid (renders `led` and `leds` commands)
- 1602 character LCD (renders `lcd` / `lcd_clear`)
- 2× SSD1306 OLED 128×64 (renders `oled` layouts: text, alert, status, icon, raw)
- 10-slot CH358 SFX bank (flashes on `sfx` / `sfx_seq`; plays preview
  WAVs from `/sfx/NN.wav` if `tools/generate_sfx.py` has been run)

Live protocol log on the right-hand side shows every frame in both
directions.

## Why this exists

The control panel hardware involves 100+ components (50 LEDs,
10 switches, 2 OLEDs, 1 LCD, sound module, key switch, PIR, PTT,
shift registers, GPIO expander). Wiring it up takes days. The sim
lets you author scenarios, validate narratives, and develop the
Pi-side overlay logic before any hardware is on the bench — then
verify the same scenarios run unchanged on real hardware.

## SFX preview

To hear the SFX bank in the browser:

```bash
cd overlay
python tools/generate_sfx.py
```

This writes 10 WAVs to `overlay/dev_assets/sfx_preview/`. The server
mounts that directory at `/sfx/` so the browser can play
`/sfx/01.wav` ... `/sfx/10.wav` when `sfx` commands arrive.
