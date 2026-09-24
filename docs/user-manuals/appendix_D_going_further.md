# Appendix D — Going Further

## You finished the build. Now what?

If you've made it this far, the panel in front of you can hear you, think about what you said, and answer with switches, lights, sound, and a spoken voice. That's a real thing. Pause for a moment and notice that you built it from a pile of loose parts and a manual.

This appendix is a map of the next five places you can take the project. None of them are full tutorials — each is a one-paragraph nudge plus a pointer to the file in the repository that has the real details. Pick one. Pick none. Pick all five over the next year. The build you have is finished as it stands; everything below is for the curious.

The five forks branch out from the same panel:

1. **Author your own scenario** — give the panel a new personality.
2. **Add a new sound** — change the audio palette the panel speaks in.
3. **Train your own Nicla wake word** — teach the panel to listen for a different name.
4. **Migrate the build to a soldered protoboard** — go further than [Chapter 13](13_permanent_build_soldering_perfboard_panel.md), or come back to it if you skipped it.
5. **Add the GIGA Display Shield as a touch scenario-selector** — pick the active scenario from a touch screen.

## Fork 1 — Author your own scenario

The panel ships with six **scenarios** (named personalities the panel takes on — each one comes with its own voice, switch labels, sound mappings, and tools the AI is allowed to use):

- **Space Command Launch** — a launch control center. Includes a real countdown, an arm-gated ignition sequence, and a range-safety destruct call.
- **Spaceship Cockpit** — a civilian deep-space explorer. Adds a warp drive, a sector scanner, and an airlock vent.
- **Pirate Ship** — an irreverent free-trader. Fire the cannon, raise the Jolly Roger, dispense grog. No arm-gate; pirates are reckless.
- **Mars Control Normal** — calm day-to-day operations on Mars. Daily systems check, resource queries, EVA scheduling.
- **Mars Control Disaster** — same physical panel as Normal, sharpened persona, evacuation and mayday tools.
- **Army Battle Command** — the most arm-gated scenario. ISR requests, target engagement, counter-battery calls — every destructive tool requires both the MT-301 key in ARM and a specific switch on.

Each one started as a piece of prose. A writer described how the console should feel and what the AI is allowed to do, and the prose was turned into the YAML and Python that the runtime reads. To make your own — say a Submarine Bridge, or a Lighthouse Keeper, or a Library Reference Desk — start at the authoring guide in [overlay/scenario/README.md](../../overlay/scenario/README.md). The gold-standard worked example is the Space Command pair: the prose lives in [overlay/narratives/scenarios/space_command_launch/narrative.md](../../overlay/narratives/scenarios/space_command_launch/narrative.md), and the Python module that the runtime imports is [overlay/scenario/space_command_launch.py](../../overlay/scenario/space_command_launch.py). The bridge between the two is `overlay/tools/emit_scenarios.py`, which reads the narrative and writes the YAML the Python loads.

The shape of the work, end to end: write a one-page narrative; list the ten switch labels; pick which of the ten universal sounds each event uses; decide which tools are arm-gated; run the emitter; verify against the browser simulator with `python -m overlay.scenario.demo --scenario your_scenario --repl`; iterate until it feels right.

> **TIP.** Start by copying the Pirate Ship folder and renaming it. Pirate Ship is the smallest of the six (no arm-gate, three tools, short narrative), so swapping the persona and switch labels is the quickest way to feel the whole authoring loop end to end.

## Fork 2 — Add a new sound

The CH358D sound module from [Chapter 6](06_sound_module_ch358d.md) holds exactly **ten** sound slots. Not eleven. The board has ten trigger pins, one for each WAV file on its TF card. Adding an eleventh sound means either re-purposing one of the ten slots or wiring a second CH358 module.

If you want to re-purpose a slot, the work happens in [overlay/canonical/sfx_bank.yaml](../../overlay/canonical/sfx_bank.yaml). That file holds a **procedural spec** for each slot — a recipe the generator follows to build the WAV from scratch. Every slot lists a waveform (sine, square, sawtooth, white noise), a frequency or pair of frequencies, a duration, an envelope (the volume shape over time), and a gain. Edit the recipe for the slot you want to change. Save the file.

Then re-generate the WAVs:

```bash
python overlay/tools/generate_sfx.py
```

Ten fresh `.wav` files land in `overlay/dev_assets/sfx_preview/`. Copy them onto the CH358's TF card the same way you did in Chapter 6 — plug the module's micro-USB into your computer, drag the new WAVs over, eject. Power-cycle the CH358 and it'll play the new sound on the slot you changed.

The catch: every scenario narrative that mentions the old slot now needs an update. If slot 4 was the alarm klaxon and you turned it into a chime, every scenario that calls `play_sfx("alarm")` will still trigger slot 4 — but now it plays a chime, which is probably not what you want. Search the six narratives under `overlay/narratives/scenarios/` for the old role name, decide whether each reference still makes sense, and re-run `python overlay/tools/emit_scenarios.py` after editing. The notes block at the bottom of [overlay/canonical/sfx_bank.yaml](../../overlay/canonical/sfx_bank.yaml) reminds you of this whenever you open the file.

## Fork 3 — Train your own Nicla wake word

The Nicla Voice you wired in Chapter 12 ships with a pre-trained model that listens for one word. You can replace that model with one of your own — trained on your voice, listening for any keyword you choose. The path goes through **Edge Impulse Studio** (a browser-based platform for training small machine-learning models that run on tiny chips, with a free tier that covers everything this project needs).

This is a real multi-week project, not a one-evening change. The appendix is a pointer rather than a tutorial; the work itself follows roughly this arc:

1. **Make an Edge Impulse account** at `edgeimpulse.com`. The free "Developer" tier is enough.
2. **Record samples.** Aim for 20 to 50 short recordings of yourself (and, ideally, other people) saying the new wake word. Edge Impulse can capture them directly from a connected Nicla, or you can upload WAV files. The wider the range of voices and accents, the better the model will generalize.
3. **Record "anything else" samples.** The model also needs to know what *isn't* the wake word — background chatter, your TV, room noise. Record several minutes of that, too.
4. **Train.** Edge Impulse handles the actual training in the cloud. You'll pick a neural-network architecture (the defaults are sensible) and watch the accuracy climb during training.
5. **Deploy to the NDP120.** The NDP120 is the always-listening chip on the Nicla Voice, and Edge Impulse has a dedicated deployment target for it. Download the firmware bundle and flash it onto the Nicla following the project's existing flashing process.
6. **Update the canonical wake-word list.** Edit `overlay/canonical/wake_words.yaml` so the rest of the system knows about the new word. The Pi-side overlay reads from this file when it decides how to react to wake events.

Plan on weeks rather than days, mostly because step 2 is patient work — every recording matters, and quick training runs on too few samples produce models that miss your wake word or trigger on a sneeze. Edge Impulse's tutorial pages walk you through the user interface; the parts specific to *this* build are the Nicla deployment target and the `wake_words.yaml` update at the end.

## Fork 4 — Migrate the build to a soldered protoboard

Here's where this appendix splits in two, depending on what you actually did.

**If you skipped Chapter 13** and stopped at the breadboard prototype — that's fine. The breadboard is a real, finished panel; many builders happily live there forever. If you change your mind later, [Chapter 13](13_permanent_build_soldering_perfboard_panel.md) is waiting for you and it doesn't matter how long the gap is. The chapter teaches soldering from a zero-experience starting point, walks you through migrating each subsystem from breadboard to perfboard one at a time, and ends with everything mounted to a real front panel. Allow a couple of weekends for it.

**If you did Chapter 13** and now own a soldered, panel-mounted build — the next step beyond perfboard is a **custom PCB** (a printed circuit board fabricated to your design, with copper traces baked in instead of wires you solder). PCB design is out of scope for this manual, but the rough path: download **KiCad** (a free, open-source PCB design tool — `kicad.org`), recreate your perfboard's circuit as a schematic, lay out the board, and send the design files to a small-batch fab house like **OSH Park** (`oshpark.com`) or JLCPCB. Three custom boards typically cost about $15 and arrive in two to three weeks.

Laying out a board that includes the Metro RP2040 socket, the MCP23017, seven 74HC595s, ten transistor drivers, and connectors for everything that leaves the board is a real engineering exercise. Most people who go down this path treat the perfboard version as a reference design and the PCB as a re-implementation for the next build. Plan on a month of evenings.

> **TIP.** Even if you never order a PCB, drawing your perfboard layout in KiCad's schematic editor is worthwhile. The schematic forces you to name every connection, and the act of naming things tends to find mistakes the perfboard hid.

## Fork 5 — Add the GIGA Display Shield as a touch scenario-selector

Look at the Bill of Materials, §1.2: there's an **Arduino GIGA Display Shield** sitting in inventory. It's a 3.5-inch capacitive touch screen meant to clip onto the front of an **Arduino GIGA R1 WiFi** host board. The shield is on hand; the R1 host board is in §3 of the BOM as an optional procurement (around $80). Without an R1 you can't drive the shield — the shield is not a standalone device.

The role the shield could play in this build is a touch UI for picking the active scenario. Today, switching from Pirate Ship to Mars Control Disaster means stopping the demo, typing `--scenario mars_control_disaster`, and starting it again. With a touch UI you could tap a scenario tile on the shield and the panel would re-label itself in place — the persona changes, the switch meanings change, the sound mappings change, all without you touching a keyboard.

The wiring would look like this:

- The Arduino GIGA R1 (with the shield clipped on) plugs into one of the Pi 5's USB ports — same way the Metro and the Nicla already do.
- The GIGA runs a small firmware that draws the scenario tiles on the shield and watches for taps.
- When a tile is tapped, the GIGA sends a JSON-lines message to the Pi over USB: `{"t":"scenario_set","name":"pirate_ship"}`.
- The Pi-side overlay listens for that message and tells the scenario runtime to swap personalities. The panel's switch labels and sound mappings change on the fly.

This is a real future drop, not yet built. The "Drops 5–9" territory mentioned in [overlay/README.md](../../overlay/README.md) is where this work would land. The HAL protocol that already runs between the Pi and the Metro (documented in [overlay/docs/HAL_PROTOCOL.md](../../overlay/docs/HAL_PROTOCOL.md)) is the right template for the Pi-to-GIGA messages — the protocol is intentionally a generic JSON-lines stream, so a new peer fits in without re-writing the existing parts. If you want to take this on, the natural starting point is to write the firmware on the GIGA first, verify it sends well-formed messages over USB serial to your laptop, then wire up the Pi-side listener.

## A word before you go

You built a thing. You wired tiny components onto a breadboard, watched a transistor switch a sound, typed text onto a screen with two wires and one chip, and turned a key and heard the panel arm. You earned each of those moments by following along and not giving up when something didn't work on the first try.

The full source of this project lives at [github.com/WayneRoessling/rasPI_playstation_with_ai](https://github.com/WayneRoessling/rasPI_playstation_with_ai). New drops land there as the build grows, and if you find a bug or want to share a scenario, that's where to send it. The panel on your desk is now a tool you can lean on. Have fun with it.
