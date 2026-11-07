# Sharp SHL25 / AS99 — hardware-first Linux bring-up, 2026-11-07

## Scope
Target is a native Linux mobile OS, ultimately using Linux **6.1** with
Sharp-specific drivers and DTS sourced from official Sharp GPL archives.
Do not use Android/AOSP as OS; Android BOOT container format is a bootloader
compatibility detail only. No VPS-ARM. Work only on the owner-authorized
S9X0R0 Windows machine and Sharp SHL25 serial 356594053328037.

## Live validation on TWRP Linux 3.4
- TWRP kernel `3.4.0`, ARMv7 Qualcomm MSM8974PRO-AB; root ADB in recovery.
- Tool `diagnostics/k34_hwprobe.c` built with static ARMHF cross GCC in
  GitHub Actions run 42358958014: **SUCCESS**.
- Build branch `feat/shl25-k34-hwprobe-20261107`; commit `8f63f44`.
- Artifact ID 13569245767; ZIP SHA256
  `b49a85e438f734322a623bade8c73bec6740cf5623477c4b31cbd9eedae37b28`.
- ELF 424296 bytes; SHA256
  `683d9b15c5a2df8e4f0c79491d72fa469c5fb98462e769424dbfedb585fc6fac`.
  Windows ZIP + ELF hash PASS, phone copy in **/tmp tmpfs** hash PASS.
- Executed in /tmp, no BOOT/Recovery/partition modifications.
  `SHL25_K34_HWPROBE_RESULT fb0=PASS touch=PASS`, exit code 0.

## Exact ioctl output
- `/dev/graphics/fb0`: `mdssfb_90000`, xres=1080, yres=1920,
  virtual=1088x3840, bpp=32, line_length=4352,
  smem_len=16711680,
  RGBA offsets/lengths=R24:8 G16:8 B8:8 A0:8, rotate=0.
- `/dev/graphics/fb1`: `mdssfb_a0000`, xres=1920, yres=1080,
  virtual=1920x2160, bpp=32, stride=7680, smem_len=16588800.
- `/dev/input/event3`: `shtps_rmi`, ABS_MT_POSITION_X [0,1079],
  ABS_MT_POSITION_Y [0,1919], ABS_MT_TRACKING_ID [0,65535].
- Other input nodes opened: event0 qpnp_pon, event1 proximity,
  event2 shgrip, event4 shtps_key.
- This establishes working **ioctl metadata interface** under recovery.
  It does NOT prove drawing a new frame, actual finger-down events,
  cold-boot panel initialization or Linux 6.1 driver functionality.

## Matched OEM 2016 Sharp bld010105 source (not 2014)
- `deckard_as99_defconfig` selects
  `CONFIG_SHDISP=y`, `CONFIG_SHDISP_BDIC_71Y=y`,
  `CONFIG_SHDISP_PANEL_ANDY=y`, `CONFIG_FB_MSM_MDSS=y`,
  `CONFIG_TOUCHSCREEN_SHTPS=y`,
  `CONFIG_SHTPS_SY3000_TM2979_001=y`.
- Touch implementation is
  `kernel/drivers/sharp/shtps/sy3000_2/shtps_rmi_spi.c`,
  NOT `sy3000_1`; mapping from Sharp Makefile.
- Sharp touch wiring in `sharp-as99.dtsi`:
  SPI2 `f9924000`, max 400 kHz, PM8941 GPIO30 reset,
  PM8941 L15 (3.0-V reference label), LVS1 (1.8-V reference label).
  Actual rail voltage/regulator enable timing must still be confirmed;
  these labels alone are not runtime measurements.
- Display stack:
  `shdisp_andy.c`, `shdisp_bl71y6.c`, `shdisp_pm.c`,
  `shdisp_kerl.c`, Qualcomm `mdss_dsi_panel.c`;
  board includes Sharp Andy 1080p command-mode panel,
  CLMR, IR2E71Y6 BDIC.
- TWRP `dmesg` confirms Sharp command-mode panel probe,
  FrameBuffer[0] 1080x1920 registration, touch event3 and eMMC.
- PM8941 S1 1.3V, S2 2.15V, S3 1.8V, L6 1.8V,
  L20 2.95V were observed enabled in sysfs.
- `fb0/show_blank_event` reports `panel_power_on = 0`
  although boot log shows `Panel already on`: must not mistake
  registration for proven cold-boot panel power sequence.

## Local evidence on S9X0R0
`C:\Users\Admin\Downloads\SHL25-Linux-Lab\Sharp-Checkpoint-20261107\`
- `TWRP-K34-Hardware\`: dmesg, kernel memory, PMIC rails,
  input, framebuffer, SDHC, I2C/SPI, USB/sysfs evidence.
- `SHL25_KERNEL34_HARDWARE_BASELINE.md`
- `SHL25_KERNEL34_HARDWARE_MATRIX.json` (16 components, input SHA256)
- `SHL25_OEM2016_DRIVER_SOURCE_MAP.json` (actual GPL tar members)
- `SHL25_OEM2016_CONFIG_BINDING_EVIDENCE.json`
- `K34-HWProbe-CI-42358958014\SHL25_K34_HWPROBE_LIVE_RESULT.txt`

## Next engineering gates
1. Build a native **kernel 3.4** diagnostic userspace that retains shell
   access and can draw a controlled framebuffer test pattern.
   Prefer a RAM-only functional test when feasible before any BOOT flash.
2. Confirm actual touch events and panel cold-boot power/reset/DSI sequence
   using OEM sources and live evidence, not guesses. TWRP retains control.
3. Isolate Linux 6.1 port on a new branch: CPU/DDR/bootloader FDT handoff,
   PM8841/PM8941, eMMC, USB transport, then Sharp DSI/CLMR/BDIC and touch.
4. Demand early boot evidence and verified BOOT p13 rollback before any 6.1
   live test; preserve TWRP Recovery p14 unchanged.
5. The owner's SHL25 battery was recently charged and TWRP percent display
   is unreliable; never infer state of charge from that percentage.

## Device safety
Only /tmp tmpfs was used for the live tool. No flash, erase, wipe,
modification of BOOT/Recovery, panel writes or user-data changes.
Existing Linux 6.16 V5 BOOT remains as previously documented.
