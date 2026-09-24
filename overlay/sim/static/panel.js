// Browser panel for the mini-ai overlay simulator.
// Speaks the JSON-lines HAL protocol (overlay/docs/HAL_PROTOCOL.md).
//
// Architecture:
//   - one WebSocket to /hal, used both to emit "events" (when the user
//     interacts with virtual hardware) and to receive "commands" from
//     the Pi 5 (which we render onto the UI).
//   - state lives in plain objects; rendering is direct DOM mutation,
//     no framework.

const SWITCH_COUNT = 10;
const LED_COUNT = 50;
const SFX_COUNT = 10;
const OLED_W = 128;
const OLED_H = 64;
const CANVAS_SCALE = 2;

const SFX_ROLES = [
  "ack","deny","caution","alarm","arm",
  "disarm","comms","click","tick","status"
];

// ── DOM refs ──────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const switchRow = $("switch-row");
const sfxRow = $("sfx-row");
const ledGrid = $("led-grid");
const logEl = $("log");
const lcdEl = $("lcd");
const statusEl = $("status");
const wsUrlEl = $("ws-url");
const oledB = $("oled-b").getContext("2d");
const oledM = $("oled-master").getContext("2d");

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  switches: new Array(SWITCH_COUNT).fill(0),
  leds: new Array(LED_COUNT).fill(0),
  ptt: 0,
  pir: 0,
  key: "SAFE",
  lcd: ["                ", "                "],
  msgId: 1,
  bootMs: performance.now(),
};

function nowMs() {
  return Math.round(performance.now() - state.bootMs);
}

// ── WebSocket ─────────────────────────────────────────────────────────────
// Pass through ?token= from the page URL when the server requires HAL_SIM_TOKEN.
const simToken = new URLSearchParams(location.search).get("token");
const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/hal` +
  (simToken ? `?token=${encodeURIComponent(simToken)}` : "");
wsUrlEl.textContent = wsUrl;
let ws = null;

function setStatus(s) {
  statusEl.className = `status ${s}`;
  statusEl.textContent = s;
}

function connect() {
  setStatus("connecting");
  ws = new WebSocket(wsUrl);
  ws.addEventListener("open", () => {
    setStatus("connected");
    // Announce the simulator as a controller. The Pi side may already
    // be connected — it will treat us as the hardware.
    send({
      t: "hello",
      fw: "sim-0.1.0",
      caps: ["switches","ptt","pir","key","leds","lcd","oled","sfx"],
      ts: nowMs(),
    });
    send({ t: "ready", ms: nowMs() });
  });
  ws.addEventListener("close", () => {
    setStatus("disconnected");
    setTimeout(connect, 1000);
  });
  ws.addEventListener("error", () => setStatus("disconnected"));
  ws.addEventListener("message", (ev) => {
    for (const line of ev.data.split("\n")) {
      const s = line.trim();
      if (!s) continue;
      try {
        const msg = JSON.parse(s);
        logFrame("in", msg);
        handleCommand(msg);
      } catch (e) {
        logRaw("err", `bad json: ${s}`);
      }
    }
  });
}

function send(msg) {
  if (!msg.id && /^(led|leds|lcd|lcd_clear|oled|sfx|sfx_seq|sync|reset)$/.test(msg.t)) {
    // commands get an id; events don't need one
    msg.id = state.msgId++;
  }
  if (!msg.ms && /^(switch|ptt|pir|key)$/.test(msg.t)) {
    msg.ms = nowMs();
  }
  const line = JSON.stringify(msg);
  logFrame("out", msg);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(line);
  }
}

// ── Log ───────────────────────────────────────────────────────────────────
function logFrame(dir, msg) {
  const t = new Date().toLocaleTimeString();
  const arrow = dir === "in" ? "← " : "→ ";
  const span = document.createElement("span");
  span.className = dir;
  span.textContent = `${t}  ${arrow}${JSON.stringify(msg)}\n`;
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;
  // Cap log
  while (logEl.childNodes.length > 500) logEl.removeChild(logEl.firstChild);
}
function logRaw(cls, text) {
  const span = document.createElement("span");
  span.className = cls;
  span.textContent = text + "\n";
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;
}
$("clear-log").addEventListener("click", () => { logEl.innerHTML = ""; });

// ── Build UI ──────────────────────────────────────────────────────────────
function buildSwitches() {
  for (let i = 1; i <= SWITCH_COUNT; i++) {
    const el = document.createElement("div");
    el.className = "switch";
    el.dataset.id = i;
    el.innerHTML = `<div class="label">S${i}</div><div class="knob"></div>`;
    el.addEventListener("click", () => toggleSwitch(i));
    switchRow.appendChild(el);
  }
}

function buildSfx() {
  for (let i = 1; i <= SFX_COUNT; i++) {
    const el = document.createElement("div");
    el.className = "sfx-slot";
    el.dataset.slot = i;
    el.innerHTML = `<div class="slot-num">K${i}</div><div class="slot-role">${SFX_ROLES[i-1]}</div>`;
    sfxRow.appendChild(el);
  }
}

function buildLeds() {
  for (let i = 1; i <= LED_COUNT; i++) {
    const el = document.createElement("div");
    el.className = "led";
    el.dataset.id = i;
    el.title = `LED ${i}`;
    ledGrid.appendChild(el);
  }
}

// ── Event sources (user → Pi) ─────────────────────────────────────────────
function toggleSwitch(id) {
  const i = id - 1;
  state.switches[i] = state.switches[i] ? 0 : 1;
  switchRow.children[i].classList.toggle("on", !!state.switches[i]);
  send({ t: "switch", id, state: state.switches[i] });
}

function setPtt(on) {
  state.ptt = on ? 1 : 0;
  $("ptt").classList.toggle("active", !!state.ptt);
  send({ t: "ptt", state: state.ptt });
}
$("ptt").addEventListener("mousedown", () => setPtt(1));
$("ptt").addEventListener("mouseup",   () => setPtt(0));
$("ptt").addEventListener("mouseleave", () => state.ptt && setPtt(0));
$("ptt").addEventListener("touchstart", (e) => { e.preventDefault(); setPtt(1); });
$("ptt").addEventListener("touchend",   (e) => { e.preventDefault(); setPtt(0); });

$("pir").addEventListener("click", () => {
  state.pir = state.pir ? 0 : 1;
  $("pir").classList.toggle("active", !!state.pir);
  send({ t: "pir", state: state.pir });
});

$("key-pos").addEventListener("change", (e) => {
  state.key = e.target.value;
  send({ t: "key", pos: state.key });
});

// ── Command handlers (Pi → user) ──────────────────────────────────────────
function handleCommand(msg) {
  // Like the firmware, ack every command that carries a tracking id so the
  // Pi can't tell the simulator from real hardware. `led` uses `id` for the
  // LED number; its tracking id is `id_msg` (HAL_PROTOCOL.md §5.1).
  const trackingId = msg.t === "led" ? msg.id_msg : msg.id;
  const ack = (ok, err) => {
    if (trackingId === undefined || trackingId === null) return;
    send(err ? { t: "ack", of: trackingId, ok, err } : { t: "ack", of: trackingId, ok });
  };
  try {
    switch (msg.t) {
      case "led":       renderLedOne(msg.id, msg.v ?? 255); break;
      case "leds":      renderLedBulk(msg.values, msg.format || "hex_pairs"); break;
      case "lcd":       renderLcdLine(msg.line, msg.text || ""); break;
      case "lcd_clear": renderLcdLine(1, "                "); renderLcdLine(2, "                "); break;
      case "oled":      renderOled(msg.display, msg.layout, msg.data || {}); break;
      case "sfx":       fireSfx(msg.slot, msg.pulse_ms || 100); break;
      case "sfx_seq":   fireSfxSeq(msg.slot, msg.count || 1, msg.interval_ms || 1000); break;
      case "sync":      ack(true); emitSync(); return;   // spec: ack first, then the state dump
      case "reset":     doReset(); break;
      // events from the Pi side are echoed back — ignore quietly
      case "hello": case "ready": case "heartbeat":
      case "switch": case "ptt": case "pir": case "key":
      case "ack": case "err": case "wake": case "intent": case "nicla_hello":
        return;
      default:
        logRaw("err", `unknown command: ${msg.t}`);
        ack(false, `unknown type ${msg.t}`);
        return;
    }
    ack(true);
  } catch (e) {
    ack(false, String(e));
  }
}

function renderLedOne(id, v) {
  if (id < 1 || id > LED_COUNT) return;
  const on = v >= 128;
  state.leds[id - 1] = on ? 1 : 0;
  ledGrid.children[id - 1].classList.toggle("on", on);
}

function renderLedBulk(values, fmt) {
  if (fmt === "hex_pairs") {
    const n = Math.min(LED_COUNT, Math.floor(values.length / 2));
    for (let i = 0; i < n; i++) {
      const v = parseInt(values.substr(i * 2, 2), 16);
      const on = v >= 128;
      state.leds[i] = on ? 1 : 0;
      ledGrid.children[i].classList.toggle("on", on);
    }
  } else if (fmt === "mask") {
    const mask = BigInt(values);
    for (let i = 0; i < LED_COUNT; i++) {
      const on = (mask >> BigInt(i)) & 1n;
      state.leds[i] = on ? 1 : 0;
      ledGrid.children[i].classList.toggle("on", !!on);
    }
  }
}

function renderLcdLine(line, text) {
  const t = (text + "                ").slice(0, 16);
  if (line === 1 || line === 2) state.lcd[line - 1] = t;
  lcdEl.textContent = state.lcd.join("\n");
}

// ── OLED rendering ────────────────────────────────────────────────────────
function renderOled(display, layout, data) {
  const ctx = display === "MASTER" ? oledM : oledB;
  const W = OLED_W * CANVAS_SCALE;
  const H = OLED_H * CANVAS_SCALE;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#9ff5ff";
  ctx.imageSmoothingEnabled = false;

  switch (layout) {
    case "text":   drawText(ctx, data.lines || [], W, H); break;
    case "alert":  drawAlert(ctx, data.title || "", data.subtitle || "", W, H); break;
    case "status": drawStatus(ctx, data, W, H); break;
    case "icon":   drawIcon(ctx, data.icon || "", W, H); break;
    case "raw":    drawRaw(ctx, data.pixels || "", W, H); break;
    default:       drawText(ctx, [`[unknown layout: ${layout}]`], W, H);
  }
}
function drawText(ctx, lines, W, H) {
  ctx.font = `${10 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.textBaseline = "top";
  lines.slice(0, 6).forEach((s, i) => {
    ctx.fillText(String(s).slice(0, 21), 4, 4 + i * 11 * CANVAS_SCALE);
  });
}
function drawAlert(ctx, title, subtitle, W, H) {
  ctx.font = `bold ${18 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillStyle = "#ffb84c";
  ctx.fillText(title.slice(0, 12), W / 2, H / 2 - 8 * CANVAS_SCALE);
  ctx.font = `${10 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.fillStyle = "#9ff5ff";
  ctx.fillText(subtitle.slice(0, 21), W / 2, H / 2 + 14 * CANVAS_SCALE);
  ctx.textAlign = "start";
}
function drawStatus(ctx, data, W, H) {
  ctx.font = `bold ${12 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.textBaseline = "top";
  ctx.fillStyle = "#9ff5ff";
  ctx.fillText((data.scenario || "—").slice(0, 21), 4, 4);
  ctx.font = `${10 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.fillStyle = data.arm === "ARMED" ? "#ff4c4c" : "#4cff9d";
  ctx.fillText(data.arm || "SAFE", 4, 4 + 16 * CANVAS_SCALE);
  ctx.fillStyle = "#9ff5ff";
  ctx.fillText(`HEALTH: ${data.health || "OK"}`, 4, 4 + 30 * CANVAS_SCALE);
}
function drawIcon(ctx, icon, W, H) {
  const glyph = ({ warn:"!", comms:"≈", check:"✓", x:"X" })[icon] || "?";
  ctx.font = `bold ${40 * CANVAS_SCALE}px ui-monospace, monospace`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(glyph, W / 2, H / 2);
  ctx.textAlign = "start";
}
function drawRaw(ctx, hex, W, H) {
  // 128*64 / 8 = 1024 bytes = 2048 hex chars
  if (hex.length < 2048) {
    drawText(ctx, ["[partial raw frame]"], W, H);
    return;
  }
  const img = ctx.createImageData(OLED_W, OLED_H);
  for (let i = 0; i < OLED_W * OLED_H; i++) {
    const byte = parseInt(hex.substr((i >> 3) * 2, 2), 16);
    const bit = (byte >> (i & 7)) & 1;
    const o = i * 4;
    img.data[o] = bit ? 159 : 0;
    img.data[o + 1] = bit ? 245 : 0;
    img.data[o + 2] = bit ? 255 : 0;
    img.data[o + 3] = 255;
  }
  // Scale up by CANVAS_SCALE
  const off = document.createElement("canvas");
  off.width = OLED_W; off.height = OLED_H;
  off.getContext("2d").putImageData(img, 0, 0);
  ctx.drawImage(off, 0, 0, W, H);
}

// ── SFX ───────────────────────────────────────────────────────────────────
function fireSfx(slot, pulseMs) {
  if (slot < 1 || slot > SFX_COUNT) return;
  const el = sfxRow.children[slot - 1];
  el.classList.add("fired");
  setTimeout(() => el.classList.remove("fired"), Math.max(120, pulseMs));
  // Try to play preview WAV if it's been generated
  const url = `/sfx/${String(slot).padStart(2, "0")}.wav`;
  const audio = new Audio(url);
  audio.volume = 0.5;
  audio.play().catch(() => {/* missing wav is fine */});
}
function fireSfxSeq(slot, count, intervalMs) {
  for (let i = 0; i < count; i++) {
    setTimeout(() => fireSfx(slot, 100), i * intervalMs);
  }
}

// ── Misc ──────────────────────────────────────────────────────────────────
function emitSync() {
  // Reply with the current state of all input peripherals
  state.switches.forEach((s, i) => send({ t: "switch", id: i + 1, state: s }));
  send({ t: "ptt", state: state.ptt });
  send({ t: "pir", state: state.pir });
  send({ t: "key", pos: state.key });
}
function doReset() {
  state.leds.fill(0);
  Array.from(ledGrid.children).forEach((el) => el.classList.remove("on"));
  state.lcd = ["                ", "                "];
  lcdEl.textContent = state.lcd.join("\n");
  oledB.fillStyle = "#000"; oledB.fillRect(0, 0, OLED_W * CANVAS_SCALE, OLED_H * CANVAS_SCALE);
  oledM.fillStyle = "#000"; oledM.fillRect(0, 0, OLED_W * CANVAS_SCALE, OLED_H * CANVAS_SCALE);
}

// ── Boot ──────────────────────────────────────────────────────────────────
buildSwitches();
buildSfx();
buildLeds();
doReset();
connect();
