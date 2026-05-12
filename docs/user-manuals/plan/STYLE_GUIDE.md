# Style Guide — Build Manual

How to write the manual so a high-school-aged first-time builder can
follow it without prior electronics experience. Internal rules for the
manual author; not part of the manual itself.

---

## 1. Voice and tone

- **Second person, friendly.** "You're going to plug this in here," not
  "The user inserts the connector." Address the reader directly.
- **Plural inclusive when the build itself is the subject.** "We'll
  wire the LCD next," — the reader and author are doing the build
  together.
- **No condescension.** A 16-year-old who has never wired a breadboard
  is not a child; they're a beginner. The same tone you'd use teaching
  a curious adult colleague who happens to be new to electronics works.
- **No "obviously," "simply," "just," "easy."** These words don't help
  someone who is finding it not obvious. Replace with:
  - "obviously" → cut
  - "just" → cut
  - "simply" → cut
  - "easy" → describe what makes it manageable, e.g. "this is one wire"
- **No humour at the reader's expense.** Self-deprecation is fine
  ("the first time the author tried this, two LEDs let out their magic
  smoke; here's how to avoid that"). Reader-mocking jokes are not.

---

## 2. Jargon: introducing technical terms

Every technical term gets defined **the first time it appears**, with:

1. **Bold the term.**
2. Define it in plain English in parentheses on the same line.
3. Add to the glossary (Appendix C) with the chapter back-link.

Example:

> Connect the wire to the **GND** (ground — the shared "zero-volts"
> reference that every part of the circuit measures against, like
> sea level for elevations) rail on the breadboard.

Subsequent uses do not need the parenthetical; bold once, plain text
thereafter.

### Analogies for the harder terms

The following terms each get a specific analogy on first use. **Use
the same analogy every time** — consistency matters more than novelty.

| Term | Analogy |
|---|---|
| Voltage          | Water pressure |
| Current          | Water flow rate (how much per second) |
| Resistance       | A narrow part of a hose |
| Ground (GND)     | Sea level for elevation measurements |
| GPIO pin         | A wire whose state we can read or change |
| I²C bus          | A shared phone line with named participants |
| SDA / SCL        | The two wires of that phone line (one for data, one for the clock everyone speaks on) |
| Pull-up resistor | A weak spring that gently holds a switch in the "up" position when nothing else is pushing on it |
| Active low       | "Quiet means yes" — the wire is normally HIGH; it goes LOW to signal something |
| Shift register   | A conga line — push one dancer in at one end, dancers shuffle along, eight of them line up across the floor |
| Transistor       | A tiny electronic switch you flick by sending a small current to its "control" leg |
| Wake word        | A name the listening device responds to, like a dog's name |
| Buffer / queue   | A waiting room |

---

## 3. Format conventions

### Build steps — numbered lists

Every action the reader takes is a numbered step.

```markdown
1. Take the Metro RP2040 out of its anti-static bag.
2. Hold the small **BOOTSEL** button on the board.
3. While holding BOOTSEL, plug the USB-C cable into your computer.
4. Release BOOTSEL.
```

Sub-steps use letters: `a. b. c.` indented under the parent step.

### Callout boxes

Six styles, all using Markdown blockquote + a leading **bold label** so
they render as plain Markdown anywhere.

```markdown
> **WARNING.** Never connect the MT-301 key switch to mains household
> power. We use only its low-voltage auxiliary contacts.

> **WARNING.** *(soldering chapter)* The soldering iron tip is hot
> enough to cause third-degree burns through fabric. Treat it as
> dangerous every single time you reach for it. Wear safety glasses.
> Ventilate the room.

> **CHECKPOINT.** Before continuing, run `python -m overlay.pi5_hal sfx 1`
> and confirm you hear the ack chime.

> **TIP.** Take a photo of your wiring with your phone now. If
> something stops working later, you can compare to find what changed.

> **TWO-PERSON.** *(easier with a partner; possible alone.)* When
> drilling the panel for the MT-301 key, one person holds the key in
> position while the other marks the centre and drills the pilot hole.
> If you're alone, clamp the key to a scrap-wood guide first.

> **DEEP DIVE.** *(optional reading — skip on first pass.)* The
> 2N3904's gain (called β or h_FE) at room temperature is roughly 200,
> meaning…

> **MISTAKE.** *(common error)* If you wired the LED's short leg to +
> instead of GND, the LED will not light. LEDs are directional —
> reseat with the long leg toward + and the flat side toward GND.
```

Distribute these throughout — every chapter should have at least one
CHECKPOINT (the proof of completion) and at least one TIP or MISTAKE.
Use **TWO-PERSON** sparingly — only where one of three things is true:
(a) the action genuinely needs more than two hands; (b) the part is
heavy or unwieldy enough that dropping it would damage it; (c) the
step is dangerous enough that having a second person watching is
sensible. Always describe how to do the step alone too — the manual
must not assume a helper is available.

### Code blocks

- Use triple-backtick fenced blocks with the language tag (`bash`,
  `python`, `text`).
- For terminal sessions, use `text` and include the prompt:
  ```text
  $ python -m overlay.pi5_hal sfx 1
  [sfx] slot 1 (id=1)
  ```
- For Python edits, show the line numbers with the surrounding
  unchanged context so the reader can find the spot in the file. Mark
  changes with `# ← edit this line` if unclear.

### Wire colour conventions

Pick wire colours by *function*, not by what's in the jumper kit. The
manual recommends:

| Function | Colour |
|---|---|
| 5 V power           | Red |
| 3.3 V power         | Orange |
| GND                 | Black |
| I²C SDA             | Yellow |
| I²C SCL             | Blue |
| Data / signal       | Green |
| Anything else       | White |

A diagram in Chapter 4 introduces this convention. Every diagram
through the rest of the manual follows it. Photos are encouraged to
match (the builder can pick wires from their kit to mirror this).

### Diagrams

- Every wiring step has a diagram showing the breadboard view (top-down).
- Diagram IDs follow `D-<chapter>.<n>` (e.g. `D-6.3`).
- All diagrams listed in [`DIAGRAM_LIST.md`](DIAGRAM_LIST.md) with a
  one-line description and source format (Fritzing file path, photo
  file path, hand-drawn scan path).

### Photographs

- One "what your bench should look like now" photo at the end of every
  wiring step.
- Photos are annotated with simple arrows + text overlays for the first
  reference to any new component. Subsequent photos are unannotated.
- Resolution: 1600 px wide minimum. Format: WebP preferred, JPEG
  acceptable.
- Lighting: bright, even. Background: solid colour (cardboard or a
  cutting mat) — no clutter.

---

## 4. Chapter structure

Every chapter follows the same skeleton so a reader can navigate
predictably:

```markdown
# Chapter N — Title

## What you're doing in this chapter
*One paragraph. Plain English. Promise the win.*

## Before you start
- Prereqs from prior chapters (with links)
- Parts laid out (with photo or list)
- Time estimate (e.g. "20 minutes")

## Step-by-step
*Numbered list of actions, interleaved with explanations.*

## Checkpoint
*The proof. The reader runs a specific command or observes a specific
behavior. If it works → continue. If not → see Troubleshooting Ch 15.*

## What you just did
*One paragraph of recap, framing what's now possible.*

## Coming up
*One line forward-link.*
```

This redundancy is intentional. A reader who skims first and then
follows along has a clear map; a reader who gets distracted can
re-orient quickly.

---

## 5. Length and pacing

| Chapter type | Target word count | Time to read + do |
|---|---|---|
| Orientation (Ch 0–4)       | 800–1,500    | 15–20 min |
| Module wiring (Ch 5–12)    | 1,500–2,500  | 30–45 min |
| Mounting / final (Ch 13–14) | 1,000–2,000 | 30 min |
| Troubleshooting (Ch 15)    | 2,500+ (reference, not read linearly) | n/a |

If a chapter exceeds 3,000 words, split it. A reader's stamina is the
budget.

---

## 6. Accessibility

- **Colour is never the only signal.** Wire-colour diagrams also use
  labels on every wire. The 4.7 kΩ resistor's colour bands diagram
  also shows the numeric value next to the bands.
- **Plain language scoring.** Aim for a Flesch reading-ease score above
  60 (≈ 8th grade reading level). Tools: `pip install textstat`; run
  on each finished chapter.
- **Alt text for every figure.** Markdown image syntax
  `![alt text](path)` with descriptive alt text, not just "figure 6.3."

---

## 7. Inclusive language

- **No assumed background.** Don't write "as you'll remember from your
  electronics class." Many readers haven't taken one.
- **Multiple "righ" paths where they exist.** Where a step has more
  than one reasonable approach (e.g. "you can solder this or use a
  breadboard"), present both and explain the trade-off briefly.
- **Pronouns: singular "they" for the reader.** Never assumes a
  gender or age beyond "high-school-aged."

---

## 8. Where the writing happens

Most of the manual is written **at the bench, during the real build.**
The author follows their own draft, builds the thing, and rewrites in
real time as gotchas emerge. The fictional manual that's written
without a real bench misses 80% of the actual difficulties.

Order of writing:

1. **Chapters 0–4 first** (workspace and orientation). These don't need
   the bench. Drafting them surfaces what the bench setup will look like.
2. **Chapters 5–12 at the bench, in build order.** Wire it, test it,
   write what just happened.
3. **Chapter 15 — troubleshooting — populated continuously** as
   problems occur during steps 2 and 3. Every gotcha goes into the
   table immediately.
4. **Chapters 13–14 after the build is done** and a panel exists.
5. **Appendices last** — they reference content that should already be
   stable.

---

## 9. Review checklist for each chapter

Before considering a chapter "done":

- [ ] Read by someone who has *not* built the thing. They follow it and
      either complete the chapter or report where they got stuck.
- [ ] Every new term is bolded + defined on first use.
- [ ] Every new term is added to the glossary.
- [ ] Every wiring step has a diagram AND a photo.
- [ ] The checkpoint at the end is testable in plain language.
- [ ] All callout boxes use the five canonical styles (§3).
- [ ] Flesch reading-ease ≥ 60 (use `textstat`).
- [ ] No "just," "simply," "obviously," or "easy" remaining.
- [ ] All wire colours match §3 convention.
