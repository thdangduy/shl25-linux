# SHL25 / AS99 — Sharp Andy CLMR runtime port, stage B1 (Linux 6.1)

Date: 2026-11-07. Scope: source and CI build **only**; handset OFF for charging.

## Verified original driver selection

Original GPL source:
`Sharp-OEM-Sources/bld010105/kernel.tar.gz`.

Sharp `arch/arm/configs/deckard_as99_defconfig` enables
`CONFIG_MACH_DECKARD_AS99=y`,
`CONFIG_USES_SHLCDC=y`,
`CONFIG_SHDISP=y`, and
`CONFIG_SHDISP_PANEL_ANDY=y`.

The board-specific Andy/CLMR code to port is
`kernel/drivers/sharp/shdisp_lcdc/shdisp_andy.c`, which for
`CONFIG_MACH_DECKARD_AS99` selects
`kernel/drivers/sharp/shdisp_lcdc/data/shdisp_andy_data_as99.h`.
The other source
`kernel/drivers/sharp/shdisp/shdisp_andy.c` selects the
DL60/AL15 variants and MUST NOT be substituted into AS99 runtime
migration. Both names exist in the OEM GPL tree; check their
Kbuild/conditional selection before using any shared code.

## Actual stage B source and provenance

- Generator: `upstream/build_shl25_andy_runtime.py`.
- JSON: `upstream/shl25-andy-as99-runtime.json`.
- Linux 6.1 C arrays:
  `drivers/gpu/drm/panel/shl25-andy-as99-runtime.h`.
- Linux 6.1 DRM code:
  `drivers/gpu/drm/panel/panel-sharp-shl25-andy.c`.
- Vendor source SHA-256:
  `shdisp_andy_data_as99.h` =
  `65773f9045ff997cc900d4ad80f000cf190065bfbdb874ac23293de52c67557d`.
- The exact vendor `shdisp_lcdc/shdisp_system.h` defines
  `WAIT_1FRAME_US (16666)` and hashes to
  `490f3d0f8a6b1763cb888edb95b7d96f89cb102977092e54c86a7c6a044169b2`.
- Generated JSON fixture SHA-256:
  `e4ea0a7d6e0a103195bf49204ea159453aaae10b49f8192c6e7332fcabcae6a1`.
- The C generator accepts only pinned hash-matched original sources
  and checks each original command type/length/source payload.
  In CI, it verifies exact checked-in JSON fixture and generated
  C header content and SHA-256; records are not transcribed manually.

### Verified data volume and hardware-dependent fields

- **16 named runtime groups**, **662 exact DCS records** extracted.
  Includes alternate silicon revision and flicker-adjusted variants.
- **471 records** depend on dynamic VCOM/gamma/related copies
  or otherwise require per-device calibration.
  These carry `calibration_required=true`; the original template
  values are **not authorized for direct hardware programming**.
- All command wait expressions resolved from the actual OEM
  wait macro. The original off sequence uses **1 frame (16,666 us)**
  and **4 frames (66,664 us)**; no delay guessed.
- Kbuild of stage B explicitly copies the generated C header into
  the pinned v6.1 source tree and builds it into the DRM panel object.
  Linux compile-time assertions cover 662 total records and 363
  gamma records.
- Firmware-assisted DSI writes via Sharp CLMR are **not equivalent**
  to ordinary host `mipi_dsi_dcs_write_buffer()` calls. The
  original runtime uses `MIPI_DSI_COMMAND_MLTPKT_TX_CLMR`,
  CLMR host high-speed clocks and firmware command queues.
  Transport protocol and power rails must be ported, not bypassed.

### Fail-closed execution rule

The Linux 6.1 DRM panel `prepare()` now checks runtime readiness
before sending **any DSI command**. The three readiness states for
CLMR power, per-device calibration and CLMR transport intentionally
remain FALSE (not set by any code). The function returns
`-EOPNOTSUPP` on attempted preparation.

The board DT `dts/shl25-as99-display.dtsi` still declares both
panel and parent DSI0 as disabled. This guards against accidentally
powering a panel with the wrong reset or VCOM sequence.

### What is NOT yet done

- No CLMR SPI + firmware transport driver for Linux 6.1.
- No BDIC/IR2E71Y6 backlight, reset GPIO85/Andy VDD GPIO69
  power-state driver, PM8941 L2/LVS2 consumer sequencing.
- No per-unit VCOM/gamma loaded from stock NVRAM/SMEM or validated
  with Sharp's original checksum logic.
- No device code (TS1/TS2/TS3) readout and runtime branch selection.
- No Linux 6.1 cold boot, DRM display, touch or other hardware PASS.

Next: implement CLMR/BDIC backend and calibration source, then remove
the fail-closed guard **only after** verified test coverage and
controlled on-device checks. Preserve K34 BOOT and TWRP Recovery.
