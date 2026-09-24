"""Transport implementations for the HAL client.

All transports expose:
    connect()                — open the link, start any receive thread
    send(line: str)          — send one JSON-lines frame (no trailing \\n required)
    recv_line(timeout=None)  — return one received line or None on timeout
    close()                  — shut down
    connected                — False once the link has dropped (or before connect)

Receivers are responsible for splitting on \\n. The client layer above
parses JSON.
"""
from __future__ import annotations

import queue
import threading
from typing import Optional


class WebsocketTransport:
    """Talks to the browser simulator at ws://host:port/hal.

    Requires `websocket-client`: pip install websocket-client.

    `connect_timeout` is used only when establishing the connection. Once
    connected, the socket is set to blocking with no timeout — the rx
    loop exits only on `close()` or a genuine disconnect. This prevents
    long idle periods (e.g. while Ollama composes a multi-second reply)
    from raising `socket.timeout`, which the rx loop's broad `except`
    would treat as a fatal disconnect and silently kill the receive
    thread.

    The kwarg name `recv_timeout` is preserved as a backward-compatible
    alias since some callers (e.g. the scene runner) pass it positionally
    or by name. Both spellings set the connect timeout.
    """

    def __init__(
        self,
        url: str = "ws://127.0.0.1:8765/hal",
        recv_timeout: float = 10.0,
        *,
        connect_timeout: Optional[float] = None,
    ):
        self.url = url
        self.connect_timeout = (
            connect_timeout if connect_timeout is not None else recv_timeout
        )
        # Kept for backward compat — callers that read this still see something
        # sensible; it now reflects the connect timeout.
        self.recv_timeout = self.connect_timeout
        self.ws = None
        self._rx_q: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        try:
            from websocket import create_connection  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "websocket-client required: pip install websocket-client"
            ) from e
        self.ws = create_connection(self.url, timeout=self.connect_timeout)
        # The connect timeout becomes the default socket timeout for
        # subsequent recv() calls — turn it off so idle periods don't
        # tear down the rx thread.
        self.ws.settimeout(None)
        self._stop.clear()   # allow reconnect after close()
        self._thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._thread.start()

    @property
    def connected(self) -> bool:
        return self.ws is not None and self._thread is not None and self._thread.is_alive()

    def _rx_loop(self) -> None:
        from websocket import WebSocketException  # type: ignore
        while not self._stop.is_set():
            try:
                raw = self.ws.recv()
            except (WebSocketException, ConnectionError, OSError):
                break   # link dropped — `connected` now reports False
            if raw is None:
                continue
            for line in (raw if isinstance(raw, str) else raw.decode("utf-8", "replace")).split("\n"):
                line = line.strip()
                if line:
                    self._rx_q.put(line)

    def send(self, line: str) -> None:
        if self.ws is None:
            raise RuntimeError("not connected")
        # WebSocket frame is text; strip any trailing newline
        self.ws.send(line.rstrip("\n"))

    def recv_line(self, timeout: Optional[float] = None) -> Optional[str]:
        try:
            return self._rx_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._stop.set()
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass


class SerialTransport:
    """USB CDC serial transport for the RP2040 firmware.

    Requires `pyserial`: pip install pyserial.

    Note: untested against real hardware until Drop 5+. The interface
    is functional but only wired up so the demo and CLI work uniformly.
    """

    def __init__(self, port: str, baud: int = 115200, recv_timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.recv_timeout = recv_timeout
        self.ser = None
        self._failed = False

    def connect(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError as e:
            raise RuntimeError("pyserial required: pip install pyserial") from e
        self.ser = serial.Serial(self.port, self.baud, timeout=self.recv_timeout)
        self._failed = False

    @property
    def connected(self) -> bool:
        return self.ser is not None and not self._failed

    def send(self, line: str) -> None:
        if self.ser is None:
            raise RuntimeError("not connected")
        data = line if line.endswith("\n") else line + "\n"
        self.ser.write(data.encode("utf-8"))
        self.ser.flush()

    def recv_line(self, timeout: Optional[float] = None) -> Optional[str]:
        if self.ser is None:
            return None
        # pyserial readline honours its constructed `timeout`; we ignore the
        # per-call timeout here for simplicity (sub-second polling is fine).
        try:
            raw = self.ser.readline()
        except Exception:
            # pyserial raises on unplug (SerialException / OSError)
            self._failed = True
            return None
        if not raw:
            return None
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    def close(self) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass


class MockTransport:
    """In-process transport for unit tests.

    Lines you `inject()` come back from `recv_line`. Lines that the
    client `send()`s are captured in `.sent` for assertions.
    """

    def __init__(self):
        self.sent: list[str] = []
        self._rx_q: queue.Queue[str] = queue.Queue()
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    @property
    def connected(self) -> bool:
        return self._connected

    def send(self, line: str) -> None:
        if not self._connected:
            raise RuntimeError("not connected")
        self.sent.append(line.rstrip("\n"))

    def recv_line(self, timeout: Optional[float] = None) -> Optional[str]:
        try:
            return self._rx_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._connected = False

    def inject(self, line: str) -> None:
        """Test helper — feed a line into the receive queue."""
        self._rx_q.put(line)
