# Chapter 0 — Welcome & Safety

## What you're doing in this chapter

Welcome. You're about to build a voice-controlled panel — a row of switches, lights, a screen, and a speaker — that listens to you talk, thinks about what you said, and responds. A small computer called a **Raspberry Pi 5** (a credit-card-sized computer that runs a full operating system) does the thinking. A second small board called the **Metro RP2040** (a smaller chip-based board that controls the switches and lights) handles the panel itself.

This first chapter has no wiring. You'll meet the tools you'll be using, learn the four safety rules that keep you and your parts in one piece, and form one quick habit — touching something metal before you touch a chip — that protects the most fragile components in the build.

> **PHOTO PENDING (D-0.2).** A finished mini-ai control panel with switches, LEDs, and small displays mounted on a front panel.

<!-- Restore when the photo exists: ![A finished mini-ai control panel with switches, LEDs, and small displays mounted on a front panel](images/D-0.2.png) -->

## Before you start

You don't need any prior electronics experience. You don't need to know what a resistor is. You don't need to have soldered anything. Every term you'll meet in this manual is bolded and explained the first time it shows up.

What you do need:

- A clear table or desk you can leave alone for a few weeks. The build moves one module at a time, and it helps to keep everything in place between sessions.
- A power outlet within reach of the table.
- A computer (Windows, Mac, or Linux) that can run a web browser and open a serial terminal. The Raspberry Pi will do most of the work, but you'll do some setup from your regular computer.
- Around 20 minutes for this chapter.

## Step-by-step

### 1. Lay out the tools

Spread the following tools on the table. You'll use them across many chapters, so a permanent home for each one saves time later.

> **PHOTO PENDING (D-0.1).** Tool tray showing USB-C cable, USB-A cable, side cutters, wire strippers, Phillips screwdriver, jumper-wire kit, breadboard, and a phone for taking photos.

<!-- Restore when the photo exists: ![Tool tray showing USB-C cable, USB-A cable, side cutters, wire strippers, Phillips screwdriver, jumper-wire kit, breadboard, and a phone for taking photos](images/D-0.1.png) -->

a. A **USB-C cable** (the small oval connector you can plug in either way up) that carries data. Some USB-C cables only carry power — those won't work for talking to the Metro RP2040. If the cable came with a phone charger, it's probably fine.

b. A **USB-A cable** (the older rectangular plug that only goes in one way up) for the Arduino Nicla Voice in a later chapter.

c. **Side cutters** (small pliers with a sharp angled blade for trimming wires).

d. **Wire strippers** (a tool that removes the plastic coating from a wire without cutting the metal inside).

e. A small **Phillips screwdriver** (the cross-shaped tip).

f. A **jumper-wire kit** (a bundle of short pre-cut wires with metal pins on the ends, used to make temporary connections on a breadboard).

g. A **breadboard** (a plastic board with rows of holes you can push wires into without soldering). You'll meet this properly in Chapter 3.

h. A phone or camera for progress photos.

i. A **multimeter** (a battery-powered tool that measures voltage and continuity, the two things you most need to check when wiring goes wrong). A basic $20 model is plenty.

### 2. Read and remember the four safety rules

These four rules cover everything that can go wrong in this build. Read them once. Re-read them whenever you sit down at the bench.

> **WARNING.** **Rule 1 — No liquids near the bench.** Move drinks to a different table. A spilled glass of water on a powered breadboard ends the build for the day, and possibly forever for whichever chip got soaked.

> **WARNING.** **Rule 2 — No mains voltage.** Everything in this manual is powered from a USB cable or the breadboard, which means it runs at 5 V or less. **Never** wire any part of this build directly into a wall outlet. The MT-301 key switch you'll meet in Chapter 11 is rated for industrial mains use, but we are only using its low-voltage auxiliary contacts. Do not connect it to household power.

> **WARNING.** **Rule 3 — Ground yourself.** Before you handle any chip — anything in a black anti-static bag — touch a large metal object first. A radiator, a metal table leg, or the metal case of a desktop computer all work. This step is short and weird, and it absolutely matters. See the **ESD** section below.

> **WARNING.** **Rule 4 — Power off before changing wires.** Pull the USB cable out of the Pi before you move any wire on the breadboard. The board doesn't mind if you don't, until one day it does. Make it a habit.

### 3. Understand ESD in one minute

**ESD** stands for **electrostatic discharge** — the same small zap you get from a doorknob in winter. To your finger, it's a brief sting. To a chip the size of a fingernail, it's a lightning strike. ESD damage often doesn't kill a chip immediately — it weakens it, and the chip fails later, after you've spent two hours wondering what's wrong.

The fix is simple. Before opening any chip's packaging:

a. Reach over and touch a large grounded metal object. The case of a powered-on desktop computer is the textbook example. A radiator works. A water tap works.

b. Now open the bag and pick the chip up by the edges. Don't touch the metal legs.

c. If you walk across a carpeted room in socks, you've recharged yourself. Touch the metal object again before picking the chip up.

> **TIP.** Many builders buy a $5 **ESD wrist strap** (a stretchy band with a wire that clips to something grounded). It works very well, but it's not required. The "touch metal first" habit covers the same ground for a build that doesn't take all day.

> **DEEP DIVE.** *(optional reading — skip on first pass.)* The voltage on a person who's walked across a wool carpet in dry winter air can reach 35,000 V. That's not a typo. It doesn't hurt you because almost no current flows. A chip's protection diodes are sized for hundreds of volts of static, so anything beyond that punches a microscopic hole in the silicon. The chip might still kind of work, but with intermittent errors that look like bad code or bad wiring. ESD damage is the most frustrating failure in electronics because it doesn't announce itself.

### 4. Form the progress-photo habit

Pull out your phone. Take a photo of your empty tools tray right now.

That photo doesn't matter. The habit does. Every chapter ends with a photo step. When something stops working three chapters from now, you'll thank yourself for having a record of what worked before.

### 5. Identify a small "parts box"

Find a shoebox, an empty tackle box, or a small bin with compartments. As parts come out of their packaging across the next chapters, they'll go in here. Loose parts on a desk get lost. Loose chips on a desk get sat on.

## Checkpoint

> **CHECKPOINT.** Before moving on to Chapter 1, you should:
>
> - Have all the tools listed in step 1 on the table.
> - Be able to say the four safety rules out loud without looking.
> - Have touched a grounded metal object at least once.
> - Have a parts box on the table, even if it's empty.
>
> If any of those four is missing, finish them before turning the page.

## What you just did

You set up the workspace, learned the four rules that keep the build (and you) safe, and met the term **ESD** — the silent killer of microchips. The tools on the table now will follow you through every chapter. From this point on, the manual will assume you have them within reach.

## Coming up

In [Chapter 1](01_what_you_already_have.md) you'll meet the parts that already live in the mini-ai system — the Raspberry Pi, its power supply, the microphone-speaker, the webcam, and the storage drive. You'll learn their names and what each one does, so the rest of the manual can refer to them by name without losing you.
