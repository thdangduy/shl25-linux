# SHL25 / AS99 — actual Synaptics SY3000 TM2979-001 touch port evidence

This is **6.1 engineering evidence**, not a claim that the touchscreen works on Linux 6.1.

## What the running K34 handset and OEM build prove

- Native standalone Linux 3.4, without Android, passed all five
  coordinate targets and a five-finger same-frame matching test.
  See the K34 branch `docs/K34_NATIVE_TOUCH_5_POINT_MULTI5_HARDWARE_PASS_20261107.md`.
- TWRP Linux 3.4 `/proc/bus/input/devices` shows
  `shtps_rmi` `event3` and `shtps_key` `event4`,
  both from SPI2.0 at physical `f9924000`.
- Sharp OEM `deckard_as99_defconfig` explicitly enables
  `CONFIG_SHTPS_SY3X00_DEV=y`,
  `CONFIG_SHTPS_SY3000_TM2979_001=y`.
- The **actual Makefile selected** by `CONFIG_SHTPS_SY3000_TM2979_001` is
  `kernel/drivers/sharp/shtps/sy3000_2/Makefile`;
  it builds the **626,843-byte** monolithic
  `sy3000_2/shtps_rmi_spi.c` plus control/debug companions.
  Do NOT accidentally port the wrong `sy3000/` or `sy3000_1/`
  variant (both also present in the GPL tarball).
- Exact source archive: `Sharp-OEM-Sources/bld010105/kernel.tar.gz`,
  SHA256 `231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb`.
  Extracted source copy for local audit:
  `Sharp-Checkpoint-20261107/OEM-Driver-Reference-2016/shtps_actual_tm2979_shtps_rmi_spi.c`.
  OEM GPL sources are **not** blindly copied into the 6.1 tree.

## Hardware DT facts, not guessed

The OEM `sharp-as99.dtsi` specifies
- BLSP1 QUP2 `spi@f9924000`, chip select 0, 400kHz,
  CPOL+CPHA (SPI mode 3), main GPIO61 interrupt with legacy DT type 0;
- PM8941 GPIO30 reset pin;
- PM8941 L15 `shtps_rmi,vdd_3_0V` (but OEM regulator definition has
  **2,100,000 uV**, not 3.0V!), and LVS1 supply from S3;
- The vendor driver requests `IRQF_TRIGGER_LOW | IRQF_ONESHOT` if
  `SHTPS_IRQ_LEVEL_ENABLE` is defined, otherwise
  `IRQF_TRIGGER_FALLING | IRQF_ONESHOT`.
  Therefore the unfinished Linux 6.1 DT intentionally keeps
  `interrupts = <61 IRQ_TYPE_NONE>` and **status disabled** until
  the selected driver configuration is resolved. Assuming level-HIGH
  would be demonstrably unsupported by the OEM IRQ handler.

## Upstream Linux 6.1 transport available, but not yet adapted

Linux tag `v6.1` already provides
`drivers/input/rmi4/rmi_spi.c` matching `compatible="syna,rmi4-spi"`,
and `drivers/input/rmi4/rmi_f11.c`/`rmi_f12.c`.
The SHL25 board OEM calls its device `compatible="sharp,shtps_rmi"`
instead. The generic driver **does not bind** to that string;
the new Sharp DT explicitly leaves the node disabled.

Linux 6.1 build prerequisites are prepared and compiled in:
`CONFIG_SPI_QUP=y`, `CONFIG_INPUT_EVDEV=y`, `CONFIG_RMI4_CORE=y`,
`CONFIG_RMI4_SPI=y`, `CONFIG_RMI4_F11=y`, `CONFIG_RMI4_F12=y`.

**Next driver port steps**
1. Audit the actual `sy3000_2/shtps_rmi_spi.c` RMI SPI transaction
   framing, F01/F11/F12 function-table discovery, data-ready delays,
   IRQ polarity and IRQ masking against the Linux 6.1 generic RMI4 SPI.
2. Add a narrow Sharp transport quirk or dedicated driver for
   unsupported transaction sequences if required. Do not rename
   compatible to `syna,rmi4-spi` until a protocol/electrical match
   is established.
3. Port PM8941 L15/LVS1, reset PMIC GPIO30, pinctrl for QUP2 and
   power-cycle delays into valid 6.1 bindings.
4. Enable **only** the verified QUP2/driver combo; perform real
   I/O probe and the already published 5-point/5-finger test.
5. Add `shtps_key` capacitive key events, firmware recovery,
   display blank/wake synchronization and charger noise mitigation.

**Hardware boundary:** User has powered off SHL25 for charging.
Do not issue ADB, flash, reboot, or device testing during this phase.
K34 BOOT p13 and Recovery p14 are unmodified.
