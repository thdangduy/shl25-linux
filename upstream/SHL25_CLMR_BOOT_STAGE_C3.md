# SHL25 AS99 — Stage C3 CLMR ROM-to-firmware boot sequence

Date: 2026-11-07. **Source/CI only**. No device flashing or kernel boot test.

## Source and implemented code

Source: Sharp GPL `bld010105/kernel.tar.gz`, selected
`drivers/sharp/shdisp_lcdc/shdisp_clmr.c` SHA256
`399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0`
and selected `shdisp_clmr.h` SHA256
`1eb86c4756fd1afb5b815eb2739e2a5170f51ac4f9279b3917201edcc1c6249d`.
The **shdisp_lcdc** board-specific implementation is authoritative,
not `drivers/sharp/shdisp` variants.

- `upstream/build_shl25_clmr_boot.py`: hash-pin both OEM files,
  extract register and value expressions, reject unknown operations,
  map actual register addresses, generate deterministic fixture + C header.
- `upstream/shl25-as99-clmr-boot.json`: exact values and source provenance.
- `drivers/spi/shl25-as99-clmr-boot-tables.h`: generated and checked.
- `drivers/spi/shl25-as99-clmr-boot.{h,c}`: source-verified
  callback-based boot executor, **no hardware adapter or probe hook**.
- `upstream/verify_shl25_clmr_boot_sequence.py`: offline boot order,
  two hardware DET variants, DMA bound/failure, IRQ-order regression.

## OEM boot sequence preserved

1. `fw_download[7]`: host CLMR register configuration, including
   HOSTBASE=0x7CE0; then HOSTAEY=3696-1=3695.
2. `shdisp_SYS_clmr_sio_eDram_transfer(mode C7)`: exact 59,136
   bytes (previous Stage C1 validates its 10-command C7/C8 framing).
3. `arm_init[6]`: use the verified `SHDISP_NOT_SUPPORT_DET`
   variant. Initial interrupt mask is an OR operation:
   DET supported `0x30000`; DET not supported `0x10000`.
4. `arm_sram2fw[7]`: starts ARM DMA using CLMR ARMDMA=0x1824.
   Poll bit0 at most 100 times. If never clear, return timeout.
5. Prepare boot-completion IRQ **before** writing
   ARMHOSTSYS=0x13 via `arm_boot[1]`.
6. Wait for boot-completion IRQ up to 2100ms (OEM constant).

All register writes in the executor take host-order u32. A future
board SPI adapter must serialize the value to Sharp's correct 4-byte
big-endian register wire order (C0), not cast unaligned memory. The
current Stage C0 SPI driver still has no readiness setter or boot
adapter and has **no physical device access** in probe.

## Critical gating / not done

Earlier C0 wrongly required `firmware_running=true` even for
pre-firmware ROM register access, which is logically impossible.
C3 separates `ensure_boot_ready()` (board power/PLL gates) and
`ensure_runtime_ready()` (boot + firmware-running).
All flags are FALSE and there are still no setter or activation paths.

The C3 executor requires independently validated PMIC rails,
reset polarity, SPI, PLL/clock, firmware integrity and IRQ, plus an
explicit DET branch. It is **not called anywhere by the registered
CLMR SPI driver**, intentionally. Firmware SHA is not computed inside
the C3 executor yet: its integrity flag is a future adapter contract,
not a completed trust/firmware-loading implementation.

Remaining before hardware use: PM8941 L2/LVS2 supply/regulator
sequencing, CLMR GPIO reset semantics, valid IRQ mapping/handshake,
firmware request/cryptographic SHA check, SPI transport adapter,
BDIC commands through CLMR firmware, and per-device Andy VCOM/gamma.
Panel DSI and CLMR SPI child continue `status="disabled"`.
Real Linux 6.1 boot, display, five-finger touch and battery still
require separate on-device tests. Native K34 PASS does not transfer.

Known-good BOOT and TWRP hashes stay immutable. No new flash image,
no modification of device recovery.
