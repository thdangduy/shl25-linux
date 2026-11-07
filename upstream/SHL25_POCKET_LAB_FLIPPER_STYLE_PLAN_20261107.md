# SHL25 Pocket Lab — Flipper-style Linux multi-tool plan

Date: 2026-11-07. Direction approved by owner: transform Sharp SHL25
into a **touch-first Linux multi-tool, inspired by Flipper Zero**.
Do NOT claim it is a Flipper Zero firmware port or copy its assets.
Preserve native Linux 6.1 port, own original Sharp K34
known-good rollback, and TWRP. SHL25 handset was not touched.

## Source-audited foundation (selected Sharp GPL bld010105)

Offline scan of exact original `kernel.tar.gz` (41,978 files) and
`vendor.tar.gz` (445 files). Original OEM source files were
extracted **only into Windows checkpoint** under
`Sharp-Checkpoint-20261107/Flipper-OEM-References`, outside git.
Evidence does NOT mean the peripheral is working on Linux 6.1.

| Feature | Exact OEM proof | Limit / port step |
|---|---|---|
| 1080p LCD + multitouch | K34 LCD text and 5-finger touch confirmed on real handset in prior stage | Linux 6.1 display/CLMR/BDIC/touch not hardware booted |
| Wi-Fi | vendor/qcom/opensource/wlan/prima, WCNSS configuration + firmware files | Linux 6.1 WCNSS and AP+STA concurrency must be validated on device |
| FeliCa/NFC | `drivers/sharp/mfc/felica.c` SHA 3ede5ec50709c59caad9f859d5d4a4fb3aef77bdbd91a938951d00bf3b59f387, `mfc/snfc.c` SHA c486fd149ea3a08d802d08ea7b438e0dc31d000d0e73b9dab8ba76d260e8cb56, `nfc/snfc_ant.c` SHA 93f0a953c0feaaed611d51b96a3b651b7eb2259011f6422476d9ce7be9715621, `sharp-as99.dtsi` `felica_cen@57` | Identify controller, secure-element boundary and interface; card emulation NOT assumed |
| IrDA / possible IR blaster | `drivers/sharp/shirda`, Kconfig `CONFIG_SHIRDA`, optional `CONFIG_SHIRBLASTER`; MSM8974 pinmap TXD45 RXD46 SD47; SHA of config `e536e6fa13f1cb8182527cbcb2ffd21fbccf55aa1b331e4e811bd9037e2843` | IR serial and remote-control blaster differ; validate selected AS99 config, carrier timing and optical TX circuit |
| TV/UHF RX | `drivers/sharp/tunerdrv/TunerDev.c` SHA `d953b3480de82ce71abd66454b81d79789772a2a52817a9b5875af042114c5be`; `drivers/sharp/tunerdrv_tmm/TunerDev_tmm.c` SHA `4a005c76f8244a8ea9e99d51a2c6330e92e7966ad912a2d02893d1791bb3de1e`; model-specific `CONFIG_MACH_DECKARD_AS99` GPIO selection | These are **GPIO/rail/clock control wrappers**, not proof of full demodulator driver. Need exact silicon, real transport TSIF, and user-space decode/firmware |
| TV pins | OEM `tunerdrv_tmm/gpio_def_tmm.h` maps DTVEN TLMM92, DTVRST TLMM13, antenna selectors PM8841 MPP1/MPP2 and TLMM49 on AS99 | Board bindings, polarity, rail/antenna logic, spectrum regulations to verify first |
| Sensors, grip | OEM `drivers/sharp/shsensor_hub`, `shgrip`, `shtps` | Linux 6.1 board-selected IRQ/SPI/regulator port |
| USB | K34 CDC ACM COM21 demonstrated; Linux 6.1 gadget configured in kernel staging | USB gadget/host and external expansion roles still unverified on 6.1 |
| Sub-GHz TX/RX | No dedicated transceiver proven | TV tuner antenna is a **receiver path** and not a CC1101/sub-GHz transmitter. External supported USB/SPI module required unless independent RF proof emerges |
| RFID 125 kHz | No LF RFID front-end proven | FeliCa/NFC 13.56MHz does not equal 125kHz RFID. External coil/reader required |
| iButton/1-Wire | No contact interface proven | External 1-Wire adapter and contact probe required |

**Important distinction:** the OEM TV hardware is a Japanese
ISDB-T/One-Seg/Full-Seg receiver path, not necessarily DVB-T2 and
not a general-purpose IQ SDR. Avoid advertising reception in
Vietnam or arbitrary UHF modulation without demodulator evidence.

No assumptions about cloning protected credentials, transmitting
on arbitrary radio frequencies, or bypassing secure elements.
Any RF transmission feature must require explicit user intent,
hardware validation and regional frequency compliance.

## Hardware capability states for GUI

Machine-readable `userspace/pocketlab/hardware-manifest.json` is
the source-of-truth feature registry. Features have:
- stable ID, UI label, group, priority;
- provenance and limitations;
- current source status;
- required driver/user-space/firmware next steps.

Driver or file node discovery is **not hardware PASS**.
`userspace/pocketlab/probe_readonly.py` enumerates candidate
`/sys` and `/dev` paths without opening them, changing GPIO,
running commands, scanning radio, transmitting RF or flashing.
Its output distinguishes `NODE_FOUND_UNVERIFIED` from
`NO_CANDIDATE_NODE`. Later real tests require hardware permission
and separate evidence logs.

## Architecture

1. **Kernel (Linux 6.1)**: real SHL25 AS99 drivers, remote-safe
   hardware diagnostics, regulator/clock/reset/IRQ recovery.
2. **Hardware services**: isolate privileged drivers in bounded
   daemons. Service APIs include `probe/start/stop/read-status`
   and must refuse absent/untested devices.
3. **Pocket Lab UI**: touch-first fullscreen launcher,
   1080x1920 landscape/portrait responsive, running on
   DRM/KMS with Qt Quick when GPU works. Alternative low-resource
   DRM/linuxfb/SDL2 path if GPU not working. No Android dependency.
4. **Terminal**: true local Linux PTY and SSH shell, virtual
   keyboard, log viewer, terminal fallback when UI is unavailable.
5. **Modules**: Network, Bluetooth, FeliCa, Infrared,
   TV/UHF receiver, USB peripherals, sensors, storage/system,
   and explicitly external Sub-GHz/RFID/iButton expansion.
6. **Observability**: show per-module readiness and proof source,
   kernel driver, firmware, bus, IRQ, power state, fail codes;
   never turn `source present` into `device functional`.

## Execution order

- **P0**: finish native 6.1 boot, USB console, PMIC,
  LCD 1080p DRM, touch, storage and thermal/battery safety.
  Preserve BOOT/TWRP and rollback. No feature that writes
  undocumented PMIC/RF GPIO on probe.
- **P1**: minimal GUI shell + real PTY + touchscreen keyboard,
  device status panel, read-only probe module.
- **P2**: Wi-Fi network and AP, Bluetooth HCI; only then
  test AP+STA in supported firmware combinations.
- **P3**: FeliCa/NFC and IrDA, gated reader/protocol tools;
  port exact selected driver and avoid secure-card assumptions.
- **P4**: TV tuner/UHF *receive*: identify tuner/demod silicon,
  OEM GPIO/TSIF and actual decoder; validate receive-only path.
- **P5**: optional external radio modules (Sub-GHz, LF RFID,
  iButton) over OTG/serial/SPI; follow laws and user authorization.

## CI/test baseline added

Run `python3 userspace/pocketlab/test_probe_readonly.py`.
Tests assert unique manifest IDs, read-only fixture behavior,
no hardware PASS from device nodes, and expansion modules
remain unavailable without independent hardware evidence.
Linux kernel CI runs this offline userspace test before cross-build.
No handset access needed.

This direction is now part of the official SHL25 Linux 6.1
roadmap, not a claim that the feature modules already operate.
