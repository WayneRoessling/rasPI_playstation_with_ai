# Archive

Superseded plans and references, kept for history. Nothing here describes
the current setup — start from the [README](../README.md) and the active plan,
[PLAN-MAI-003](../active_plans/PLAN-MAI-003_NVMe_Migration_and_Full_Setup.md).

| File | What it was | Why archived |
|------|-------------|--------------|
| [plans/PLAN-MAI-001_Pi5_Platform_Build.md](plans/PLAN-MAI-001_Pi5_Platform_Build.md) | Manual, phase-by-phase Pi 5 build on a 1TB microSD | Automated by `setup_all.py`; storage moved to USB-NVMe (PLAN-MAI-003) |
| [plans/PLAN-MAI-002_Reflash_and_Full_Setup.md](plans/PLAN-MAI-002_Reflash_and_Full_Setup.md) | Reflash the SD card and run the automated setup | Abandoned — the SD card was counterfeit |
| [designs/DESIGN-MAI-001_System_Architecture.md](designs/DESIGN-MAI-001_System_Architecture.md) | First architecture draft (voice assistant only) | Predates the scenario console; names components that were never built |
| [reference/cmdline_normal.txt](reference/cmdline_normal.txt), [reference/cmdline_recovery.txt](reference/cmdline_recovery.txt) | Kernel command lines for normal / recovery boot of the SD card | Tied to the discarded card's PARTUUID; the NVMe boot uses Imager's defaults |
