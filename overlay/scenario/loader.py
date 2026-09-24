"""Build a ``Scenario`` from its emitted YAML.

Every authored scenario module does the same thing: read
``overlay/narratives/scenarios/<id>/_emitted/scenario.yaml`` (written by
``overlay/tools/emit_scenarios.py``) and combine it with the generic tools
plus that scenario's own tools. The narrative stays the single source of
truth for title, voice, persona and switch labels.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml required: pip install pyyaml\n")
    raise

from .runtime import Scenario
from .tools import GENERIC_TOOLS, Tool


OVERLAY_ROOT = Path(__file__).resolve().parent.parent
NARRATIVES_DIR = OVERLAY_ROOT / "narratives" / "scenarios"

DEFAULT_SFX_ROLES = [
    "ack", "deny", "caution", "alarm", "arm",
    "disarm", "comms", "click", "tick", "status",
]


def emitted_yaml_path(scenario_id: str) -> Path:
    return NARRATIVES_DIR / scenario_id / "_emitted" / "scenario.yaml"


def load_emitted(scenario_id: str, path: Optional[Path] = None) -> dict:
    src = path or emitted_yaml_path(scenario_id)
    if not src.exists():
        raise FileNotFoundError(
            f"emitted scenario YAML not found at {src}.\n"
            f"Run: python overlay/tools/emit_scenarios.py {scenario_id}"
        )
    with src.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: emitted YAML is not a mapping")
    return data


def build_from_emitted(
    scenario_id: str,
    *,
    tools: Sequence[Tool],
    default_title: str,
    default_voice: str,
    emitted_path: Optional[Path] = None,
) -> Scenario:
    """Construct a ``Scenario``: emitted YAML + generic tools + ``tools``."""
    data = load_emitted(scenario_id, emitted_path)
    labels = data.get("switch_labels") or []
    if len(labels) != 10:
        raise ValueError("emitted scenario has fewer than 10 switch_labels")

    return Scenario(
        name=data.get("title", default_title),
        voice=data.get("voice", default_voice),
        persona_prompt=data.get("persona_prompt", ""),
        tools=list(GENERIC_TOOLS) + list(tools),
        switch_labels=[str(s) for s in labels],
        sfx_role_names=list(data.get("sfx_role_names") or DEFAULT_SFX_ROLES),
    )
