"""Pi 5 side HAL client for the mini-ai overlay.

Speaks the JSON-lines protocol defined in overlay/docs/HAL_PROTOCOL.md.
Connects to either the browser-based simulator (WebSocket) or the
real RP2040 firmware (USB CDC serial). Pi-side application code
should not know the difference.

Typical use:

    from pi5_hal import HalClient
    from pi5_hal.transport import WebsocketTransport

    hal = HalClient(WebsocketTransport("ws://127.0.0.1:8765/hal"))
    hal.on("switch", lambda m: print("switch", m["id"], "->", m["state"]))
    hal.connect()

    hal.set_led(1, on=True)
    hal.play_sfx(7)
    hal.write_lcd(1, "ALT 12000 OK")

    # ... main loop, callbacks fire on the receive thread ...

    hal.disconnect()
"""
from .client import HalClient
from .transport import WebsocketTransport, SerialTransport, MockTransport

__all__ = ["HalClient", "WebsocketTransport", "SerialTransport", "MockTransport"]
