# SHL25 Linux 6.1 — Stage C4 Sharp BDIC VSP/VSN register programs

Date 2026-11-07. Source-only/CI build. Phone remains off charging.

## Verified board-specific OEM sources

- `kernel/drivers/sharp/shdisp_lcdc/data/shdisp_bl71y6_ctrl.h`
  SHA256 `f4a034bc613339c92b04c9df94f5a5adcb06ab51dfab53e9ba2ee095e9d2f69b`.
- `data/shdisp_bl71y6_data_as99.h`
  SHA256 `79bebee79c31f2a0d39637dc0de5c6b596f4f196cdbd73e0017df7b069dab18b`.
- `shdisp_bl71y6.h`
  SHA256 `d78408db969bd0ff9cf2efdec97e2cd5c4158a16cbaf6777238b8ee17404ae62`.
- `shdisp_bl71y6.c`
  SHA256 `ae1d0d78dc639c881c80c857a781e510341fdd66e92c8481e88088b4b02c3206`.
- Correct variant: `CONFIG_MACH_DECKARD_AS99`. The VSP/VSN
  sequences are defined in the OEM common ctrl header, with AS99
  chip-specific values (including `BDIC_REG_CPM1_VAL_TS1=0x05`).

## Implementation added to Linux 6.1 worktree

- `upstream/build_shl25_bdic_power.py` regenerates exact source-pinned
  power steps, register addresses, flags, mask and delays.
- `upstream/shl25-as99-bdic-power.json` contains 7 ordered groups,
  17 exact register operations.
- `drivers/spi/shl25-as99-bdic-power-tables.h` generated C arrays.
- `drivers/spi/shl25-as99-bdic-power.{c,h}`: typed callback executor
  with explicit versioned VSN branch and strict readiness guards.
- `upstream/verify_shl25_bdic_power.py`: offline table/protocol/delay
  and no-hardware-hook safety checks.
- Build script stages `CONFIG_SPI_SHL25_AS99_BDIC_POWER=y` and checks
  the Linux 6.1 object. No kernel probe or initcall for C4.

## Original register power details

- ACTIVE: bank=0, set SYSTEM1 bit 0x80, wait 1000 us, set SYSTEM3 bit 0x02.
- STANDBY: bank=0, clear SYSTEM3 bit 0x02, clear SYSTEM1 bit 0x80.
- VSP ON: bank=0, DCDC2_TEST_57=0, set SYSTEM2 bit 0x01, wait 3000 us.
- VSP OFF: clear SYSTEM2 bit 0x01, DCDC2_TEST_57=0x80,
  wait 2000 us.
- VSN ON (non-TS1): SYSTEM2 masked write data 0x10 mask 0x50.
- VSN ON (TS1 / chip version 0): write CPM1=0x05, clear SYSTEM2
  bit 0x20, masked write data 0x10 mask 0x50, wait 16000 us,
  set SYSTEM2 bit 0x20.
- VSN OFF: SYSTEM2 masked write data 0x40 mask 0x50,
  wait 1000 us.

`SHDISP_BDIC_SET` performs masked-write(data, data),
`CLR` performs masked-write(0, mask), `RMW` performs
masked-write(data, mask). `BANK` is Sharp firmware command 0x5F,
not an ordinary write to register 0xFF.

## Explicitly missing / blocked

The transport must run through Sharp CLMR firmware commands (previous
C2 implementation is an offline queue fixture, NOT a live firmware
dispatcher), and the CLMR firmware must first boot. The actual PM8941
L2/LVS2 supply sequencing, GPIOs, real BDIC chip-version reading,
backlight policy, DSI panel calibration and error recovery are not
connected. `board_power_verified`, `clmr_firmware_running`,
`clmr_fwcmd_channel_verified`, `bdic_chipver_read_verified` are
required. No live caller sets these or calls the C4 executor.

No Windows ADB operation, flash, recovery modification, or device
boot. Source compile PASS must not be presented as LCD hardware PASS.
