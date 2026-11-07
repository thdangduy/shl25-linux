# SHL25 / AS99 Sharp Andy panel — Linux 6.1 driver port, stage A

**2026-11-07. Source + CI only.** Device powered OFF for charging.
No reboot, ADB, flash, or partition access in this stage.

## Real code delivered

- `drivers/gpu/drm/panel/panel-sharp-shl25-andy.c`: native Linux 6.1
  `mipi_dsi_driver` and `drm_panel` integration.
- Standalone command-mode, four DSI lanes, 24-bit RGB888, 1080×1920,
  60 Hz timing from original Sharp GPL.
- 28 panel-on commands and 2 panel-off commands from
  `sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi`.
  Vendor packet types 0x23/0x29 are generic short/long writes;
  0x05 is DCS short-write with an OEM padding byte.
  Per-record waits (10, 50, 120 ms) are preserved exactly.
- Raw vendor packet SHA-256:
  ON `521f981db5686f8d11ff3b04404f29f0473b1b83bc4cd5c2ad56063535b2e499`;
  OFF `c09f10cbd7e0150e77fab2922392201b033ffd19ea8c9afa596d65630aacdf10`.
- Exact packet manifest: `upstream/shl25-andy-oem-dsi.json`.
  `upstream/verify_shl25_andy_panel.py --verify` deterministically
  rebuilds the command arrays from this SHA-pinned manifest and compares
  every generated source byte, mode, lane count, RGB format and
  command-mode requirement. Original OEM DTS can be compared via
  `--extract-oem original.dtsi --write` (only intentional generation).
- `scripts/build-upstream-linux61.sh` grafts the driver into verified
  clean Linux tag v6.1, appends Kconfig/Makefile entries, forces
  `CONFIG_DRM_PANEL_SHARP_SHL25_ANDY=y` and fails CI if object
  `panel-sharp-shl25-andy.o` is missing.
- `dts/shl25-as99-display.dtsi` declares the original DSI0 panel in
  Linux 6.1 with compatible `sharp,shl25-andy`, virtual channel 0,
  explicitly `status = "disabled"`.
  `upstream/verify_shl25_peripherals.py` rejects accidental panel/DSI0
  enablement until the power/IRQ/firmware work is complete.

## Blocking dependencies — no hardware-PASS claim

The Sharp Andy command stream is **not** an independent panel power
sequence. OEM hardware also uses Sharp `mipi_spi_0` CLMR companion,
`shdisp_bdic` IR2E71Y6 backlight, regulators PM8941
L2/LVS2 and L15/LVS1 as applicable, reset GPIO, TE signal and
MDSS command-mode clock/transfer path. Those must be ported, staged
and verified before enabling the DSI panel node on Linux 6.1.

The actual handset LCD and five-finger touch passed under **Linux 3.4**,
not Linux 6.1. A successful 6.1 driver compile only establishes API
compatibility and source completeness for the DSI panel command phase.

Next: port CLMR/BDIC startup and power sequencing, firmware asset
dependencies, then validate final DSI0 graph and DRM mode/TE timing
in CI before first controlled 6.1 hardware attempt. Preserve K34
BOOT p13 recovery baseline and TWRP p14.
