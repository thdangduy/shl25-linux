# SHL25 Linux 6.1 — BDIC via Sharp CLMR firmware queue (Stage C2)

2026-11-07. Offline source/fixture work only; no device access. This is
**not** a functional Linux 6.1 BDIC or backlight driver.

## Correct architecture — NOT a naive Linux I2C write

Sharp selected OEM `drivers/sharp/shdisp_lcdc/shdisp_system.c`
(SHA256 `985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f`)
implements most `shdisp_SYS_bdic_i2c_write/read/mask_write/multi_write`
via `shdisp_FWCMD_buf_add()` and `shdisp_FWCMD_doKick()`.
This queues commands to the CLMR's embedded ARM firmware: source calls
`shdisp_SYS_clmr_sio_eDram_transfer(SHDISP_CLMR_EDRAM_C8,...)`, then
writes `SHDISP_CLMR_REG_ARMSETINT1` and waits for firmware command
completion/handshake. It is NOT equivalent to a standalone Linux
`i2c_transfer()` on an assumed bus. Keep a direct BDIC Linux I2C
controller node disabled until its actual wiring and operating mode
are independently verified.

Sharp `shdisp_lcdc/shdisp_system.h` SHA256:
`490f3d0f8a6b1763cb888edb95b7d96f89cb102977092e54c86a7c6a044169b2`.
Exact firmware opcodes:
- `0x50` BDIC I2C one-byte write;
- `0x51` masked write;
- `0x52` multi-write (1..20 bytes);
- `0x54` one-byte read.

The OEM firmware payload carries BDIC slave address **0xA8 as an
8-bit address**; corresponding 7-bit address is `0x54`. Do not insert
`0xA8` directly as a Linux I2C `reg` property.

FWCMD API domains: BKL=`0x30`, PROXSENSOR=`0x50`. Each item is
`opcode, ((API + kick_count) & 0x7f), payload_len_le16, payload`;
`kick_count` cycles from 1..15. Firmware command completion sets
the high bit of the last command's interrupt byte, after appending
`FE 0F` terminator and `FF` padding to 16-byte alignment.

Example single write, API=PROXSENSOR, register 0x12, value 0x34:
`50 d1 03 00 a8 12 34 fe 0f ff ff ff ff ff ff ff`
(16-byte offline reference only; **never send directly to uninitialized
CLMR**).

## Confirmed BDIC power sequencing branches

`shdisp_bl71y6.c` calls `shdisp_bdic_vsp_on` to turn on LCD
positive supply and chooses `shdisp_bdic_vsn_on_ts1` for chip version
0, otherwise `shdisp_bdic_vsn_on` for negative supply.
The selected register tables and timing originate in the correct
AS99 variant, not generic Sharp BDIC defaults. Firmware queue transport,
the CLMR firmware handshake and per-chip revision must be operational
before these power tables are enabled.

## Implemented CI-level offline test

`upstream/verify_shl25_bdic_fwcmd.py` checks:
- OEM command codes, 8-bit slave address and API class;
- command length endian, item flag and counter, terminator/alignment;
- 1-byte write, mask write, read and bounded multi-write vectors;
- rejection of unsupported opcodes, invalid lengths and unverified
  command API domains.

Windows verification was additionally run against both SHA-pinned
original source/header files using `--oem-header` and `--oem-source`.
Source-only CI tests do not require or embed proprietary firmware,
and perform no SPI/I2C calls. These PASS flags are not hardware results.

## Next required changes

1. Port CLMR firmware loader eDRAM stream, ROM-to-SRAM transfer,
   reset/PLL, boot-complete IRQ and timeout state machine.
2. Add firmware queue transport and BDIC register tables with chip
   revision detection; separate pre-firmware and post-firmware access
   gates to avoid an impossible circular dependency.
3. Bind real BDIC power sequencing, error/status checks and PM8941
   L2/LVS2 rails, then connect guarded Andy panel VCOM/gamma runtime.
4. Keep all corresponding DT nodes disabled until real device test
   readiness. Native Linux 3.4 LCD/touch hardware PASS remains
   independent from Linux 6.1 build/driver PASS.
