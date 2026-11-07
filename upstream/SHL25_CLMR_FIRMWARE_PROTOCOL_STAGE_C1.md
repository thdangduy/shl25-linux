# SHL25 / AS99 — CLMR firmware eDRAM SPI protocol (Stage C1 offline)
Date: 2026-11-07. **Source-only and CI/offline validation. SHL25 is OFF charging.**

## OEM evidence, pinned SHA

Selected Sharp GPL 2016 driver: `kernel/drivers/sharp/shdisp_lcdc/shdisp_system.c`
SHA256 `985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f`.

Selected firmware includes `shdisp_clmr_fw.h` and `shdisp_clmr_fw_default.h`.
The latter has SHA256 `e6c4ea72cc8220dcff6b7a39df3e633cc11e394d896588362ed23519fc20b981`.
Extracted firmware image `arm_fw` is **3696 blocks × 16 bytes = 59,136 bytes**,
SHA256 `a3da76d0bbc1154a774e097bfd851026cde7a09c3983ea9315181835510145f5`.

On Windows only (not in Git, firmware, or any flashable BOOT):
`Sharp-Checkpoint-20261107/Linux61-CLMR-Firmware-Extract-20261107/SHL25_AS99_CLMR_arm_fw.bin`.

## Real transfer logic

`shdisp_SYS_clmr_sio_eDram_transfer()` uses 6,144-byte scratch buffer and
16-byte payload blocks; it reserves 4 bytes per transfer. Therefore the
**largest data payload is 6,128 bytes** per SPI message. The first
firmware download write (mode 0) has opcode `0xC7`, each later chunk
uses `0xC8`; mode 2 starts with `0xC8`. Writes use the 50 MHz SPI
clock, and the register/firmware protocol is not generic MIPI DCS.

The OEM copies payload to offset 1 but transfers `4 + payload_length`
bytes. The last 3 transmitted scratch bytes are not deliberately
initialized at that callsite. The offline test zero-pads those bytes
for deterministic vectors **without claiming that this is authorized
hardware behavior**. This discrepancy must be resolved by the full
firmware/CLMR handshaking port, rather than blindly reusing our vectors.

Full 59,136-byte image produces **10 messages**: 9 full 6,128-byte payload
segments, followed by one 3,984-byte segment (on-wire length 3,988).
All segments preserve byte ordering and the original firmware SHA.

The firmware boot path also does:
- `shdisp_clmr_fw_download()`: programs `fw_download[]`, assigns
  `SHDISP_CLMR_REG_HOSTAEY` with `htonl(arm_fw_size - 1)`, streams
  firmware in `SHDISP_CLMR_EDRAM_C7` mode.
- `shdisp_clmr_arm_sram2fw()`: programs `arm_sram2fw[]` and polls
  `SHDISP_CLMR_REG_ARMDMA` up to 100 times.
- `shdisp_clmr_arm_boot()` and `shdisp_clmr_wait4fw_boot_comp()`:
  uses an IRQ/completion with timeout and vendor failsafe checks.
- These steps depend on power/reset/PLL readiness and cannot safely
  be replaced by a single SPI write.

## Implemented regression

`upstream/verify_shl25_clmr_fw_packets.py` is pure Python (no networking,
device access, or hardware writes). It validates message segmentation,
opcodes, order, bounds, 16-byte alignment, rejection of invalid modes,
and byte-for-byte reconstruction.

Windows validation with the original `--oem-source` and
`--oem-firmware` paths PASS:
- `SHL25_AS99_CLMR_FW_EDRAM_PACKET_VECTOR_PASS`
- `SHL25_AS99_CLMR_OEM_EDRAM_SOURCE_HASH_PASS`
- `SHL25_AS99_CLMR_OEM_FW_SHA_AND_PACKETIZATION_PASS`

Linux 6.1 CI runs these deterministic tests **without including the
vendor binary**. No firmware is compiled into the new SPI driver.

## Next hard gates

1. Recover `fw_download[]`, `arm_sram2fw[]`, IRQ/completion, watchdog
   recovery and PLL/reset timing exactly from the AS99 OEM source.
2. Add a stateful CLMR firmware loader only once BDIC VSP/VSN
   power sequencing, PM8941 parent rails and board reset polarity
   are correctly wired. Separate pre-boot register access gates from
   post-firmware DSI transport readiness.
3. Integrate VCOM/gamma with validated per-device calibration (not
   constant placeholder tables), then allow panel initialization.
4. Preserve USB + TWRP rollback and validate on real device in
   controlled stages; **no Linux 6.1 hardware PASS yet**.
