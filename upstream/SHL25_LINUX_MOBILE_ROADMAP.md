# SHL25 Linux Mobile — native Linux, terminal first

**Goal:** develop a native, Sharp-independent Linux system for SHL25/AS99. Not Android, not an Android-derived launcher, not an entire Raspberry Pi desktop. First display a working text terminal on the **real LCD**; only then develop a minimal touch-first mobile GUI.

## Build provenance and boundaries

- Kernel base: official upstream Linux v6.16, pinned commit 038d61fd642278bab63ee8ef722c50d10ab01e8f. Do not use third-party prebuilt kernels.
- Board port: separate DTS/config/driver patches in this repository, hardware details cross-checked against the Sharp official SHL25 OSS kernel, vendor and hardware tarballs (01.00.05 and 01.01.05).
- Builds use GitHub Actions; Windows is the working lab. Never use VPS-ARM. Never change TWRP Recovery or erase userdata for bring-up.
- Kernel source license and vendor driver licenses must be respected. Old 3.4 driver source is reference and must be ported for current APIs, not copied unmodified.

## Boot milestones (gates)

| Gate | Hardware proof | Acceptance evidence |
| --- | --- | --- |
| 0 | Original Sharp kernel 3.4 + static diagnostic PID1, eMMC /cache | **PASS**, marker SHL25_DIAG_PID1_OK kernel=3.4.0; TWRP independent recovery |
| 1 | Original upstream 6.16 enters PID1, basic SoC, PMIC, eMMC | Marker in /cache showing Linux 6.16, USB serial/ConfigFS or other diagnostic path if available |
| 2 | Real LCD clocks/regulators + DSI panel initialization | Physical screen displays known test pattern, correct orientation and colors; not just stock bootloader logo |
| 3 | Linux text console on LCD | DRM/KMS, fbdev console emulation + built-in font and virtual terminal; visible shell prompt and readable output |
| 4 | Local interaction | Port actual touch controller via Linux input/evdev; USB keyboard + SSH remain useful during initial input testing |
| 5 | Minimal Linux userspace | Small rootfs/init: BusyBox/Buildroot initially, persistent config/logs, usable boot and shutdown |
| 6 | Purpose-built native touch UI | Direct DRM/KMS compositor or LVGL + evdev, native terminal, files, network/USB gadget, SSH, device health, power |
| 7 | Stable daily use | suspend/resume, charging/battery gauges, Wi-Fi (if supportable), USB peripherals, crash recovery, updates |

### Critical distinction: bootloader splash is not an initialized Linux display

The existing Sharp 1080x1920 LCD uses DSI command-mode panel sequences plus Sharp shdisp/CLMR/IR2E71Y6 components. Modern `CONFIG_DRM_MSM=y` alone is **not** sufficient to light the panel: port the exact board panel bridge/power/reset/timing path and avoid guessing signal mappings. If bootloader framebuffer reuse is possible, verify physical RAM and compatible simple-framebuffer binding before using it; do not fabricate addresses.

### Terminal-first kernel configuration targets

After board memory/probe gate succeeds:
- `CONFIG_DRM_MSM=y`, associated panel/bridge and MDSS/DSI components built-in.
- `CONFIG_DRM_FBDEV_EMULATION=y`, `CONFIG_FB=y`, `CONFIG_FRAMEBUFFER_CONSOLE=y`, `CONFIG_VT=y`, `CONFIG_VT_CONSOLE=y` (as supported by pinned kernel config).
- `console=tty0` and a font at 1080x1920. A simple static initramfs launches `/bin/sh` on the LCD VT only after /dev/tty0 is available.
- `CONFIG_INPUT_EVDEV=y` for future touch.
- Minimal working diagnostics remain available from /cache. Persistent ramoops only after a verified reserved RAM region is established.

## Native mobile UI after terminal PASS

Use a low-dependency **LVGL application on DRM/KMS + evdev** for the first GUI. Software rendering is acceptable for early development; do not block on GPU acceleration. Start portrait 1080x1920 with accessible touch hit targets and adaptive layout, then add hardware acceleration only when DRM/MSM GPU is stable.

Initial screens: **Terminal**, **Files**, **Connections** (Wi-Fi/USB network/SSH/NetBird if portable), **Device** (battery, temperatures, storage, CPU, log), and **Settings** (brightness, rotation, power). Avoid Android framework, Play Services, a full desktop environment, telephony, and camera until explicitly needed.

The UI is strictly downstream of physical-LCD/terminal/input bring-up. Never interpret CI compile PASS as actual display support.

## Source audit

Compare 2014 bld010005 kernel/vendor/hardware with 2016 bld010105 kernel/vendor; inventory Sharp panel / shdisp / CLMR / IR2E71Y6, power/regulator, touchscreen, eMMC and thermal/charging paths. Only apply evidence-backed patches to the dedicated upstream branch.
