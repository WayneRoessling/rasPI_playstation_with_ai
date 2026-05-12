"""Non-blocking JSON-lines protocol over USB CDC.

Wire format and message types: overlay/docs/HAL_PROTOCOL.md
"""
import json
import sys

import supervisor

MAX_LINE = 1024


class Protocol:
    """JSON-lines over the default REPL CDC.

    To migrate to a second CDC channel (separating protocol from REPL),
    uncomment `usb_cdc.enable(...)` in boot.py and swap `sys.stdin/stdout`
    here for `usb_cdc.data`.
    """

    def __init__(self):
        self._buf = ""

    def send(self, obj: dict) -> None:
        line = json.dumps(obj) + "\n"
        sys.stdout.write(line)

    def drain(self):
        """Yield zero or more parsed messages currently available."""
        while supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
            if ch == "\n":
                line = self._buf.strip()
                self._buf = ""
                if not line:
                    continue
                if len(line) > MAX_LINE:
                    self._log_drop("line too long")
                    continue
                try:
                    yield json.loads(line)
                except (ValueError, MemoryError) as exc:
                    self._log_drop("bad json: {}".format(exc))
            elif ch == "\r":
                continue
            else:
                self._buf += ch
                if len(self._buf) > MAX_LINE:
                    self._buf = ""
                    self._log_drop("buffer overflow")

    @staticmethod
    def _log_drop(msg: str) -> None:
        # stderr keeps drop messages out of the protocol stream
        try:
            sys.stderr.write("[proto] " + msg + "\n")
        except Exception:
            pass
