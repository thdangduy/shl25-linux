# SHL25 / AS99 — Linux 6.1 CLMR SPI Bridge C6

Date: 2026-11-07. Source/CI only. Sharp SHL25 remains OFF for charging.

## Stage C6 now implemented

The source-only C3 boot sequencer previously compiled without an
actual SPI callback adapter. C6 provides one:

- `drivers/spi/shl25-as99-clmr-spi-bridge.c`
- `drivers/spi/shl25-as99-clmr-spi-bridge.h`
- `upstream/verify_shl25_clmr_spi_bridge.py` offline regression.
- `scripts/build-upstream-linux61.sh` copies and compiles
  `CONFIG_SPI_SHL25_AS99_CLMR_BRIDGE=y`, verifies object existence.
- `.github/workflows/linux61.yml` includes C6 sources in artifacts.

**C6 driver is not attached to the existing SPI probe.** It has
no initcall, module registration, exported symbol or incoming call in
the staged kernel. It compiles with the pinned Linux 6.1 tree only.
The AS99 QUP1 SPI controller and Sharp CLMR child stay disabled in DTS.

## Exact OEM wire protocol

Source `bld010105/kernel/drivers/sharp/shdisp_lcdc/shdisp_system.c`
SHA256 `985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f`.

- Reg write: 0xC0 + BE16 register address + **BE32 value**.
  Original OEM obtains this by writing `htonl(data)` bytes into
  the transmit buffer. Example HOSTAEY=3695:
  `c0 0e 14 00 00 0e 6f`.
- Reg read: two separate `spi_sync()` messages, first
  `C2 + BE16 register`, second `C4 + four dummy bytes`; decode
  result from reply[1..4] as BE32. CS handling retained as OEM
  transfer flags. OEM read/write clocks are 20/50 MHz.
- Firmware eDRAM stream: 59,136 bytes split into 10 SPI transfers.
  Mode C7 starts with opcode C7, all subsequent chunks C8.
  Maximum 6,128 payload bytes, with 4-byte frame overhead in a
  6,144-byte scratch frame. Last three bytes are cleared for
  deterministic output, since the OEM scratch bytes are not
  explicitly initialized at the copy site. **This assumption
  remains blocked from hardware until validated.**

## Firmware origin and gate

C6 references Linux `request_firmware()` name
`sharp/shl25-as99-clmr.bin` with `CONFIG_FW_LOADER=y`.
The exact OEM binary is intentionally not committed.
The C3 executor validates SHA-256 for the loaded image before the
first SPI register write. Mismatch returns -EKEYREJECTED.

The bridge entry point requires independent board prerequisites:
PMIC supplies, CLMR GPIO reset, SPI bus, clock/PLL, firmware boot IRQ
and confirmed DET variant. The board must provide real
arm/wait IRQ callbacks. C6 deliberately does not guess PM8941
L2/LVS2 GPIO settings, create an IRQ completion on the wrong line,
enable DSI or call the bridge from the SPI probe.

Both the runtime and bootstrap CLMR sources remain isolated until
those conditions can be verified. No Linux 6.1 device boot/display
PASS is claimed.

## Validation

Source-level regression checks cover wire-endian, two-message reads,
ten C7/C8 firmware frames, chunk bounds and byte preservation, all
readiness checks and no probe activation. Linux CI cross-compiles the
actual C6 bridge as an ARMv7 object in Linux 6.1; only CI success
proves compilation, not hardware behavior.

Next: derive exact CLMR reset/IRQ and regulator wiring from the
AS99 Sharp OEM DTS and selected panel board source; build a board
power/IRQ adapter behind explicit validation, retain TWRP and native
3.4 rollback until controlled Linux 6.1 boot verification.
