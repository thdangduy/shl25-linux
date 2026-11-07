# SHL25 / AS99 CLMR register SPI transport — Linux 6.1 stage C0

Date: 2026-11-07. Source/CI only. Phone OFF for charging.

## Correct original sources and physical transport

From the Sharp GPL `bld010105` selected
`drivers/sharp/shdisp_lcdc/shdisp_system.c`:
SHA-256 `985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f`.

Physical bus: BLSP1 QUP1 at `spi@f9923000`, chip-select 0,
DT compatible `sharp,mipi_spi_0`, SPI mode 3 plus CS high.

Original protocol:
- **Write:** opcode `0xC0`, 16-bit register address in big-endian,
  four bytes of value in native little-endian order, 50 MHz.
- **Read:** first message `0xC2` + 16-bit big-endian register address,
  second distinct message `0xC4` + four dummy bytes at 20 MHz;
  result is the last four received bytes (`rx[1:5]`).
- Separate `spi_sync()` calls for the read message are preserved, not
  replaced by a single chip-select-continuous transfer.
- Firmware eDRAM streaming opcodes `0xC7`/`0xC8` are a separate
  transport and **not implemented** in this stage.

## Real Linux 6.1 implementation

- `drivers/spi/spi-shl25-as99-clmr.c`: actual SPI driver with
  Linux 6.1 `spi_sync_transfer()` and mutex-serialized register
  reads/writes. No unsafe unaligned integer accesses.
- `scripts/build-upstream-linux61.sh`: stages the driver inside
  the pinned upstream Linux v6.1 tree; Kconfig
  `CONFIG_SPI_SHL25_AS99_CLMR=y`, compilation and artifact
  object checks.
- `upstream/verify_shl25_clmr_spi.py`: source/DT safety and exact
  protocol-frame regression checks. These checks are NOT proof of
  a working CLMR on real hardware.
- `dts/shl25-as99-peripherals.dtsi`: both SPI1 bus and CLMR node
  remain `status="disabled"`.

**Fail-closed:** Every CLMR register read/write checks three state
flags, `bdic_power_validated`, `firmware_running` and
`clmr_pll_clock_ready`. These default to FALSE and have no enable path
yet. The SPI probe itself performs no register I/O, reset, firmware
download or regulator actions. No CLMR command will execute under
this staged configuration.

## Firmware provenance (local asset only)

Selected OEM sources:
`drivers/sharp/shdisp_lcdc/shdisp_clmr_fw.h` and
`shdisp_clmr_fw_default.h`.
The default header has SHA-256
`e6c4ea72cc8220dcff6b7a39df3e633cc11e394d896588362ed23519fc20b981`.
Its `arm_fw` image extracts to **59,136 bytes**, SHA-256
`a3da76d0bbc1154a774e097bfd851026cde7a09c3983ea9315181835510145f5`.
OEM `arm_fw_size=3696` blocks of 16 bytes, matching 59,136 bytes.
OEM `arm_fw_base=0x7CE0`, `arm_fw_start=0x0`; neither may be treated
as arbitrary physical DDR addresses.

Local Windows file only:
`Sharp-Checkpoint-20261107/Linux61-CLMR-Firmware-Extract-20261107/SHL25_AS99_CLMR_arm_fw.bin`.

The firmware binary is intentionally not included in this source
commit, Linux 6.1 initramfs or a flashable image.

## Required before any hardware enablement

Implement the separate CLMR firmware boot/eDRAM protocol, reset/PLL
GPIO85/GPIO8, BDIC reset GPIO76, CLK_SEL GPIO107, PM8941 L2/LVS2
power sequencing, Sharp CLMR firmware command queues, TE and board
calibration. Then integrate with the stage B1 662-record runtime DCS
table and remove fail-closed gates only after verification.

No Linux 6.1 hardware driver PASS, no flashing, no TWRP edits.
