"""Pin assignments and hardware configuration.

Edit to match actual wiring. Imported once at boot by code.py.

Reference pinout: https://learn.adafruit.com/adafruit-metro-rp2040/pinouts

NOTE: Each peripheral's `enabled` flag lets you bring hardware up one module
at a time. The firmware advertises `caps` in its hello frame based on these
flags — the Pi side won't send commands for disabled peripherals.
"""

# `board` is only available on-device. Stubbed import keeps the file
# loadable on a workstation for syntax checking.
try:
    import board
except ImportError:
    class _BoardStub:
        def __getattr__(self, name):
            return name
    board = _BoardStub()


CONFIG = {
    # ── I2C bus (shared: MCP23017, 1602 LCD, both OLEDs) ────────────────────
    "i2c": {
        "sda": board.GP4,
        "scl": board.GP5,
        "frequency_hz": 400_000,
    },

    # ── 10 toggle switches via MCP23017 expander ────────────────────────────
    "switches": {
        "enabled": False,        # flip True when MCP23017 is wired
        "transport": "mcp23017", # alt: "gpio" (then provide `pins` list)
        "mcp_addr": 0x20,
        "mcp_pins": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],  # GPA0..GPB1
        "debounce_ms": 20,
        "active_low": True,      # switches short to GND when ON
    },

    # ── PTT momentary button (direct GPIO) ──────────────────────────────────
    "ptt": {
        "enabled": False,
        "pin": board.GP6,
        "pull": "up",
        "active_low": True,
        "debounce_ms": 10,
    },

    # ── PIR motion sensor ───────────────────────────────────────────────────
    "pir": {
        "enabled": False,
        "pin": board.GP7,
        "pull": "none",          # PIR module drives output high on motion
        "active_low": False,
    },

    # ── MT-301R4P-P key switch (two contacts: SAFE, ARM) ────────────────────
    "key": {
        "enabled": False,
        "transport": "mcp23017", # or "gpio"
        "mcp_addr": 0x20,
        "safe_pin": 10,          # MCP GPB2 — high when key in SAFE position
        "arm_pin": 11,           # MCP GPB3 — high when key in ARM position
        "active_low": True,
    },

    # ── 50 LEDs via daisy-chained 74HC595 shift registers ───────────────────
    "leds": {
        "enabled": False,
        "count": 50,
        "transport": "74hc595",  # alt: "tlc5940" (PWM, future)
        "ser_pin": board.GP10,
        "srclk_pin": board.GP11,
        "rclk_pin": board.GP12,
        "oe_pin": board.GP13,    # active low; tie to GND if not used
    },

    # ── 1602 character LCD (I2C backpack, PCF8574) ──────────────────────────
    "lcd_1602": {
        "enabled": False,
        "i2c_addr": 0x27,
    },

    # ── OLED panel B (Adafruit #938, SSD1306) ───────────────────────────────
    "oled_panel_b": {
        "enabled": False,
        "i2c_addr": 0x3C,
        "width": 128,
        "height": 64,
    },

    # ── OLED master (STEMMA QT 128x64, address jumper to 0x3D) ──────────────
    "oled_master": {
        "enabled": False,
        "i2c_addr": 0x3D,
        "width": 128,
        "height": 64,
    },

    # ── CH358D K-pin trigger outputs (one per slot) ─────────────────────────
    # Each GPIO drives the base of a 2N3904 NPN; the collector pulls the
    # corresponding K-pin to GND. Active high at the GPIO; active low at K.
    "sfx_ch358": {
        "enabled": False,
        "pins": [
            board.GP14, board.GP15, board.GP16, board.GP17, board.GP18,
            board.GP19, board.GP20, board.GP21, board.GP22, board.GP26,
        ],
        "default_pulse_ms": 100,
    },
}
