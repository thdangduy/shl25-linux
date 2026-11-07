# Sharp SHL25 / AS99 — native Linux 3.4 raw touch events PASS

Date: 2026-11-07; device SHL25/AS99, standalone Linux 3.4, Windows S9X0R0 COM21.

## Verified observation

The owner confirmed the LCD visibly rendered `SHL25 / LINUX 3.4 / LCD TEST`
in a red rectangular frame and pixel-style letters. The evidence is
recorded in `docs/K34_NATIVE_LCD_VISUAL_HARDWARE_PASS_20261107.md`.

During a new controlled touch capture, native ARMHF BusyBox shell read
`/dev/input/event3` using a 20-second bounded, read-only command:

```sh
/bin/busybox timeout 20 /bin/busybox hexdump -C -n 512 /dev/input/event3
```

The device returned **512 bytes = 32 complete Linux ARM32 input_event
records (16 bytes each)**. These are real kernel input events on the
native OS, not device-tree claims or host emulation.

Raw capture on Windows (preserve as forensic source):
`Sharp-Checkpoint-20261107/SHL25_NATIVE_TOUCH_EVENT3_LIVE_20261107.txt`

## Decoded kernel input events

On this ARMv7 Linux 3.4 system, each event is:
`struct timeval {int32 sec; int32 usec;}; uint16 type; uint16 code; int32 value`,
little-endian, total 16 bytes.

Verified Linux input event codes:
- `EV_ABS=3, ABS_MT_SLOT=0x30` (multitouch slot).
- `EV_ABS=3, ABS_MT_POSITION_X=0x35`.
- `EV_ABS=3, ABS_MT_POSITION_Y=0x36`.
- `EV_ABS=3, ABS_MT_PRESSURE=0x3a`.
- `EV_ABS=3, ABS_MT_TRACKING_ID=0x39`, value `-1` denotes release.
- `EV_SYN=0, SYN_REPORT=0`, end of input frame.

Selected records decoded directly from the 512-byte capture:

| Frame | Slot | X | Y | Pressure |
|---|---:|---:|---:|---:|
| 1 | 12 | 650 | 405 | 39 |
| 2 | 15 | 677 | 314 | 37 |
| 3 | 12 | 711 | 212 | 34 |
| 4 | 11 | 737 | 160 | 32 |
| 5 | 15 | 755 | 154 | 24 |
| 6 | 11 | 756 | 151 | 16 |

A following event reports `ABS_MT_TRACKING_ID=-1` and `SYN_REPORT`.
The input stream contains 6 position frames and a release frame. Slot
IDs vary: the six points **must not** be characterized as one finger's
continuous trajectory without tracking-ID correlation or more history.

## Real hardware / software conclusions

PASS:
- The registered `shtps_rmi` touchscreen input path produces actual
  `EV_ABS` multitouch position, pressure and `EV_SYN` events on
  native Sharp Linux 3.4, rather than merely enumerating as an input
  device.
- The physical Sharp LCD separately displayed native framebuffer
  graphics (owner-confirmed).
- USB COM21/BusyBox shell are functional while collecting touch events;
  no Android framework or ADB in native boot.

NOT YET PROVEN:
- Visual touch cursor/gesture UI, rotation/calibration accuracy, complete
  multitouch finger tracking, touch IRQ latency under load, long-term
  suspend/resume behavior.
- Linux 6.1 boots on this hardware or has working LCD/touch drivers.

## Engineering next steps

1. Add userland input visualization (crosshair/touch dots) using raw
   event streams and framebuffer force-kickoff; prove mapping on LCD
   directly. Keep a bounded, read-only input capture and restore pixels.
2. Preserve OEM source/boot evidence: touchscreen `shtps_rmi` SPI2.0,
   framebuffer `mdssfb_90000`, Sharp MIPI DSI command-mode panel and
   force-refresh mechanism in `mdss_mdp_overlay.c`.
3. Port clock, pinctrl, regulator, SPI/input and DSI/MDP dependencies
   incrementally into Linux 6.1, testing in QEMU/CI first, then on device
   with verified TWRP rollback.

Safety: current BOOT p13 v5, verified SHA256 from previous readback
`b0d52a1fce11070791607b14e476ca8a67209483fb7cafcfb7209b5be22b849f`.
TWRP Recovery p14 untouched; no flash or reboot for LCD/touch tests.
No Windows driver changes, no VPS-ARM.
