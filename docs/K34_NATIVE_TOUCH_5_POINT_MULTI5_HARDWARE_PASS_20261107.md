# Sharp SHL25 / AS99 — 5-point coordinate and true 3/4/5-finger hardware PASS

Date: 2026-11-07 (20:12–20:13 ICT). Device SHL25/AS99.
Authorized host S9X0R0, native standalone Linux 3.4 (v5) over CDC ACM COM21.
No Android framework, BOOT flash, TWRP changes, VPS-ARM, or Windows driver installs.

## Test method

Program: `diagnostics/k34_touch_points.c` on branch
`feat/shl25-k34-hwprobe-20261107`. GitHub CI run **42375595863 SUCCESS**,
source commit **559f0c5**, compiled ARMv7 EABI static no-libc, QEMU ABI check PASS.
Final ARM executable SHA256
`6d3565a5445ad62068e23ba13cd460df7e13e56185aa1cb5387f23d0101a6708`,
8,684 bytes. Verified identical SHA after segmented transfer through COM21
to volatile `/tmp/k34-touch-points`. Boot partition never changed.

The application draws five circles numbered 1–5 on the Sharp LCD,
generates a reproducible-but-jittered target layout, and reads
`/dev/input/event3` (Sharp `shtps_rmi` SPI touchscreen).
Each target has radius/tolerance **116 physical pixels**. Successful
single-target touches require X/Y within the circle and release
between targets. Simultaneous multi-touch success requires separate
positions matching the indicated unique targets in one
`EV_SYN/SYN_REPORT` frame. Type A `SYN_MT_REPORT` and Type B
`ABS_MT_SLOT=0x2F` are supported. The driver sample uses
`ABS_MT_TOUCH_MAJOR=0x30` to signal contact width, NOT slot ID.

Display path: `/dev/graphics/fb0` (1080x1920, RGB offset 24/16/8),
`FBIOPUT_VSCREENINFO` with `FB_ACTIVATE_FORCE`, already visually
verified by device owner. App restores previous framebuffer pixels
on normal completion. Input reads never use EVIOCGRAB.

## Exact 5 single-target test result — PASS 5/5

`d²=(Xobserved-Xtarget)²+(Yobserved-Ytarget)²`; threshold is
`116²=13456`. Every observed d² is below threshold:

| Point | Target (X,Y) | Touch (X,Y) | Squared error (px²) | Approx error (px) | Verdict |
|---|---|---|---:|---:|---|
| 1 | (222, 483) | (177, 458) | 2650 | 51.5 | PASS |
| 2 | (768, 503) | (797, 522) | 1202 | 34.7 | PASS |
| 3 | (584, 912) | (594, 916) | 116 | 10.8 | PASS |
| 4 | (253, 1494) | (313, 1492) | 3604 | 60.0 | PASS |
| 5 | (839, 1502) | (829, 1551) | 2501 | 50.0 | PASS |

No coordinate rotation/transposition was needed to match the LCD
targets. These values demonstrate basic position mapping with
**116 px tolerance**; they are not a claim of subpixel calibration.

## True simultaneous multi-touch — PASS 3/4/5

The following messages are emitted only after multiple positions from
the same frame are checked against *distinct* targets:

```text
SHL25_TOUCH_MULTI_PASS a=3 b=5 c=23 d=21
SHL25_TOUCH_MULTI_PASS a=4 b=5 c=31 d=27
SHL25_TOUCH_MULTI_PASS a=5 b=5 c=31 d=31
SHL25_TOUCH_ALL_PASS a=5 b=4 c=5 d=300
```

Field meanings in MULTI_PASS: `a`=minimum matched targets required,
`b`=number of contact records in that frame,
`c`=observed target bitmask, `d`=expected bitmask.
- MULTI3: expected targets 1+3+5 (mask 21), observed mask 23
  includes those 3 targets, PASS.
- MULTI4: expected 1+2+4+5 (mask 27), observed mask 31
  includes those 4 targets, PASS.
- MULTI5: 5 simultaneous contacts and **all 5 target bits set**
  (observed mask 31, expected mask 31), PASS.
- The `d=300` in the ALL_PASS summary is the number of nonmatching
  intermediate input frames, NOT a count of test failures. It does
  not negate the verified 5/5 and multi 3/4/5 passes.

The test's device-side timeout was not reached; it exited automatically
with status ALL_PASS and the host monitor returned exitCode 0.

## Evidence / recovery

Windows evidence:
- `Sharp-Checkpoint-20261107/SHL25_TOUCH_POINTS_LIVE_RESULT.log`
- `Sharp-Checkpoint-20261107/SHL25_TOUCH_POINTS_UPLOAD_RAM.log`
- Device RAM file `/tmp/shl25-touch-points.log` (may disappear after reboot).

After the test, COM21 was still PnP OK. A short `exit` command returned
the shell to native Linux PID1 diagnostic console. Native Linux 3.4 v5
is still running with its original unchanged BOOT image.

## What is proven / next

**PASS:** 1080x1920 LCD renders standalone Linux UI, coordinates of five
actual touches align with corresponding displayed targets (116 px
tolerance), and the touch driver reports five concurrent distinct
coordinates within a single input frame. CDC ACM and BusyBox ash work
without Android. This is direct hardware evidence for the SHL25 driver
and input path on Linux **3.4**.

**NOT PROVEN:** touch latency benchmarking, exact calibration against
a professional digitizer, five-finger stress over time, suspend/resume,
or working LCD and touch drivers under Linux **6.1**. Next is to port
the verified OEM 3.4 regulator, SPI IRQ, MDSS/DSI and Sharp panel/
touch dependencies incrementally into Linux 6.1 while preserving
TWRP Recovery p14 and known BOOT rollback.

Note: Earlier file `K34_NATIVE_TOUCH_EVENT_HARDWARE_PASS_20261107.md`
incorrectly called EV_ABS code 0x30 a slot. The corrected mapping
is TOUCH_MAJOR=0x30, SLOT=0x2F. Do not infer multi-touch from
TOUCH_MAJOR alone; this test uses distinct target coordinates in
the same SYN_REPORT frame.
