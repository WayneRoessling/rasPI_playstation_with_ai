"""Boot-time configuration for the mini-ai overlay RP2040 firmware.

Runs once at startup before code.py. Keep minimal.

CircuitPython 9+. Tested on Adafruit Metro RP2040.
"""
import supervisor

# Disable auto-reload so file edits over the workstation USB MSC mount don't
# reset the firmware mid-session. Manually re-enable with `supervisor.reload()`
# from the REPL when you want to pick up changes.
supervisor.runtime.autoreload = False

# NOTE: a second USB CDC channel (data) can be enabled here to separate the
# JSON-lines protocol from the REPL. Left disabled in the skeleton — the
# protocol shares the default REPL CDC. To enable, uncomment:
#
#     import usb_cdc
#     usb_cdc.enable(console=True, data=True)
#
# and update lib/protocol.py to use `usb_cdc.data` instead of `sys.stdin/stdout`.
