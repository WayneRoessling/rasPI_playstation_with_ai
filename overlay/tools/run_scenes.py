"""Drop 7 — scripted scene validation harness.

Loads scene YAML files from ``overlay/scenes/`` (or any explicit path),
drives them against a running simulator + scenario runtime, and reports
pass/fail per step + per scene. The behavioural complement to
``overlay/tools/validate_canonical.py`` (which is the static checker).

Scenes describe an authored sequence of stimuli (events / utterances)
plus the expected hardware effects. Two execution modes:

* ``llm``  — uses Ollama via ``scenario.llm.run_turn``. Realistic but
  slow and needs a tool-capable model running locally.
* ``mock`` — the scene includes ``scripted_tool_calls`` mapping each
  utterance to the tool calls a mock LLM would emit. The runner
  dispatches those directly through ``ScenarioRuntime.dispatch_tool``.
  Fast, deterministic, CI-friendly.

Usage::

    python overlay/tools/run_scenes.py overlay/scenes/examples/test_console_smoke.yaml
    python overlay/tools/run_scenes.py --all
    python overlay/tools/run_scenes.py --all --mode mock
    python overlay/tools/run_scenes.py scene.yaml -v
    python overlay/tools/run_scenes.py --all --json

Exit code 0 on all pass, 1 on any failure, 2 on load/schema errors.

Both the runner and the in-process HAL client connect to the simulator
WebSocket; the runner uses its own WebSocket connection purely to
inject ``switch``/``key``/``ptt``/``pir``/``wake``/``intent`` events.
The simulator broadcasts each frame to every *other* client, so events
sent by the runner arrive at the HAL state mirror unchanged.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml required: pip install pyyaml\n")
    sys.exit(2)

try:
    from overlay.pi5_hal.client import HalClient
    from overlay.pi5_hal.transport import WebsocketTransport
    from overlay.scenario.runtime import ScenarioRuntime
    from overlay.scenario.llm import run_turn, DEFAULT_MODEL, OLLAMA_DEFAULT_URL
    from overlay.scenario.demo import SCENARIOS
except ImportError:  # pragma: no cover — direct-script invocation fallback
    HERE = Path(__file__).resolve()
    sys.path.insert(0, str(HERE.parent.parent.parent))
    from overlay.pi5_hal.client import HalClient  # type: ignore  # noqa: E402
    from overlay.pi5_hal.transport import WebsocketTransport  # type: ignore  # noqa: E402
    from overlay.scenario.runtime import ScenarioRuntime  # type: ignore  # noqa: E402
    from overlay.scenario.llm import run_turn, DEFAULT_MODEL, OLLAMA_DEFAULT_URL  # type: ignore  # noqa: E402
    from overlay.scenario.demo import SCENARIOS  # type: ignore  # noqa: E402


log = logging.getLogger("run_scenes")

SCENES_ROOT = Path(__file__).resolve().parent.parent / "scenes"
EXAMPLES_DIR = SCENES_ROOT / "examples"

VALID_KEY_POSITIONS = {"SAFE", "ARM", "OFF", "RUN", "TEST"}
VALID_STEP_TYPES = {"event", "utterance", "wait", "assert"}
VALID_ASSERTIONS = {
    "tool_calls_include", "tool_calls_exclude", "tool_call_count",
    "reply_matches", "leds_on", "leds_changed",
    "lcd_line_1", "lcd_line_2",
}
# Anything under `state.<field>` is allowed too — checked dynamically.


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass
class StepResult:
    index: int
    type: str
    summary: str
    failures: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    commands: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


@dataclass
class SceneResult:
    name: str
    path: str
    mode: str
    scenario: str
    steps: list[StepResult] = field(default_factory=list)
    load_error: Optional[str] = None
    runtime_error: Optional[str] = None

    @property
    def ok(self) -> bool:
        if self.load_error or self.runtime_error:
            return False
        return all(s.ok for s in self.steps)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "mode": self.mode,
            "scenario": self.scenario,
            "ok": self.ok,
            "load_error": self.load_error,
            "runtime_error": self.runtime_error,
            "steps": [dataclasses.asdict(s) for s in self.steps],
        }


# ── Schema validation ───────────────────────────────────────────────────────


def _validate_scene(data: dict, src: Path) -> list[str]:
    """Return a list of human-readable errors. Empty = valid."""
    errs: list[str] = []
    if not isinstance(data, dict):
        return [f"{src}: top-level must be a mapping"]
    for required in ("name", "scenario", "steps"):
        if required not in data:
            errs.append(f"{src}: missing required key {required!r}")
    scenario = data.get("scenario")
    if scenario is not None and scenario not in SCENARIOS:
        errs.append(
            f"{src}: scenario {scenario!r} unknown "
            f"(valid: {sorted(SCENARIOS.keys())})"
        )
    mode = data.get("mode", "llm")
    if mode not in ("llm", "mock"):
        errs.append(f"{src}: mode must be 'llm' or 'mock', got {mode!r}")

    setup = data.get("setup") or {}
    if not isinstance(setup, dict):
        errs.append(f"{src}: setup must be a mapping")
    else:
        key = setup.get("key")
        if key is not None and key not in VALID_KEY_POSITIONS:
            errs.append(
                f"{src}: setup.key must be one of {sorted(VALID_KEY_POSITIONS)}, "
                f"got {key!r}"
            )
        switches = setup.get("switches") or {}
        if not isinstance(switches, dict):
            errs.append(f"{src}: setup.switches must be a mapping")
        else:
            for k, v in switches.items():
                try:
                    i = int(k)
                except (TypeError, ValueError):
                    errs.append(f"{src}: setup.switches key {k!r} must be 1..10")
                    continue
                if not 1 <= i <= 10:
                    errs.append(f"{src}: setup.switches key {i} out of range 1..10")
                if not isinstance(v, (bool, int, str)):
                    errs.append(
                        f"{src}: setup.switches[{i}] must be bool/int/str, "
                        f"got {type(v).__name__}"
                    )

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        errs.append(f"{src}: steps must be a non-empty list")
        return errs

    for idx, step in enumerate(steps, start=1):
        where = f"{src}: step[{idx}]"
        if not isinstance(step, dict):
            errs.append(f"{where}: step must be a mapping")
            continue
        kind = _classify_step(step)
        if kind is None:
            errs.append(
                f"{where}: must declare exactly one of {sorted(VALID_STEP_TYPES)}"
            )
            continue
        expect = step.get("expect") or {}
        if not isinstance(expect, dict):
            errs.append(f"{where}: expect must be a mapping")
            continue
        for key in expect:
            base = key.split(".", 1)[0]
            if key in VALID_ASSERTIONS or base == "state":
                continue
            errs.append(f"{where}: unknown assertion {key!r}")

    if mode == "mock":
        scripted = data.get("scripted_tool_calls") or {}
        if not isinstance(scripted, dict):
            errs.append(f"{src}: scripted_tool_calls must be a mapping (utterance -> [tool_calls])")
        else:
            for utt, calls in scripted.items():
                if not isinstance(calls, list):
                    errs.append(
                        f"{src}: scripted_tool_calls[{utt!r}] must be a list of tool-call dicts"
                    )
                    continue
                for j, c in enumerate(calls):
                    if not isinstance(c, dict) or "name" not in c:
                        errs.append(
                            f"{src}: scripted_tool_calls[{utt!r}][{j}] must be "
                            f"{{name: str, args: dict}}"
                        )
    return errs


def _classify_step(step: dict) -> Optional[str]:
    keys_present = [k for k in VALID_STEP_TYPES if k in step]
    if len(keys_present) != 1:
        return None
    return keys_present[0]


# ── Event injection ─────────────────────────────────────────────────────────


class Injector:
    """Second WebSocket connection used to broadcast events into the sim.

    The sim relays each frame to every *other* client, so a frame sent
    via this connection lands at the HalClient that the runner spun up.
    Kept separate from the HalClient transport so its rx loop doesn't
    swallow our own events.
    """

    def __init__(self, url: str):
        self.url = url
        self.ws = None

    def connect(self, timeout: float = 5.0) -> None:
        try:
            from websocket import create_connection  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "websocket-client required: pip install websocket-client"
            ) from e
        self.ws = create_connection(self.url, timeout=timeout)

    def send(self, frame: dict) -> None:
        if self.ws is None:
            raise RuntimeError("injector not connected")
        # Add a coarse timestamp so the sim UI can log the frame coherently
        frame.setdefault("ms", int(time.monotonic() * 1000))
        self.ws.send(json.dumps(frame))

    def close(self) -> None:
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None


# ── Setup application ───────────────────────────────────────────────────────


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("on", "true", "1", "yes", "closed")
    return bool(v)


def _apply_setup(injector: Injector, hal: HalClient, setup: dict, *,
                 wait_timeout: float = 2.0) -> None:
    """Inject events to bring the panel into the scene's initial state.

    Reaches the desired state by injecting only the *deltas* relative to
    the current HAL state mirror — runs after a fresh ``hal.connect()``
    so the mirror starts at zeros / SAFE. Blocks on each injected event
    via ``wait_for_event`` so the mirror is guaranteed up-to-date before
    the first step runs.
    """
    state = hal.state()

    # Key first — many tools are arm-gated, and we want the arm transition
    # to happen before we toggle switches that the scenario will care about.
    desired_key = setup.get("key")
    if desired_key is not None and desired_key != state["key"]:
        injector.send({"t": "key", "pos": desired_key})
        hal.wait_for_event(type_filter="key", timeout=wait_timeout)

    switches = setup.get("switches") or {}
    for k, v in switches.items():
        sid = int(k)
        want = _to_bool(v)
        current = bool(state["switches"][sid - 1])
        if want != current:
            injector.send({"t": "switch", "id": sid, "state": 1 if want else 0})
            hal.wait_for_event(type_filter="switch", timeout=wait_timeout)

    # PTT, PIR — optional, rarely used in setup but supported for completeness.
    if "ptt" in setup:
        injector.send({"t": "ptt", "state": 1 if _to_bool(setup["ptt"]) else 0})
        hal.wait_for_event(type_filter="ptt", timeout=wait_timeout)
    if "pir" in setup:
        injector.send({"t": "pir", "state": 1 if _to_bool(setup["pir"]) else 0})
        hal.wait_for_event(type_filter="pir", timeout=wait_timeout)

    # Small settle for any tail propagation.
    time.sleep(0.05)


# ── Step execution + assertion eval ─────────────────────────────────────────


def _normalise_args(args: Any) -> dict:
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    return {}


def _exec_event_step(injector: Injector, hal: HalClient, step: dict, *,
                     wait_timeout: float = 2.0) -> None:
    """Inject an event and block until the HalClient has ingested it.

    Without the explicit wait_for_event call, the HalClient's rx polling
    cycle (transport.recv_line(timeout=0.5)) can lag by up to half a
    second behind the injection — long enough that an `assert` step
    immediately after the event would race the state mirror update.
    """
    ev = step["event"] or {}
    if not isinstance(ev, dict) or "t" not in ev:
        raise ValueError(f"event step requires a mapping with `t`: got {ev!r}")
    type_ = str(ev["t"])
    injector.send(dict(ev))
    # Block until the same event type is dispatched into the state mirror.
    # The wait_for_event call drains the queue, so it is OK if other
    # events are pending — we only care that ours has arrived.
    got = hal.wait_for_event(type_filter=type_, timeout=wait_timeout)
    if got is None:
        log.warning("event %s did not echo back within %.1fs", type_, wait_timeout)
    # Small grace period for any dependent state propagation (e.g. switch
    # changes that the scenario tool might read mid-step).
    time.sleep(0.05)


def _exec_utterance_step_llm(runtime: ScenarioRuntime, step: dict, scene: dict,
                              tool_call_capture: list, *,
                              model: str, ollama_url: str,
                              history: list, timeout: float) -> tuple[str, list]:
    def observer(name, args, result):
        tool_call_capture.append({
            "name": name, "args": _normalise_args(args), "result": result,
        })
    speech, history = run_turn(
        runtime,
        str(step["utterance"]),
        model=model,
        ollama_url=ollama_url,
        history=history,
        on_tool_call=observer,
        timeout=timeout,
    )
    return speech, history


def _exec_utterance_step_mock(runtime: ScenarioRuntime, step: dict, scene: dict,
                               tool_call_capture: list) -> str:
    utt = str(step["utterance"])
    scripted = (scene.get("scripted_tool_calls") or {}).get(utt)
    if scripted is None:
        raise ValueError(
            f"mock mode: no scripted_tool_calls entry for utterance {utt!r}"
        )
    for tc in scripted:
        name = tc["name"]
        args = _normalise_args(tc.get("args"))
        result = runtime.dispatch_tool(name, args)
        tool_call_capture.append({"name": name, "args": args, "result": result})
    # Reply text is a courtesy field — assertions may regex-match it
    return str((scene.get("scripted_replies") or {}).get(utt, ""))


def _matches_call(actual: dict, expected: dict) -> bool:
    """Match an actual {name, args, result} against an expected pattern.

    Expected is a dict with at least `name`. Optional `args_contain` is a
    sub-mapping every entry of which must equal the matching field in
    the actual call's args. Optional `result_matches` is a regex on the
    runtime's tool result string.
    """
    if actual.get("name") != expected.get("name"):
        return False
    args_contain = expected.get("args_contain") or {}
    if args_contain:
        actual_args = actual.get("args") or {}
        for k, v in args_contain.items():
            if actual_args.get(k) != v:
                return False
    result_re = expected.get("result_matches")
    if result_re is not None:
        if not re.search(result_re, str(actual.get("result", ""))):
            return False
    return True


def _eval_assertions(expect: dict, *, tool_calls: list, reply: str,
                     leds_before: list[int], hal: HalClient) -> list[str]:
    """Return a list of human-readable assertion failures (empty = pass)."""
    failures: list[str] = []
    leds_after = hal.leds_mirror()

    if "tool_calls_include" in expect:
        for pat in expect["tool_calls_include"]:
            if not isinstance(pat, dict) or "name" not in pat:
                failures.append(
                    f"tool_calls_include entry {pat!r} malformed (need {{name: …}})"
                )
                continue
            if not any(_matches_call(c, pat) for c in tool_calls):
                failures.append(
                    f"tool_calls_include: no call matched {pat!r}; "
                    f"actual calls: {[c['name'] for c in tool_calls]}"
                )

    if "tool_calls_exclude" in expect:
        for pat in expect["tool_calls_exclude"]:
            if not isinstance(pat, dict) or "name" not in pat:
                failures.append(
                    f"tool_calls_exclude entry {pat!r} malformed (need {{name: …}})"
                )
                continue
            if any(_matches_call(c, pat) for c in tool_calls):
                failures.append(
                    f"tool_calls_exclude: forbidden call matched {pat!r}"
                )

    if "tool_call_count" in expect:
        want = int(expect["tool_call_count"])
        got = len(tool_calls)
        if got != want:
            failures.append(f"tool_call_count: want {want}, got {got}")

    if "reply_matches" in expect:
        pat = str(expect["reply_matches"])
        if not re.search(pat, reply or ""):
            failures.append(
                f"reply_matches: pattern {pat!r} did not match reply {reply!r}"
            )

    if "leds_on" in expect:
        want = sorted(int(i) for i in expect["leds_on"])
        got = sorted(i + 1 for i, v in enumerate(leds_after) if v)
        if got != want:
            failures.append(f"leds_on: want {want}, got {got}")

    if "leds_changed" in expect:
        want = sorted(int(i) for i in expect["leds_changed"])
        changed = sorted(
            i + 1
            for i in range(len(leds_after))
            if leds_after[i] != (leds_before[i] if i < len(leds_before) else 0)
        )
        # leds_changed=[] means "no LEDs changed" — strict match.
        if changed != want:
            failures.append(f"leds_changed: want {want}, got {changed}")

    lcd = hal.lcd_lines()
    for line_num in (1, 2):
        key = f"lcd_line_{line_num}"
        if key in expect:
            want = str(expect[key])
            got = lcd.get(line_num, "")
            if got != want:
                failures.append(f"{key}: want {want!r}, got {got!r}")

    state = hal.state()
    for key, want in expect.items():
        if not key.startswith("state."):
            continue
        field = key[len("state."):]
        got = _resolve_state_field(state, field)
        if got != want:
            failures.append(f"{key}: want {want!r}, got {got!r}")

    return failures


def _resolve_state_field(state: dict, field: str) -> Any:
    """Dot-path resolution for state.<field> assertions."""
    parts = field.split(".")
    cur: Any = state
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


# ── Per-scene driver ────────────────────────────────────────────────────────


def _run_scene(path: Path, *, mode_override: Optional[str], sim_url: str,
                model: str, ollama_url: str, verbose: bool,
                timeout: float) -> SceneResult:
    raw_text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        return SceneResult(
            name=path.stem, path=str(path), mode="?", scenario="?",
            load_error=f"yaml parse error: {exc}",
        )

    errs = _validate_scene(data, path)
    if errs:
        return SceneResult(
            name=str(data.get("name") or path.stem),
            path=str(path), mode=str(data.get("mode") or "?"),
            scenario=str(data.get("scenario") or "?"),
            load_error="; ".join(errs),
        )

    mode = mode_override or str(data.get("mode") or "llm")
    scenario_id = str(data["scenario"])
    name = str(data["name"])
    result = SceneResult(name=name, path=str(path),
                         mode=mode, scenario=scenario_id)

    scenario = SCENARIOS[scenario_id]

    # Generous WebSocket recv timeout — the default 5 s is fine for the
    # demo (each user utterance produces frames within a second) but a
    # multi-step scene with 10-15 s LLM turns can easily go that long
    # without any inbound frame, tripping the socket timeout and tearing
    # the rx loop down. 300 s comfortably covers an end-to-end scene.
    hal = HalClient(WebsocketTransport(sim_url, recv_timeout=300.0))
    injector = Injector(sim_url)
    try:
        hal.connect()
        injector.connect()
    except Exception as exc:
        result.runtime_error = f"failed to connect to {sim_url}: {exc!r}"
        try:
            hal.disconnect()
        except Exception:
            pass
        injector.close()
        return result

    # Always reset before applying setup so previous scenes can't leak
    # state into this one. The sim broadcasts the reset to every client
    # (including the panel UI) so the user can see scenes transitioning.
    try:
        try:
            hal.reset()
            time.sleep(0.25)
            hal.clear_leds()
            hal.clear_lcd()
            time.sleep(0.1)
        except Exception as exc:
            log.warning("pre-scene reset raised: %r", exc)

        setup = data.get("setup") or {}
        _apply_setup(injector, hal, setup)

        runtime = ScenarioRuntime(hal, scenario)
        history: list = []

        for idx, step in enumerate(data["steps"], start=1):
            kind = _classify_step(step) or "?"
            expect = step.get("expect") or {}
            tool_calls: list[dict] = []
            reply = ""

            leds_before = hal.leds_mirror()
            hal.start_recording()
            t0 = time.monotonic()

            summary = ""
            failures: list[str] = []
            try:
                if kind == "event":
                    _exec_event_step(injector, hal, step)
                    summary = f"event {step['event']!r}"
                elif kind == "wait":
                    ms = int(step["wait"])
                    time.sleep(max(0.0, ms) / 1000.0)
                    summary = f"wait {ms}ms"
                elif kind == "utterance":
                    if mode == "llm":
                        reply, history = _exec_utterance_step_llm(
                            runtime, step, data, tool_calls,
                            model=model, ollama_url=ollama_url,
                            history=history, timeout=timeout,
                        )
                    else:
                        reply = _exec_utterance_step_mock(
                            runtime, step, data, tool_calls
                        )
                    summary = f"utterance {step['utterance']!r}"
                elif kind == "assert":
                    summary = "assert (no stimulus)"
                else:
                    failures.append(f"unknown step kind {kind!r}")
            except Exception as exc:
                failures.append(f"step raised: {exc!r}")

            dt = time.monotonic() - t0
            commands = hal.pop_recording()

            failures += _eval_assertions(
                expect,
                tool_calls=tool_calls,
                reply=reply,
                leds_before=leds_before,
                hal=hal,
            )

            sr = StepResult(
                index=idx, type=kind,
                summary=f"{summary} ({dt:.2f}s)",
                failures=failures,
                tool_calls=tool_calls,
                commands=commands,
            )
            result.steps.append(sr)
            if verbose:
                _print_step_detail(sr, reply=reply)

            if failures and not verbose:
                # Surface the first failure right away even in non-verbose
                # mode so the operator gets feedback while LLM mode runs.
                print(f"   step {idx} [{kind}] FAIL: {failures[0]}",
                      file=sys.stderr)

    except Exception as exc:
        result.runtime_error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            hal.disconnect()
        except Exception:
            pass
        injector.close()

    return result


def _print_step_detail(sr: StepResult, *, reply: str = "") -> None:
    flag = "PASS" if sr.ok else "FAIL"
    print(f"   step {sr.index} [{sr.type}] {flag}: {sr.summary}", file=sys.stderr)
    if reply:
        print(f"      reply: {reply!r}", file=sys.stderr)
    for c in sr.tool_calls:
        print(f"      ▸ {c['name']}({json.dumps(c['args'])}) -> {c['result']!r}",
              file=sys.stderr)
    for f in sr.failures:
        print(f"      ✗ {f}", file=sys.stderr)


# ── Entry point ─────────────────────────────────────────────────────────────


def _discover_scenes(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for r in roots:
        if r.is_dir():
            out.extend(sorted(p for p in r.rglob("*.yaml") if p.is_file()))
        elif r.is_file():
            out.append(r)
    # Stable order: by relative path
    return sorted(set(out), key=lambda p: str(p))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("scene", nargs="?",
                    help="path to a scene YAML; omit with --all")
    ap.add_argument("--all", action="store_true",
                    help="run every scene under overlay/scenes/examples/")
    ap.add_argument("--mode", choices=["llm", "mock"], default=None,
                    help="override per-scene mode (default: each scene's own)")
    ap.add_argument("--sim", default="ws://127.0.0.1:8765/hal",
                    help="simulator WebSocket URL")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="Ollama model name (LLM mode only)")
    ap.add_argument("--ollama", default=OLLAMA_DEFAULT_URL,
                    help="Ollama base URL")
    ap.add_argument("--llm-timeout", type=float, default=180.0,
                    help="per-turn Ollama HTTP timeout (seconds)")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON summary on stdout")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print every step + every tool call")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )

    if not args.scene and not args.all:
        ap.error("provide a scene path or pass --all")

    scenes: list[Path] = []
    if args.all:
        scenes = _discover_scenes([EXAMPLES_DIR])
    if args.scene:
        scenes.append(Path(args.scene))
    if not scenes:
        print("no scenes found", file=sys.stderr)
        return 2

    results: list[SceneResult] = []
    overall_t0 = time.monotonic()
    for path in scenes:
        print(f"\n[scene] {path}", file=sys.stderr)
        res = _run_scene(
            path,
            mode_override=args.mode,
            sim_url=args.sim,
            model=args.model,
            ollama_url=args.ollama,
            verbose=args.verbose,
            timeout=args.llm_timeout,
        )
        results.append(res)
        flag = "PASS" if res.ok else "FAIL"
        if res.load_error:
            print(f"  {flag}: {res.load_error}", file=sys.stderr)
        elif res.runtime_error:
            print(f"  {flag}: runtime error: {res.runtime_error}", file=sys.stderr)
        else:
            n_steps = len(res.steps)
            n_fail = sum(1 for s in res.steps if not s.ok)
            print(f"  {flag}: {n_steps - n_fail}/{n_steps} steps "
                  f"(scenario={res.scenario}, mode={res.mode})",
                  file=sys.stderr)
    overall_dt = time.monotonic() - overall_t0

    n_pass = sum(1 for r in results if r.ok)
    n_fail = len(results) - n_pass

    if args.json:
        payload = {
            "scenes": [r.to_dict() for r in results],
            "summary": {"pass": n_pass, "fail": n_fail,
                        "total": len(results),
                        "duration_s": round(overall_dt, 2)},
        }
        print(json.dumps(payload, indent=2))

    print(file=sys.stderr)
    print(f"[summary] {n_pass}/{len(results)} scenes passed "
          f"({n_fail} failed) in {overall_dt:.1f}s",
          file=sys.stderr)
    if n_fail:
        print("[summary] failed scenes:", file=sys.stderr)
        for r in results:
            if not r.ok:
                why = r.load_error or r.runtime_error or (
                    f"{sum(1 for s in r.steps if not s.ok)} step(s) failed"
                )
                print(f"   - {r.name} ({r.path}): {why}", file=sys.stderr)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
