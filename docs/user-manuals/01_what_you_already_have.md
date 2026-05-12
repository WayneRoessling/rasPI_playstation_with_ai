# Chapter 1 — What You Already Have

## What you're doing in this chapter

Before you wire anything new, let's lay out the parts that are already in the mini-ai system and learn their names. There are five of them on the desk right now: the Raspberry Pi 5, its power supply, the microphone-and-speaker module, the webcam, and the storage drive. None of these need wiring — they all connect through USB cables that probably came in their boxes — but the rest of the manual will keep referring to them by name, so a quick guided tour now saves a lot of guessing later.

This chapter is about identification, not assembly. By the end you'll be able to point at each part and say what it does in one sentence.

![Annotated photo of the five existing mini-ai parts arranged on a tray: Pi 5, 27 W USB-C power supply, Yahboom mic/speaker, Logitech C920 webcam, and 2 TB SSD](images/D-1.1.png)

## Before you start

You should have finished [Chapter 0](00_welcome_and_safety.md). The tools and the parts box are on the table.

You'll need:

- The five existing parts (Pi 5, PSU, Yahboom mic/speaker, C920 webcam, SSD). If yours arrived together, they're probably still in their original boxes — open them now and put each part on the table, but leave any anti-static bags closed for the moment.
- About 15 minutes.

## Step-by-step

### 1. Meet the Raspberry Pi 5

Pick up the **Raspberry Pi 5** (a credit-card-sized computer that runs a full operating system, made by the Raspberry Pi Foundation). It's the green-or-red rectangular board with four USB ports, a network port, and a fan on top.

The Pi 5 is a **single-board computer**, often shortened to **SBC** (an entire computer — processor, memory, network, video — on one circuit board, with no separate case or extras). Yours has 16 GB of RAM and is the most powerful Pi model that exists at the time of writing.

A few features to find with your eyes:

a. The four **USB ports** — two black (USB 2.0, slower) and two blue (USB 3.0, faster). The Yahboom mic/speaker and the webcam will plug in here.

b. The **USB-C power input** in one corner. The label says "PWR IN." This is where the 27 W power supply goes.

c. The **40-pin GPIO header** along one long edge. **GPIO** stands for **general-purpose input/output** — a row of metal pins you can use to send or receive small electrical signals. You won't touch these until Chapter 4, but it's worth knowing they're there.

d. The **fan**, which sits on top of a heat sink. It spins up when the Pi works hard. That's normal.

> **TIP.** If your Pi is in a case, that's fine — leave it in the case. The case typically has cutouts for every port and the heat sink is usually inside it. Take the case off only if Chapter 4 asks you to (it doesn't on most cases — the GPIO header is reachable through the top cutout).

### 2. Meet the 27 W USB-C power supply

Next to the Pi, find the **USB-C power supply** (a wall plug with a USB-C cable coming out of it). This is sometimes called the **PSU** (short for **power supply unit** — the device that turns wall-outlet power into the safe low-voltage power the Pi needs).

![Close-up of the official 27 W USB-C power supply, with the 27 W rating circled on the label](images/D-1.2.png)

Look at the label on the brick. It should say **27 W** (sometimes written **5.1 V / 5 A**). This number matters.

> **WARNING.** The Pi 5 needs the **27 W** supply. A phone charger or laptop power brick might look identical and even plug in — but if it's rated below 27 W, the Pi will silently behave strangely: random reboots, USB devices that disappear, files that corrupt. None of those failures look like a power problem on the surface. Always use the proper 27 W supply.

> **MISTAKE.** *(common error)* "It plugged in, so it must be fine." Many USB-C bricks are 15 W or 20 W, which is enough to make a Pi 5 turn on but not enough to keep it stable under load. If you see weird behaviour later — a USB device that vanishes when the speaker plays — check the brick's wattage first.

### 3. Meet the Yahboom mic/speaker

Find the **Yahboom YB-MAE02-V1.0** (a small circuit board with a microphone array and a speaker, made by Yahboom). It has a USB-A cable coming out of it. You'll hear it called the "Yahboom mic" or "Yahboom speaker" interchangeably across the manual — it's both.

This part is what the mini-ai talks **through** and listens **with**. When the AI replies to you, the spoken voice comes out of this speaker. When you speak to it, the microphone array picks you up.

The Yahboom plugs into one of the Pi's USB-A ports. Don't plug it in yet — it lives in the parts box for now.

### 4. Meet the Logitech C920 webcam

Find the **Logitech C920** (a USB webcam with a clip mount). It's a regular video-call camera. The mini-ai uses it for optional vision tasks — you can ask "what do you see?" and it'll describe the scene.

For this manual, the webcam is **not** part of the panel build. It stays plugged in for vision, but the control panel works the same whether you use vision features or not. You'll find it mentioned in [Chapter 14](14_first_real_run.md) and not before.

> **DEEP DIVE.** *(optional reading — skip on first pass.)* The C920 is a **UVC** device — **USB Video Class** — which means any modern computer treats it as a generic webcam without needing a driver. The same is true for the Yahboom mic/speaker, which is a **USB Audio Class** device. This is why neither one needs configuration to work with the Pi.

### 5. Meet the 2 TB SSD

Find the **SSD** (an **solid-state drive** — fast computer storage with no moving parts, the modern replacement for spinning hard drives). Yours is a **2 TB** drive — 2,000 gigabytes — which is enormous for a build like this. The reason it's that large is that the AI's language models and the speech-recognition data take up a lot of room.

The SSD plugs into the Pi via a USB enclosure or a special board called a **HAT** (a small expansion board that mounts on top of the Pi's GPIO header — the acronym originally stood for "Hardware Attached on Top"). Either way works. Yours is probably already attached.

### 6. Look up what your mini-ai can already do

The Pi runs three pieces of software that are already installed. You don't need to set these up — the existing mini-ai-pi setup script handled them — but it helps to know what each one does, because you'll be talking to them through the panel later.

- **Whisper.** Listens to a sound file and writes down the words. This is **speech-to-text** (often shortened to **STT**).
- **Ollama.** Takes a question and writes back an answer, like a chat conversation. It runs a **large language model**, often shortened to **LLM** (a kind of AI program that reads text and writes more text).
- **Piper.** Takes a piece of text and reads it out loud. This is **text-to-speech** (often shortened to **TTS**), and it's what comes out of the Yahboom speaker.

Together, those three programs form the **voice pipeline**: you speak, Whisper writes it down, Ollama reads it and writes back, Piper reads the reply out loud. The control panel you're about to build sits on top of this pipeline and adds switches, lights, and a smaller dedicated speaker for sound effects.

### 7. Optional: turn the Pi on and verify it works

If you want a quick win right now, plug the Pi into its power supply and let it boot. You'll see the fan spin and small green and red lights blink on the board. After about 30 seconds, the Pi is awake.

You don't need to do anything with the Pi yet — that comes in [Chapter 4](04_powering_things.md). Power it off again (pull the USB-C plug from the Pi end, not the wall end — same as you'd close a laptop) and put it back on the bench.

## Checkpoint

> **CHECKPOINT.** Before continuing to Chapter 2, you should be able to:
>
> - Point to the Raspberry Pi 5 and name it.
> - Point to the 27 W power supply and explain why the wattage matters.
> - Point to the Yahboom mic/speaker, the C920 webcam, and the SSD.
> - Say what STT, LLM, and TTS each do, in your own words.
>
> If any of those is fuzzy, re-read the relevant step.

## What you just did

You took five parts out of their boxes, learned their names, and met five new vocabulary words: **Raspberry Pi**, **single-board computer (SBC)**, **PSU**, **GPIO**, and **HAT**. You also met the three programs that make up the voice pipeline: **Whisper** (speech-to-text), **Ollama** (the language model), and **Piper** (text-to-speech). The rest of the manual builds the **panel** that sits next to those parts — a row of switches, LEDs, displays, and sound — without touching the voice pipeline at all.

## Coming up

[Chapter 2](02_big_picture_of_the_control_panel.md) zooms out and shows the four-box picture of the whole system: the Pi, the panel's own brain, the always-listening ear, and the panel itself. Once you can sketch that picture from memory, the rest of the build is a guided tour of how those four boxes get wired together.
