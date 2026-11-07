# SHL25/AS99 — Sharp CLMR PM8941 rails + GPIO power Stage C7

Date 2026-11-07. Only source/CI; handset OFF charging.
No device changes, BOOT/TWRP untouched.

## Exact source provenance (selected AS99 kernel bld010105)

Extracted on Windows from original immutable kernel.tar.gz:

- `arch/arm/boot/dts/sharp-shdisp-clmr.dtsi`
  SHA256 `bfc029b599c3b4c0236f74e5079db80b49da21dce3d63d4677c1258b6b3b2260`
- `arch/arm/boot/dts/sharp-as99-shdisp.dtsi`
  SHA256 `b2bf7ce848b7818e4749832ee6e8f0e26756fdb5acfc7e5af4b3324bdd1e5289`
- `arch/arm/boot/dts/sharp-as99.dtsi`
  SHA256 `86f325c59d6b63e2905c2bb7b7353b3b1528df56db6257ee47d2db270619740a`
- `drivers/sharp/shdisp_lcdc/shdisp_clmr.c`
  SHA256 `399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0`
- `drivers/sharp/shdisp_lcdc/shdisp_system.h`
  SHA256 `490f3d0f8a6b1763cb888edb95b7d96f89cb102977092e54c86a7c6a044169b2`

## Verified board hardware map

- Display companion Sharp CLMR: BLSP1 QUP1 `spi@f9923000`,
  chip select 0, 50 MHz max, SPI mode 3, CS active-high.
- `clmr_vdd_18tx-supply = <&pm8941_lvs2>`: VS type, first enable,
  wait **1000us**.
- `clmr_vdd_12lp-supply = <&pm8941_l2>`: LDO type, set to
  exactly **1,200,000 uV**, load **100,000 uA**, second enable,
  wait **1000us**.
- Core VDD switch: PM8941 GPIO19, active high, **after** both rails.
  On shutdown, pull switch low first, then disable L2, then LVS2.
- CLMR reset TLMM GPIO85, PLLONCTL TLMM GPIO8,
  firmware hint IRQ TLMM GPIO75, TE GPIO12.
- Other display GPIO: Andy VDD TLMM69, CLK_SEL TLMM107.
- OEM interrupt spec is `<75 0>`. Linux 6.1 trigger type,
  pinctrl wiring and correct IRQ acknowledgment MUST be confirmed
  before enablement; do not invent an edge/level policy.

## C7 implementation and test

- `drivers/spi/shl25-as99-clmr-power.{c,h}` compiles a typed
  regulator/GPIO supply sequencer using Linux 6.1 consumer APIs.
  It handles voltage/load configuration, ordered enable, delays,
  ordered disable and rollback when second regulator enable fails.
- It uses `gpiod_direction_output()` to hold the core switch low
  until both rails are ready. The future board adapter must prove
  active-high polarity and bind the real PMIC GPIO19.
- `upstream/shl25-as99-clmr-board-power.json` pins the original
  source hashes and actual board map; no fabricated DT phandles.
- `upstream/verify_shl25_clmr_power.py` validates the map,
  source order, timing, rollback and default disabled DTS. On Windows
  its optional OEM-input validation compared all original SHA256s.
- Linux 6.1 build script stages
  `CONFIG_SPI_SHL25_AS99_CLMR_POWER=y`, verifies object built and
  adds sources/map to artifacts.

**No caller** currently provides
`shl25_clmr_power_resources` or asserts the 4 readiness guards.
There is no initcall, SPI probe hook, DT enablement, firmware boot,
GPIO toggling or source-driven handset action in this stage.
The code alone is NOT proof that power rails work on Linux 6.1.

Next: verify and bind PM8941 LVS2/L2 and GPIO19 phandles on
upstream Linux 6.1, reset/clock GPIO85/GPIO8 and IRQ75 type,
then integrate this with C6 SPI bridge and C3 firmware boot,
and finally BDIC FWCMD and Andy panel calibration.
