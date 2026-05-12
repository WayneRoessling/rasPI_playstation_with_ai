# HAL Protocol — mini-ai overlay

The Pi 5 (AI brain) talks to a hardware controller using this protocol. The
controller is either:

- the **Adafruit Metro RP2040** running the CircuitPython firmware in
  `overlay/firmware/rp2040/`, or
- the **browser-based simulator** in `overlay/sim/`.

Both speak the same wire format. The Pi 5 cannot distinguish them, which is the
whole point — develop and validate scenarios against the simulator, then move
to real hardware without changing the Pi-side code.

The Arduino Nicla Voice (always-on wake/keyword detection) speaks a small
**subset** of this same protocol over a second USB-CDC link — see
[Nicla subset](#nicla-subset) below.

## 1. Transport

| Endpoint            | Transport          | Default settings                          |
|---------------------|--------------------|-------------------------------------------|
| RP2040 (real HW)    | USB CDC serial     | 115200 baud, 8N1, no flow control         |
| Browser simulator   | WebSocket          | text frames, `ws://localhost:8765/hal`    |
| Nicla Voice         | USB CDC serial     | 115200 baud, 8N1                          |

Both transports carry **JSON-lines**: one JSON object per line, terminated by
`\n` (LF, 0x0A). UTF-8 encoded. No literal newlines inside string values
(escape as `\n`).

## 2. Framing rules

- Each message is a single JSON object on one line.
- Malformed lines are silently dropped at the receiver, with one stderr log
  line at the receiver's discretion.
- Lines longer than **1024 bytes** are dropped. (LED bulk updates use a packed
  format that fits — see `leds` command.)
- Both sides emit messages asynchronously. There is no strict request/response
  lockstep; commands may carry an `id` so the controller can return a matching
  `ack`.

## 3. Common fields

| Field | Type   | Required | Purpose                                                |
|-------|--------|----------|--------------------------------------------------------|
| `t`   | string | yes      | Message type discriminator                             |
| `v`   | int    | no       | Schema version, default `1`                            |
| `id`  | int    | no       | Sender-assigned tracking ID (commands; ack echoes it)  |
| `ms`  | int    | no       | Sender monotonic milliseconds since boot (events)      |

Unknown fields are ignored — forward-compatibility is preserved this way.

## 4. Events (controller → Pi 5)

### 4.1 `hello`
Sent once at controller boot.
```json
{"t":"hello","fw":"0.1.0","caps":["switches","leds","lcd","oled","sfx","ptt","pir","key"],"ts":1234}
```
`caps` advertises which peripherals this controller actually drives. Pi 5
should not send commands for capabilities not listed.

### 4.2 `ready`
Controller has completed self-test and is ready for commands.
```json
{"t":"ready","ms":850}
```

### 4.3 `switch`
Toggle switch edge (id is 1..10, state is 0=open, 1=closed).
```json
{"t":"switch","id":3,"state":1,"ms":12345}
```

### 4.4 `ptt`
Push-to-talk button edge.
```json
{"t":"ptt","state":1,"ms":12350}
```

### 4.5 `pir`
PIR motion sensor edge.
```json
{"t":"pir","state":1,"ms":15000}
```

### 4.6 `key`
MT-301 isolator key position change. Defined positions: `"SAFE"`, `"ARM"`.
Additional positions reserved: `"OFF"`, `"RUN"`, `"TEST"`.
```json
{"t":"key","pos":"ARM","ms":20000}
```

### 4.7 `ack`
Acknowledgment of a previously issued command (matched by `of`).
```json
{"t":"ack","of":42,"ok":true}
{"t":"ack","of":43,"ok":false,"err":"slot out of range"}
```

### 4.8 `err`
Asynchronous error (not tied to a specific command).
```json
{"t":"err","code":"I2C_NACK","msg":"oled at 0x3D not responding"}
```

### 4.9 `heartbeat`
Periodic liveness signal — every 5 s by default.
```json
{"t":"heartbeat","ms":300000,"uptime_ms":300000}
```

## 5. Commands (Pi 5 → controller)

### 5.1 `led` — set a single LED
```json
{"t":"led","id":17,"v":255,"id_msg":42}
```
- `id` (int, 1..LED_COUNT): which LED.
- `v` (int, 0..255): brightness. Firmware with binary-only drivers (74HC595)
  treats `v >= 128` as ON, else OFF.

### 5.2 `leds` — set multiple LEDs in one frame
```json
{"t":"leds","values":"0F00FF...","format":"hex_pairs","id":43}
```
- `format`: `"hex_pairs"` — string of 2-hex-digit values, one per LED,
  ordered by LED id 1..N. So `"FF00"` means LED1=255, LED2=0.
- Alternatively, `"format":"mask","values":"0x000003FF"` to set the first 10
  LEDs on with binary on/off semantics.
- Use this instead of many `led` frames to stay within the 1024-byte line
  limit. 50 LEDs × 2 hex chars = 100 bytes — comfortable.

### 5.3 `lcd` — write a line to the 1602 character LCD
```json
{"t":"lcd","line":1,"text":"ALT 12000   FUEL 087","id":44}
```
- `line`: 1 or 2.
- `text`: truncated to 16 chars (no wrap).
- Use `{"t":"lcd_clear"}` to blank.

### 5.4 `oled` — render a layout on one of the OLED displays
```json
{"t":"oled","display":"B","layout":"alert","data":{"title":"BREACH","subtitle":"hull section 3"},"id":45}
```
- `display`: `"B"` (panel display 2) or `"MASTER"` (status display).
- `layout`: one of:
  - `"text"` — `data.lines` is array of strings, line-wrapped.
  - `"alert"` — `data.title` (large) + `data.subtitle` (small).
  - `"status"` — `data.scenario`, `data.arm` ("ARMED"|"SAFE"), `data.health`.
  - `"icon"` — `data.icon` is one of a named glyph set (`"warn"`,
    `"comms"`, `"check"`, `"x"`).
  - `"raw"` — `data.pixels` is a hex-encoded 1bpp 128×64 framebuffer (1024
    bytes hex = 2048 chars; exceeds line limit → chunked, see §6).
- Layouts are rendered by the controller. Pi 5 doesn't need to know fonts.

### 5.5 `sfx` — trigger a CH358 sound slot
```json
{"t":"sfx","slot":4,"pulse_ms":120,"id":46}
```
- `slot`: 1..10 (maps to CH358 K1..K10).
- `pulse_ms`: how long to hold the K-pin LOW (default 100). Tune per CH358
  variant.

### 5.6 `sfx_seq` — trigger a slot repeatedly (countdown ticks)
```json
{"t":"sfx_seq","slot":9,"count":5,"interval_ms":1000,"id":47}
```

### 5.7 `sync` — request a full state dump
```json
{"t":"sync","id":48}
```
Controller responds with an `ack` followed by one event per peripheral with
its current state.

### 5.8 `reset` — soft reset
```json
{"t":"reset","id":49}
```
Returns LEDs to off, displays to splash, then re-emits `hello`/`ready`.

## 6. Chunked OLED frames

For `oled` with `layout:"raw"`, the framebuffer is split into chunks of
≤512 hex chars:
```json
{"t":"oled","display":"B","layout":"raw","chunk":1,"of":4,"data":{"pixels":"..."},"id":50}
```
Receiver buffers chunks 1..of, renders on the final chunk.

## 7. Nicla subset

The Arduino Nicla Voice speaks a tiny event-only subset on its own USB-CDC
link. It does not consume commands.

### 7.1 `wake`
Wake-word detected.
```json
{"t":"wake","word":"computer","conf":0.92,"ms":50000}
```

### 7.2 `intent`
Short-command keyword classified (no Whisper round-trip needed).
```json
{"t":"intent","key":"abort","conf":0.87,"ms":50500}
```

### 7.3 `nicla_hello`
At boot, advertising the trained model.
```json
{"t":"nicla_hello","fw":"0.1.0","model":"sentinel-v1","keywords":["computer","captain","abort","launch","status","shields","fire","arm","disarm","help"]}
```

Pi 5 fuses `wake` and `intent` events with main-protocol events in its
event loop. The scenario layer decides whether to act on an intent
(see arm-gating in `canonical/tools.yaml`).

## 8. Reserved type values

| `t` value      | Direction | Notes                                  |
|----------------|-----------|----------------------------------------|
| `hello`        | C→P       | Boot greeting                          |
| `ready`        | C→P       | Self-test complete                     |
| `switch`       | C→P       | Toggle switch edge                     |
| `ptt`          | C→P       | Push-to-talk edge                      |
| `pir`          | C→P       | PIR motion edge                        |
| `key`          | C→P       | Key position change                    |
| `ack`          | C→P       | Command ack                            |
| `err`          | C→P       | Async error                            |
| `heartbeat`    | C→P       | Periodic liveness                      |
| `wake`         | N→P       | Nicla wake-word                        |
| `intent`       | N→P       | Nicla classified intent                |
| `nicla_hello`  | N→P       | Nicla boot                             |
| `led`          | P→C       | Single LED                             |
| `leds`         | P→C       | Bulk LED                               |
| `lcd`          | P→C       | 1602 line write                        |
| `lcd_clear`    | P→C       | 1602 clear                             |
| `oled`         | P→C       | OLED render                            |
| `sfx`          | P→C       | CH358 trigger                          |
| `sfx_seq`      | P→C       | CH358 repeated trigger                 |
| `sync`         | P→C       | State dump request                     |
| `reset`        | P→C       | Soft reset                             |

(C = hardware controller; P = Pi 5; N = Nicla Voice.)

## 9. Versioning

Breaking changes increment the top-level `v` field. Controllers reject
frames with `v` greater than they support and emit `err` with
`code:"VERSION"`. Adding new `t` values or new optional fields is
non-breaking.

## 10. Reference timings

| Operation                     | Target latency        |
|-------------------------------|-----------------------|
| Switch edge → Pi 5 event      | < 30 ms               |
| SFX command → audible sound   | < 60 ms               |
| LCD line update               | < 50 ms               |
| OLED layout render            | < 100 ms              |
| OLED raw framebuffer (4 chunks)| < 250 ms             |
| Bulk LED update (50 LEDs)     | < 40 ms               |

These are budgets, not guarantees. Validate against `tools/protocol_bench.py`
(future).
