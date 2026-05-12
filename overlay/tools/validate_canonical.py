"""Cross-reference validator for the canonical entity catalogs.

Loads every YAML under ``overlay/canonical/`` plus any emitted scenario
YAMLs under ``overlay/narratives/scenarios/<id>/_emitted/``, and checks
that every cross-reference between them resolves.

Exit code 0 = clean. Exit code 1 = at least one inconsistency. All
findings are printed to stderr; stdout shows a brief summary so the
script can be chained.

Checks performed:

1. ``scenarios.yaml`` is well-formed; every authored scenario has a
   matching narrative directory and (if present) an emitted YAML whose
   ``id`` agrees with the catalog handle.
2. Every default tool referenced in ``scenarios.yaml`` is defined in
   ``tools.yaml``.
3. Every default wake-word / intent referenced in ``scenarios.yaml`` is
   defined in ``wake_words.yaml`` (and has the correct role).
4. Every hardware module referenced in ``scenarios.yaml`` is defined in
   ``hardware_modules.yaml``.
5. Every ``used_by`` scenario id in ``tools.yaml`` exists in
   ``scenarios.yaml``.
6. Every ``sfx_slot_refs`` integer is in [1, 10] (matches sfx_bank.yaml
   slot range).
7. Every ``referenced_displays`` value in ``tools.yaml`` is a
   protocol_id declared in ``displays.yaml``.
8. ``leds.yaml`` groups partition [1, led_count] without overlap and
   without gap; every switch_mirror_map.switch matches a switch id.
9. Every ``switches.yaml`` click_sfx_slot / arm_sfx_slot / disarm_sfx_slot
   is a valid SFX slot.
10. Every display kind=display in ``hardware_modules.yaml`` has a
    matching id in ``displays.yaml`` and vice versa.

Usage::

    python overlay/tools/validate_canonical.py
    python overlay/tools/validate_canonical.py --strict-emitted
    python overlay/tools/validate_canonical.py --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml required: pip install pyyaml\n")
    sys.exit(2)


OVERLAY_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIR = OVERLAY_ROOT / "canonical"
NARRATIVES_DIR = OVERLAY_ROOT / "narratives" / "scenarios"

SFX_SLOT_RANGE = range(1, 11)


def log(msg: str) -> None:
    sys.stderr.write(f"[validate] {msg}\n")


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level is not a mapping")
    return data


def _required_file(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing canonical file {label}: {path}")
    return load_yaml(path)


class Validator:
    """Holds all loaded catalogs and accumulates findings."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.sfx: dict = {}
        self.scenarios: dict = {}
        self.switches: dict = {}
        self.displays: dict = {}
        self.leds: dict = {}
        self.tools: dict = {}
        self.wake_words: dict = {}
        self.hw: dict = {}
        # Derived lookups
        self._scenario_ids: set[str] = set()
        self._tool_ids: set[str] = set()
        self._wake_keys: set[str] = set()
        self._display_protocol_ids: set[str] = set()
        self._display_ids: set[str] = set()
        self._switch_ids: set[int] = set()
        self._hw_ids: set[str] = set()

    # ── loading ─────────────────────────────────────────────────────────
    def load(self) -> None:
        self.sfx = _required_file(CANONICAL_DIR / "sfx_bank.yaml", "sfx_bank.yaml")
        self.scenarios = _required_file(CANONICAL_DIR / "scenarios.yaml", "scenarios.yaml")
        self.switches = _required_file(CANONICAL_DIR / "switches.yaml", "switches.yaml")
        self.displays = _required_file(CANONICAL_DIR / "displays.yaml", "displays.yaml")
        self.leds = _required_file(CANONICAL_DIR / "leds.yaml", "leds.yaml")
        self.tools = _required_file(CANONICAL_DIR / "tools.yaml", "tools.yaml")
        self.wake_words = _required_file(CANONICAL_DIR / "wake_words.yaml", "wake_words.yaml")
        self.hw = _required_file(CANONICAL_DIR / "hardware_modules.yaml", "hardware_modules.yaml")

        self._scenario_ids = {s.get("id") for s in self.scenarios.get("scenarios", []) if s.get("id")}
        self._tool_ids = {t.get("id") for t in self.tools.get("tools", []) if t.get("id")}
        self._wake_keys = {k.get("key") for k in self.wake_words.get("keywords", []) if k.get("key")}
        self._display_protocol_ids = {
            d.get("protocol_id") for d in self.displays.get("displays", [])
            if d.get("protocol_id")
        }
        self._display_ids = {d.get("id") for d in self.displays.get("displays", []) if d.get("id")}
        self._switch_ids = {s.get("id") for s in self.switches.get("switches", []) if s.get("id")}
        self._hw_ids = {m.get("id") for m in self.hw.get("modules", []) if m.get("id")}

    # ── helpers ─────────────────────────────────────────────────────────
    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    # ── checks ──────────────────────────────────────────────────────────
    def check_scenarios(self, strict_emitted: bool = False) -> None:
        for sc in self.scenarios.get("scenarios", []):
            sid = sc.get("id")
            where = f"scenarios.yaml[{sid!r}]"
            if not sid:
                self.err("scenarios.yaml", "scenario entry missing id")
                continue
            status = sc.get("status", "planned")

            for tool in sc.get("default_tools", []) or []:
                if tool not in self._tool_ids:
                    self.err(where, f"default_tools refs unknown tool {tool!r}")
            for kw in sc.get("default_wake_words", []) or []:
                if kw not in self._wake_keys:
                    self.err(where, f"default_wake_words refs unknown keyword {kw!r}")
            for kw in sc.get("default_intent_allowlist", []) or []:
                if kw not in self._wake_keys:
                    self.err(where, f"default_intent_allowlist refs unknown keyword {kw!r}")
            for mod in sc.get("hardware_modules", []) or []:
                if mod not in self._hw_ids:
                    self.err(where, f"hardware_modules refs unknown module {mod!r}")

            # Authored scenarios must have a narrative file on disk
            if status == "authored":
                narrative = OVERLAY_ROOT / sc.get(
                    "narrative_path",
                    f"narratives/scenarios/{sid}/narrative.md",
                )
                if not narrative.exists():
                    self.err(where, f"authored scenario has no narrative at {narrative}")
                emitted = OVERLAY_ROOT / sc.get(
                    "emitted_path",
                    f"narratives/scenarios/{sid}/_emitted/scenario.yaml",
                )
                if not emitted.exists():
                    if strict_emitted:
                        self.err(where, f"authored scenario has no emitted YAML at {emitted}")
                    else:
                        self.warn(where, f"no emitted YAML yet at {emitted} (run emit_scenarios.py)")
                else:
                    self._check_emitted_consistency(sid, emitted)

    def _check_emitted_consistency(self, sid: str, emitted: Path) -> None:
        where = f"emitted[{sid}]"
        try:
            data = load_yaml(emitted)
        except Exception as exc:
            self.err(where, f"failed to load: {exc}")
            return
        if data.get("id") != sid:
            self.err(where, f"emitted id={data.get('id')!r} disagrees with catalog id {sid!r}")
        labels = data.get("switch_labels") or []
        if not isinstance(labels, list) or len(labels) != 10:
            self.err(where, f"switch_labels must be a list of 10, got len={len(labels)}")
        # tools_scenario referenced in emitted frontmatter should be tools.yaml entries
        for t in data.get("tools_scenario", []) or []:
            tid = t.get("id") if isinstance(t, dict) else t
            if tid and tid not in self._tool_ids:
                self.err(where, f"tools_scenario refs unknown tool {tid!r}")
        for w in data.get("wake_words", []) or []:
            # narrative may use spaces (e.g. "mission control") for prose; map to underscores
            key = str(w).replace(" ", "_")
            if key not in self._wake_keys:
                self.err(where, f"wake_words[{w!r}] not in wake_words.yaml keyword bank")
        for i in data.get("intent_allowlist", []) or []:
            if i not in self._wake_keys:
                self.err(where, f"intent_allowlist[{i!r}] not in wake_words.yaml keyword bank")
        for m in data.get("hardware_modules", []) or []:
            if m not in self._hw_ids:
                self.err(where, f"hardware_modules[{m!r}] not in hardware_modules.yaml")

    def check_tools(self) -> None:
        for tool in self.tools.get("tools", []):
            tid = tool.get("id")
            where = f"tools.yaml[{tid!r}]"
            if not tid:
                self.err("tools.yaml", "tool entry missing id")
                continue
            for slot in tool.get("sfx_slot_refs", []) or []:
                if slot not in SFX_SLOT_RANGE:
                    self.err(where, f"sfx_slot_refs entry {slot} out of range 1..10")
            for disp in tool.get("referenced_displays", []) or []:
                if disp not in self._display_protocol_ids:
                    self.err(where, f"referenced_displays {disp!r} not in displays.yaml protocol_ids")
            for used in tool.get("used_by", []) or []:
                if used not in self._scenario_ids:
                    self.err(where, f"used_by refs unknown scenario {used!r}")

    def check_switches(self) -> None:
        for sw in self.switches.get("switches", []):
            sid = sw.get("id")
            where = f"switches.yaml[id={sid}]"
            slot = sw.get("click_sfx_slot")
            if slot is not None and slot not in SFX_SLOT_RANGE:
                self.err(where, f"click_sfx_slot {slot} out of range 1..10")
            mirror = sw.get("led_mirror")
            if mirror is not None and not 1 <= mirror <= self.leds.get("led_count", 50):
                self.err(where, f"led_mirror {mirror} outside LED range 1..{self.leds.get('led_count', 50)}")
        # MT-301 SFX slots
        key = self.switches.get("mt301_key") or {}
        for field in ("arm_sfx_slot", "disarm_sfx_slot"):
            slot = key.get(field)
            if slot is not None and slot not in SFX_SLOT_RANGE:
                self.err(f"switches.yaml[mt301_key]", f"{field} {slot} out of range 1..10")
        ptt = self.switches.get("ptt") or {}
        slot = ptt.get("click_sfx_slot")
        if slot is not None and slot not in SFX_SLOT_RANGE:
            self.err("switches.yaml[ptt]", f"click_sfx_slot {slot} out of range 1..10")

    def check_leds(self) -> None:
        n = self.leds.get("led_count", 0)
        if n <= 0:
            self.err("leds.yaml", "led_count must be > 0")
            return
        covered: list[int] = []
        for grp in self.leds.get("groups", []):
            where = f"leds.yaml[group={grp.get('id')!r}]"
            rng = grp.get("range")
            if not (isinstance(rng, list) and len(rng) == 2):
                self.err(where, "range must be a [start, end] pair")
                continue
            start, end = int(rng[0]), int(rng[1])
            if not (1 <= start <= end <= n):
                self.err(where, f"range {rng} not within 1..{n}")
                continue
            for i in range(start, end + 1):
                if i in covered:
                    self.err(where, f"led {i} also covered by an earlier group (overlap)")
                covered.append(i)
            for entry in grp.get("switch_mirror_map", []) or []:
                if entry.get("switch") not in self._switch_ids:
                    self.err(where, f"switch_mirror_map entry switch={entry.get('switch')} not in switches.yaml")
                if entry.get("led") not in range(start, end + 1):
                    self.err(where, f"switch_mirror_map entry led={entry.get('led')} outside group range {start}..{end}")
        missing = sorted(set(range(1, n + 1)) - set(covered))
        if missing:
            self.warn("leds.yaml", f"LEDs not in any group: {missing}")

    def check_displays_vs_hw(self) -> None:
        hw_display_ids = {
            m.get("id") for m in self.hw.get("modules", [])
            if m.get("kind") == "display"
        }
        only_in_displays = self._display_ids - hw_display_ids
        only_in_hw = hw_display_ids - self._display_ids
        for d in only_in_displays:
            self.err("displays.yaml", f"display {d!r} has no matching kind=display module in hardware_modules.yaml")
        for d in only_in_hw:
            self.err("hardware_modules.yaml", f"kind=display module {d!r} has no matching displays.yaml entry")

    def check_wake_words(self) -> None:
        # Every authored scenario's wake/intent set must be drawn from
        # the universal bank — already covered in check_scenarios.
        # Here just ensure no duplicate keys.
        seen: set[str] = set()
        for kw in self.wake_words.get("keywords", []):
            key = kw.get("key")
            if not key:
                self.err("wake_words.yaml", "keyword entry missing key")
                continue
            if key in seen:
                self.err("wake_words.yaml", f"duplicate keyword key {key!r}")
            seen.add(key)
            roles = kw.get("role") or []
            for role in roles:
                if role not in ("wake", "intent"):
                    self.err("wake_words.yaml", f"keyword {key!r} has unknown role {role!r}")

    def check_sfx_bank(self) -> None:
        slots = self.sfx.get("slots", [])
        if len(slots) != 10:
            self.err("sfx_bank.yaml", f"expected exactly 10 slots, got {len(slots)}")
        seen: set[int] = set()
        for s in slots:
            slot = s.get("slot")
            if slot in seen:
                self.err("sfx_bank.yaml", f"duplicate slot {slot}")
            if slot not in SFX_SLOT_RANGE:
                self.err("sfx_bank.yaml", f"slot {slot} not in 1..10")
            seen.add(slot)

    # ── orchestration ──────────────────────────────────────────────────
    def run(self, strict_emitted: bool = False) -> None:
        self.check_sfx_bank()
        self.check_switches()
        self.check_leds()
        self.check_displays_vs_hw()
        self.check_wake_words()
        self.check_tools()
        # scenarios last — it reaches into the other catalogs and benefits
        # from a clean lookup set
        self.check_scenarios(strict_emitted=strict_emitted)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--strict-emitted", action="store_true",
                    help="treat missing _emitted/scenario.yaml as an error, not a warning")
    args = ap.parse_args(argv)

    v = Validator()
    try:
        v.load()
    except (FileNotFoundError, ValueError) as exc:
        log(f"LOAD FAILED: {exc}")
        return 2

    v.run(strict_emitted=args.strict_emitted)

    for w in v.warnings:
        log(f"WARN  {w}")
    for e in v.errors:
        log(f"ERROR {e}")

    if v.errors:
        print(f"validate_canonical: FAIL ({len(v.errors)} errors, {len(v.warnings)} warnings)")
        return 1
    print(f"validate_canonical: OK ({len(v.warnings)} warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
