# Appendix C — Glossary

Every technical term bolded in chapters 0 through 4 of this manual, with a short definition and a link back to the chapter where it first appeared. Add to this glossary as new terms are introduced in later chapters.

---

## A

**Active low.** A signalling convention where a wire is normally HIGH (at the supply voltage), and a device pulls it LOW (down to GND) to mean "yes." "Quiet means yes." First appears in a later chapter; included here for forward reference.

---

## B

**Breadboard.** A plastic board with hundreds of small holes that connect to each other in a fixed pattern under the surface, used to wire circuits temporarily without solder. The two long rails on each edge run the full length; the columns of 5 holes in the middle are connected vertically. See [Chapter 3](03_setting_up_your_workspace.md).

**Bus.** A shared wire (or small group of wires) that several devices listen to at the same time, each identified by an address. The mini-ai panel uses an I²C bus for its displays. See [Chapter 2](02_big_picture_of_the_control_panel.md).

---

## C

**Camera (C920).** The Logitech C920 USB webcam used by the mini-ai for optional vision tasks. It's a UVC-class device, meaning any computer recognises it without a special driver. See [Chapter 1](01_what_you_already_have.md).

**Common ground.** The practice of connecting every device's GND wire to the same set of wires, so all devices agree on what "zero volts" means. Sharing a ground is mandatory; devices with private "grounds" misbehave. See [Chapter 4](04_powering_things.md).

**Current.** How much electricity flows per second, like water flow rate in a pipe. Measured in amperes (A). See [Chapter 4](04_powering_things.md).

---

## E

**ESD (electrostatic discharge).** The tiny zap you get from a doorknob in winter. Harmless to people, sometimes fatal to chips. The fix is to touch a grounded metal object before handling any chip. See [Chapter 0](00_welcome_and_safety.md).

**ESD wrist strap.** A stretchy band with a wire that clips to something grounded, keeping you continuously discharged while you work. Optional but useful. See [Chapter 0](00_welcome_and_safety.md).

---

## G

**GND (ground).** The shared "zero-volts" reference that every part of a circuit measures voltage against, like sea level for elevations. Wired in black throughout this manual. See [Chapter 3](03_setting_up_your_workspace.md) and [Chapter 4](04_powering_things.md).

**GPIO (general-purpose input/output).** A wire whose state a computer can read or change. The Pi 5 has 40 GPIO pins; the Metro RP2040 has 26. See [Chapter 1](01_what_you_already_have.md).

**GPIO header.** The black plastic strip with two rows of metal pins along one edge of the Raspberry Pi. The Pi 5 has 40 GPIO pins arranged in a 2×20 layout. See [Chapter 4](04_powering_things.md).

---

## H

**HAL (hardware abstraction layer).** Software that hides the difference between real hardware and a simulator, so the same code works whether the panel is wired up or whether you're testing in a browser. See [Chapter 2](02_big_picture_of_the_control_panel.md).

**HAT.** A small expansion board that mounts on top of the Raspberry Pi's GPIO header. The acronym originally stood for "Hardware Attached on Top." See [Chapter 1](01_what_you_already_have.md).

---

## J

**Jumper wire.** A short pre-cut wire with metal pins on the ends, used to make temporary connections on a breadboard. Comes in male-male, male-female, and female-female flavours. See [Chapter 3](03_setting_up_your_workspace.md).

---

## L

**LLM (large language model).** A type of AI program that reads text and writes more text. The mini-ai runs an LLM called Ollama, which is what produces the conversational replies. See [Chapter 1](01_what_you_already_have.md).

---

## M

**MCU (microcontroller).** A tiny computer that runs a single program forever, talks directly to physical pins, and reacts instantly. The Metro RP2040 is an MCU. See [Chapter 2](02_big_picture_of_the_control_panel.md).

**Multimeter.** A battery-powered tool that measures voltage and continuity, the two checks you'll do most often when wiring goes wrong. A basic $20 model is plenty. See [Chapter 0](00_welcome_and_safety.md) and [Chapter 4](04_powering_things.md).

---

## O

**Ollama.** The piece of software running on the Pi that holds the large language model (LLM) and produces conversational replies. See [Chapter 1](01_what_you_already_have.md).

---

## P

**Panel (control panel).** The flat board with switches, LEDs, displays, a small speaker, and a key switch on the front that the manual teaches you to build. See [Chapter 2](02_big_picture_of_the_control_panel.md).

**Piper.** The piece of software running on the Pi that reads text out loud through the speaker — text-to-speech (TTS). See [Chapter 1](01_what_you_already_have.md).

**Progress photo.** A photo taken at the end of every wiring step. The series of progress photos becomes your private debugging tool when something stops working later. See [Chapter 0](00_welcome_and_safety.md) and [Chapter 3](03_setting_up_your_workspace.md).

**PSU (power supply unit).** The wall-plug device that turns wall-outlet power into the safe low-voltage power the Pi needs. For the Pi 5, must be the 27 W USB-C version. See [Chapter 1](01_what_you_already_have.md).

---

## R

**Rail.** One of the four long rows along the edges of a breadboard. The two on the top run full-length; the two on the bottom run full-length; the top and bottom are not connected to each other through the board itself. See [Chapter 3](03_setting_up_your_workspace.md).

**Raspberry Pi.** A credit-card-sized computer that runs a full operating system, made by the Raspberry Pi Foundation. The mini-ai uses the Pi 5 model with 16 GB of RAM. See [Chapter 1](01_what_you_already_have.md).

**Resistance.** A property of a material that limits how much electricity can flow through it, like a narrow section in a hose. Measured in ohms (Ω). See [Chapter 4](04_powering_things.md).

---

## S

**SBC (single-board computer).** An entire computer — processor, memory, network, video — on one circuit board, with no separate case or extras. The Raspberry Pi is an SBC. See [Chapter 1](01_what_you_already_have.md).

**Simulator.** Software that pretends to be hardware. The mini-ai's simulator opens in your web browser and shows the panel as a clickable on-screen interface, so you can test code before any real wires are plugged in. See [Chapter 2](02_big_picture_of_the_control_panel.md).

**SSD (solid-state drive).** Fast computer storage with no moving parts, the modern replacement for spinning hard drives. The mini-ai uses a 2 TB SSD for the AI models. See [Chapter 1](01_what_you_already_have.md).

**STT (speech-to-text).** Software that listens to a sound file and writes down the words. The mini-ai uses Whisper for STT. See [Chapter 1](01_what_you_already_have.md).

---

## T

**TTS (text-to-speech).** Software that takes a piece of text and reads it out loud. The mini-ai uses Piper for TTS. See [Chapter 1](01_what_you_already_have.md).

---

## U

**USB-A.** The older rectangular USB plug that only goes in one way up. Used for connecting peripherals to the Pi. See [Chapter 0](00_welcome_and_safety.md).

**USB-C.** The newer small oval USB plug you can insert either way up. Used for power and data on the Pi 5 and the Metro RP2040. See [Chapter 0](00_welcome_and_safety.md).

**USB peripheral.** Any device that plugs into a USB port — webcam, mic/speaker, keyboard, mouse. See [Chapter 1](01_what_you_already_have.md).

---

## V

**Voltage.** How hard electricity is being pushed through a wire, like water pressure in a pipe. Measured in volts (V). The mini-ai panel uses 5 V (red wires) and 3.3 V (orange wires) throughout. See [Chapter 4](04_powering_things.md).

---

## W

**Wake word.** A name the listening device responds to, like a dog's name. When you say the wake word, the Nicla Voice notices and pokes the Pi to start listening. See [Chapter 2](02_big_picture_of_the_control_panel.md).

**Whisper.** The piece of software running on the Pi that handles speech-to-text (STT). See [Chapter 1](01_what_you_already_have.md).

**Wire-colour convention.** The rule that every wire's colour matches its function: red = 5 V, orange = 3.3 V, black = GND, yellow = I²C SDA, blue = I²C SCL, green = signal, white = anything else. See [Chapter 4](04_powering_things.md).

---

## Y

**Yahboom YB-MAE02-V1.0.** The USB microphone-array-and-speaker module on the mini-ai. The microphone picks up your voice; the speaker plays back what the AI says (via Piper TTS). See [Chapter 1](01_what_you_already_have.md).

---

*Terms introduced in chapters 5 and later will be added here as those chapters are written. For the latest version, check the file in the repository.*
