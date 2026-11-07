# SHL25 / AS99 — Linux 6.1 complete hardware-driver migration register

**Last updated:** 2026-11-07. Target: native Linux **6.1**, not an Android ROM.
**Status:** IN PROGRESS; no bootable/fully functional Linux 6.1 handset has been proven.

## Baseline, authority, and release requirement

Primary Sharp vendor source: archived 2016 GPL `Sharp-OEM-Sources/bld010105/kernel.tar.gz`
(SHA-256 `231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb`);
detailed original DTS extracted locally under `Sharp-Checkpoint-20261107/OEM-Driver-Reference-2016`.
Direct hardware evidence from TWRP Linux 3.4 under `TWRP-K34-Hardware/`, and owner-confirmed standalone Linux 3.4 USB, LCD and 5-finger touch tests in
`docs/K34_NATIVE_USB_IAD_V4_HARDWARE_PASS_20261107.md`,
`docs/K34_NATIVE_LCD_VISUAL_HARDWARE_PASS_20261107.md` and
`docs/K34_NATIVE_TOUCH_5_POINT_MULTI5_HARDWARE_PASS_20261107.md` on the K34 branch.

**No shortcut:** K34 hardware PASS is not Linux 6.1 PASS.
Linux 6.1 CI zImage/DTB PASS is not proof of boot or device I/O.
Each row needs: (1) verified driver/firmware, (2) Linux 6.1 Kconfig,
(3) accepted board DT or platform data, (4) on-device probe and function test.
Some vendor drivers need substantial rewrite to Linux 6.1 kernel APIs;
copying 2016 files directly is not a valid port.

## Complete device scope / acceptance register

| ID | Subsystem | Actual Sharp/K34 evidence | 6.1 work and dependency | Acceptance gate |
|---|---|---|---|---|
| 01 | AP/SoC, CPU cores, GIC, timers | Qualcomm MSM8974PRO-AB, 4× ARMv7, memory bootloader QCDT | ARMv7 MSM8974Pro DTS, clocks, SCM, SMEM, TZ carveouts, SPM | CPU1–3 online, kernel PID1 and timer stable |
| 02 | PM8841/PM8941 SPMI regulators/GPIO | PM8841 v2.1, PM8941 v3.1, at least 64 regulators; OEM PMIC DTS | Map **all** used rails, SPMI GPIO/MPP, parent supply relationships; no made-up voltages | read back regulators and validate consumers/power switching |
| 03 | eMMC / SDHC1 | 29.1 GiB eMMC mmcblk0 with 38 partitions | Linux 6.1 sdhci-msm and Sharp pad drive 12mA CLK, 10mA CMD/data, L20/S3 | partition read-only enumeration, ext4 mount |
| 04 | SD/MMC slot / SDHC2 | OEM sharp-as99-sdcc.dtsi drive 12mA on SDHC2; slot detection not yet proven | Determine removable-slot wiring, vmmc, card detect; don't enable by assumption | real card insertion/removal and transfer |
| 05 | USB OTG/PHY, gadget serial | Native K34 USB CDC ACM COM21 8/8 reopen; data send/receive | Linux 6.1 PHY + ChipIdea USB controller + configfs CDC ACM, USB host/OTG power & extcon | Linux 6.1 USB console, host/peripheral mode, transfers |
| 06 | MDP/DSI display engine | mdssfb_90000 1080×1920 32bpp; real LCD text visible via FORCE ioctl | Mainline MSM DRM/KMS, MDSS/DSI clocks, framebuffers, DMA, modesetting | physical test pattern and page flip on 6.1 |
| 07 | Sharp Andy panel | OEM `sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi`, CMD DSI0 | Port a DRM panel with validated initialization DCS, reset, timings, suspend | cold boot logo replaced by native UI, stable brightness |
| 08 | CLMR + BDIC / backlight | SPI1.0 mipi_spi_0, CLMR & IR2E71Y6 platform devices, lcd-backlight 255 | Port Sharp CLMR/BDIC control + regulators L2/LVS2 + GPIO/IRQ 75/9; firmware analysis | backlight levels, blank/unblank, suspend/resume |
| 09 | Capacitive touchscreen | SPI2.0 `shtps_rmi`, IRQ GPIO61, PM8941 reset GPIO30, rails L15/LVS1; native 5 points and 5 simultaneous contacts PASS | RMI SPI input driver, correct IRQ/rails/reset and K34 tracking semantics | same five-position + five-finger test under Linux 6.1 |
| 10 | Touch capacitive keys | `shtps_key` event4 sourced from SPI2.0 | Preserve keymap, GPIO/interrupt and power behavior | all capacitive keys register correct Linux keycodes |
| 11 | Grip sensor | SPI10.0 `shgrip_dev`, BLSP2 QUP4, 960kHz | Port Sharp grip SPI driver and runtime power/interrupt | grip input switch test with event log |
| 12 | IMU gyro/accelerometer | I²C12 addr 0x68 `mpu6515` inv-mpu-iio; OEM orientation and secondary AK8963 compass 0x0c | Verify MPU6515 register compatibility; port IIO + compass, gyro calibration | XYZ sensor readings, orientation/compass |
| 13 | Proximity / light sensors | `proximity` input event1; Sharp proximity_cdc sources | Identify prox/ALS front-end, port sensor and calibration | covering/uncovering + ALS lux changes |
| 14 | Rear camera | OEM CCI sensor **IMX214** at 0x20, 4 CSI lanes, reset PM8941 GPIO13, actuator AK7345 | V4L2 sensor, Qualcomm CCI/CSIPHY/CSID/VFE media pipeline, regulator rails | real 1080p image stream and still capture |
| 15 | Front camera | OEM CCI sensor **IMX132** at 0x6c, separate CSI lanes, reset PM8941 GPIO14 | V4L2 sensor and shared CSI/ISP media-controller | stream real front-camera frames |
| 16 | Autofocus / flash/torch | OEM `ak7345,actuator`; PM8941 dual flash & torch | actuator and LED flash V4L2 subdevices, thermal limits | focus sweep + torch + flash trigger |
| 17 | GPU / hardware acceleration | K34 `/dev/kgsl-3d0` exists; functionality not verified | Adreno 330 DRM/MSM, IOMMU, firmware, GPU clocks | accelerated EGL/GLES render, GPU fault-free |
| 18 | Audio codec/ADSP | OEM Sharp audio-routing and Qualcomm sound components, headset properties | Discover exact codec, ASoC routing, ADSP remoteproc firmware and DAI | speaker/mic/earpiece/headphone audio and call route |
| 19 | Earpiece amplifier | I²C5 addr 0x6f `shreceiver_i2c`, Sharp `shreceiver_lm48560.c` | Port external amp and ASoC DAPM power control | volume/control at real receiver |
| 20 | Wi-Fi | OEM Qualcomm/Atheros WLAN and QCA sources, historical AR6004/HSIC **not independently confirmed on 6.1** | Identify chip transport and firmware from stock logs; port driver (ath6kl/other after verification) | scan, join AP, DHCP, iperf two-way |
| 21 | Bluetooth | K34 hci_smd, hci_uart and bluetooth_power modules visible | Identify transport (SMD/UART), controller firmware, rfkill & HCI | pairing, scan, bidirectional data/audio |
| 22 | Baseband LTE/SIM/mobile data | OEM rmnet0–7, rmnet_usb0, QMI/diag devices in kernel 3.4 | QRTR/SMD/remoteproc/QMI/modem bring-up, SIM, radio firmware and control | identify SIM/carrier, network attach, mobile IP, data |
| 23 | GNSS/GPS | Qualcomm modem subsystem likely involved; stock source needed for exact UART/QMI route | Confirm firmware and Qualcomm service path, then expose GNSS data | actual NMEA/location fix tested outdoors |
| 24 | NFC / FeliCa | I²C5 `felica_cen` @0x57 bound, `snfc_ant` @0x40 node disabled by OEM, Sharp MFC/NFC sources | Port NFC/FeliCa transport/SE and region-specific GPIO control | device ID, tag read/write where supported |
| 25 | Infrared / IrDA | OEM `sharp,use-irda` BLSP8 UART f995e000, `ir_kbd_i2c` present | Port UART/IR TX/RX route and pinmux, confirm physical hardware | IR send/receive with external reference |
| 26 | TV/tuner if populated | Sharp tunerdrv and tunerdrv_tmm sources present; physical module unverified | Verify chip/DT enable; vendor tuner compatibility & firmware | detect tuner + receive test (or evidence-based N/A) |
| 27 | Battery gauge / charging | OEM `sharp,shbatt`, QPNP BMS/charger, multiple battery supplies, wireless supply | Full charging state machine, ADC/thermistors, battery protection, wireless charging path | real charge/discharge, temperature/current/status safe and accurate |
| 28 | Thermal management | 17 thermal zones in K34, QPNP sensors and Sharp regulation | TSENS, thermal trips, cooling devices, cpufreq interaction | realistic sensor values, throttling trip recovery |
| 29 | Buttons/LED/vibrator | qpnp_pon event0, RGB LED + LED flash nodes in OEM, vibrator status unknown | Input keys, PWM/LED, haptics & PMIC pin config | power/keys/LED states/haptic response |
| 30 | RTC, wake/suspend/poweroff | PMIC/RTC and wake sources in 3.4; standalone shutdown untested | wake IRQ routing, watchdog, suspend/resume, RTC alarm | RTC continuity, suspend wake, graceful shutdown |

Rows with only *source existence* are not yet evidence that an accessory chip is physically populated: especially WLAN transport, tuner, GPS and vibrator. Preserve such uncertainty explicitly.

## Linux 6.1 stage gates

1. **Core:** CPU/bootloader RAM fixup, clocks, SPMI regulators, SDHC/eMMC, USB serial live; no Android dependency.
2. **Input/display:** MDSS DRM/KMS + Sharp Andy/BDIC/CLMR panel; SPI2 `shtps_rmi` 5/5 + 5 concurrent touches. Existing K34 proof is the golden acceptance fixture.
3. **Power/thermal + storage/communication:** charging/BMS, thermal, SD card, WLAN, BT, modem and GPS tested.
4. **Multimedia and Sharp accessories:** audio, cameras/CSI, GPU, NFC/FeliCa, IR, LEDs, tuner where present.
5. **Full regression:** all applicable rows tested on 6.1, power cycle and restore; source, artifacts, tests and hashes preserved.

**Hardware safety:** Device currently powered off for charging, so work only on Windows source and GitHub CI. Do not flash 6.1 without an independently bootable initramfs, a validated QCDT/DDR fixup path and TWRP recovery p14, plus hash-verified p13 rollback. Do not treat unverified 6.1 boot as a success.

## First current changes: mainline 6.1 bus layout

`dts/shl25-as99-peripherals.dtsi` introduces accurate but DISABLED QUP controllers:
- SPI1 `f9923000`: Sharp CLMR/display `mipi_spi_0`;
- SPI2 `f9924000`: `shtps_rmi` touch controller GPIO61;
- SPI10 `f9966000`: `shgrip_dev`;
- I²C5 `f9927000`: FeliCa `0x57`, antenna `0x40`;
- Existing mainline I²C12 `f9968000`: MPU6515 `0x68`.

The 6.1 upstream pinctrl functions, clock IDs and bus compatibility were validated against *tag v6.1* original SoC/pinctrl/SPi source. This is a compile-checked **driver port foundation** with explicit DISABLED nodes; no subdevice is claimed functional on 6.1 yet. `upstream/verify_shl25_peripherals.py` checks the compiled FDT, not source text.
