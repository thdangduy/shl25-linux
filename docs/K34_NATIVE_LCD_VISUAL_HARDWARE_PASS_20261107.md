# Sharp SHL25 / AS99 — native Linux 3.4 LCD visual hardware PASS

Date: 2026-11-07, 19:48 +07. Windows host: S9X0R0, native USB CDC ACM COM21.

## Definitive visual evidence (reported by device owner)

The device owner observed all **three lines** on the physical phone LCD:

- `SHL25`
- `LINUX 3.4`
- `LCD TEST`

The owner described **a red rectangular frame** around the content and a **pixel-style font**. This was observed during a repeat run of the test, not inferred from a framebuffer ioctl or Windows log. Before this proof, the stock SHARP splash had disappeared and the screen was black with backlight on.

**Verdict:** native Linux 3.4 physically updates the Sharp handset's display with custom framebuffer graphics. This demonstrates a functional visible path from standalone Linux user space to display hardware, when an explicit force refresh is requested. This does **not** prove that touch events, a window compositor, all SHDISP power sequences, or Linux 6.1 display support are already working.

## Reproducible technical procedure

- Native BOOT: `SHL25-K34-NATIVE-BUSYBOX-SHELL-QEMU-v5.img`
- Verified p13 SHA256 from earlier flash:
  `b0d52a1fce11070791607b14e476ca8a67209483fb7cafcfb7209b5be22b849f`.
- OEM Sharp GPL Linux 3.4 kernel, with native ARMHF BusyBox PID1/shell.
- Source display driver `drivers/video/msm/mdss/mdss_mdp_overlay.c`
  requires `FB_ACTIVATE_FORCE` or `FB_ACTIVATE_VBL` for MDP kickoff.
- Diagnostic framebuffer writer `/sbin/fbtext` draws a red framed
  `SHL25 / LINUX 3.4 / LCD TEST` message into `/dev/graphics/fb0`,
  holds about 5 seconds, and restores original pixels.
- Static no-libc ARMv7 binary `k34-fbforce` (repo
  `diagnostics/k34_fbforce.c`) calls `FBIOPUT_VSCREENINFO` with
  `FB_ACTIVATE_FORCE`, preserving x/y resolution and color format.
- Binary SHA256:
  `a292802c5aea5c5eb64adcb0f3ea7b3c6ce412c2f05ffc31b0835a6a38ed46bd`.
- Binary transferred to volatile `/tmp/k34-fbforce` over CDC ACM COM21
  in short base64 chunks; decoded SHA256 matched exactly.
- Repeat Windows script:
  `Sharp-Checkpoint-20261107\\SHL25_LCD_VISUAL_REPEAT_10.ps1`.
- Test procedure per loop:
  `(/sbin/fbtext & sleep 1; /tmp/k34-fbforce; wait; /tmp/k34-fbforce)`
- Log:
  `Sharp-Checkpoint-20261107\\SHL25_LCD_VISUAL_REPEAT_10.log`.
- Result: **10/10 DRAWN, 10/10 RESTORED, 20/20 force ioctl successes**.
- At test completion, shell exited normally to native PID1 diagnostic
  console, and `info` returned `Linux 3.4.0`.
- Windows COM21 `USB Serial Device` remained PnP `OK`.

## Why the older tests were inconclusive

The first version of `fbtext` only modified framebuffer RAM and restored
it. Sysfs `fb0/pan=0,0` returned 0 but did not necessarily trigger an
MDP commit because the activation flags were absent. The original splash
disappeared and the screen became black/backlit. A verified FORCE ioctl
then exercised the driver's kickoff path and yielded owner-confirmed
red-framed text on the real screen.

## Next gates

1. Capture **actual touch input events** from registered Sharp
   `shtps_rmi` driver (previously identified as `/dev/input/event3`
   on SPI2.0); confirm EV_ABS X/Y changes and EV_SYN with real touches.
2. Use Linux 3.4 as a measured baseline for Sharp display and touch
   clock, power, DMA, SPI and DSI dependencies.
3. Port proven hardware dependencies to Linux 6.1 in controlled stages.
   Do not treat this kernel 3.4 result as Linux 6.1 boot PASS.

Safety: no BOOT/Recovery changes in the LCD proof; TWRP p14 untouched;
no Windows driver modifications, no VPS-ARM. Known inaccurate TWRP
battery percentage is not a valid charge measurement.
