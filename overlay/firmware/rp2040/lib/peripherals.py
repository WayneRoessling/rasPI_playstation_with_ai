"""Peripheral abstractions for the mini-ai overlay.

Each peripheral exposes a small interface (poll / emit_state / set_one / ...).
The skeleton ships with stub implementations that respect the `enabled` flag
in config.py: disabled peripherals are reported as missing in the `caps` list
and silently no-op on all calls.

Replace stub bodies with real driver code as hardware is wired up — one
peripheral at a time. The protocol stays unchanged.

Recommended CircuitPython libraries (install on CIRCUITPY/lib/):

  adafruit_bus_device         (shared)
  adafruit_mcp230xx           (switches, key)
  adafruit_character_lcd      (1602 via PCF8574 backpack)
  adafruit_ssd1306            (both OLEDs)
  adafruit_74hc595            (LED chain)
  adafruit_framebuf           (OLED layouts)
"""
# pylint: disable=unused-argument,no-self-use


class Peripherals:
    def __init__(self, cfg, proto):
        self.cfg = cfg
        self.proto = proto
        # Shared bus would be constructed here once any I2C peripheral is enabled.
        # self._i2c = busio.I2C(cfg["i2c"]["scl"], cfg["i2c"]["sda"])
        self.switches = SwitchBank(cfg.get("switches", {}), proto)
        self.ptt = PttButton(cfg.get("ptt", {}), proto)
        self.pir = PirSensor(cfg.get("pir", {}), proto)
        self.key = KeySwitch(cfg.get("key", {}), proto)
        self.leds = LedBank(cfg.get("leds", {}), proto)
        self.lcd = CharLcd(cfg.get("lcd_1602", {}), proto)
        self.oled = OledBank(cfg.get("oled_panel_b", {}),
                             cfg.get("oled_master", {}), proto)
        self.sfx = SfxBank(cfg.get("sfx_ch358", {}), proto)

    def capabilities(self):
        caps = []
        if self.switches.enabled: caps.append("switches")
        if self.ptt.enabled:      caps.append("ptt")
        if self.pir.enabled:      caps.append("pir")
        if self.key.enabled:      caps.append("key")
        if self.leds.enabled:     caps.append("leds")
        if self.lcd.enabled:      caps.append("lcd")
        if self.oled.enabled:     caps.append("oled")
        if self.sfx.enabled:      caps.append("sfx")
        return caps

    def self_test(self):
        for p in (self.switches, self.ptt, self.pir, self.key,
                  self.leds, self.lcd, self.oled, self.sfx):
            p.self_test()

    def poll(self, now_ms):
        self.switches.poll(now_ms)
        self.ptt.poll(now_ms)
        self.pir.poll(now_ms)
        self.key.poll(now_ms)
        self.sfx.poll(now_ms)

    def emit_sync(self, now_ms):
        for p in (self.switches, self.ptt, self.pir, self.key):
            p.emit_state(now_ms)

    def reset(self):
        self.leds.clear_all()
        self.lcd.clear()


class _Base:
    def __init__(self, cfg, proto):
        self.cfg = cfg
        self.proto = proto
        self.enabled = bool(cfg.get("enabled", False))

    def self_test(self): pass
    def poll(self, now_ms): pass
    def emit_state(self, now_ms): pass


class SwitchBank(_Base):
    """10 toggle switches via MCP23017 (or direct GPIO).

    TODO: instantiate adafruit_mcp230xx.MCP23017 on the shared I2C bus,
    configure 10 pins as inputs with pull-up, then in poll() read GPIOA/B
    once per loop, debounce per-pin, emit {"t":"switch","id":N,"state":S}
    on edges. emit_state() should send the current state of all 10 in one
    burst (used to answer `sync` commands).
    """


class PttButton(_Base):
    """Push-to-talk momentary button (direct GPIO).

    TODO: configure digitalio.DigitalInOut with pull-up. Debounce. Emit
    {"t":"ptt","state":0|1} on edges.
    """


class PirSensor(_Base):
    """Inland PIR motion sensor (direct GPIO).

    TODO: PIR output goes HIGH on detect, falls after ~3-5s. Emit
    {"t":"pir","state":0|1} on each transition.
    """


class KeySwitch(_Base):
    """MT-301R4P-P 4-pole rotary isolator. Decoded as SAFE / ARM.

    TODO: read both contact pins (SAFE, ARM). One should be HIGH at a time.
    Map to pos string; emit {"t":"key","pos":"SAFE"|"ARM"} on change.
    """


class LedBank(_Base):
    """50 LEDs via daisy-chained 74HC595 shift registers (binary on/off).

    TODO: construct shift register chain (7 chips = 56 channels; use first 50).
    set_one() updates one bit in the local state buffer and shifts the whole
    chain. set_bulk() parses values per format and shifts in one pass.

    Formats:
      hex_pairs : "FF0080..." (2 hex chars per LED, 0..255; binary driver
                  treats >=128 as ON)
      mask      : "0x0123ABCD" hex bitmask (LED1 = bit 0)
    """
    def __init__(self, cfg, proto):
        super().__init__(cfg, proto)
        self.count = cfg.get("count", 50)
        self._state = bytearray(self.count)  # local mirror, all off

    def set_one(self, led_id, value):
        if 1 <= led_id <= self.count:
            self._state[led_id - 1] = max(0, min(255, int(value)))
        # TODO: shift out

    def set_bulk(self, values, fmt):
        if fmt == "hex_pairs":
            n = min(self.count, len(values) // 2)
            for i in range(n):
                self._state[i] = int(values[i * 2: i * 2 + 2], 16)
        elif fmt == "mask":
            mask = int(values, 16) if isinstance(values, str) else int(values)
            for i in range(self.count):
                self._state[i] = 255 if (mask >> i) & 1 else 0
        # TODO: shift out

    def clear_all(self):
        for i in range(self.count):
            self._state[i] = 0
        # TODO: shift out


class CharLcd(_Base):
    """1602 character LCD via PCF8574 I2C backpack.

    TODO: instantiate adafruit_character_lcd.character_lcd_i2c. write_line()
    truncates to 16 chars and writes to row 0 or 1.
    """
    def write_line(self, line, text): pass
    def clear(self): pass


class OledBank(_Base):
    """Both SSD1306 OLEDs. Selects between panel B (0x3C) and master (0x3D)."""

    def __init__(self, cfg_b, cfg_master, proto):
        # The "enabled" flag here is OR of either display's enable.
        merged = {"enabled": cfg_b.get("enabled") or cfg_master.get("enabled")}
        super().__init__(merged, proto)
        self.cfg_b = cfg_b
        self.cfg_master = cfg_master

    def render(self, display, layout, data):
        # display: "B" or "MASTER"; layout: text|alert|status|icon|raw
        # TODO: instantiate adafruit_ssd1306; dispatch by layout.
        pass


class SfxBank(_Base):
    """CH358D K-pin pulser. Each GPIO drives a 2N3904 NPN.

    TODO: configure pins as DigitalInOut outputs, default LOW.
    trigger(slot, pulse_ms) drives the pin HIGH for pulse_ms then LOW.

    Note: pulse cannot block the main loop. The skeleton uses a small queue
    of (pin, end_ms) tuples that poll() services — non-blocking. trigger_seq
    enqueues `count` pulses spaced by interval_ms.
    """
    def __init__(self, cfg, proto):
        super().__init__(cfg, proto)
        self._queue = []  # list of (pin_index, end_ms)
        self._seq = []    # list of (slot, fire_at_ms, remaining)

    def trigger(self, slot, pulse_ms):
        # TODO: drive pin HIGH; enqueue end_ms = now + pulse_ms to drop it.
        pass

    def trigger_seq(self, slot, count, interval_ms):
        # TODO: enqueue `count` (slot, fire_at_ms) tuples spaced by interval.
        pass

    def poll(self, now_ms):
        # TODO: drop any expired pulses to LOW; fire any due sequence beats.
        pass
