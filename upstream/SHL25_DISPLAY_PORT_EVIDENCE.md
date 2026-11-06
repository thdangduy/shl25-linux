# SHL25 display bring-up: evidence from Sharp GPL 2014 versus 2016

## Scope

This note serves the **native Linux** project only: first show a live VT terminal on the real Sharp SHL25 LCD, then create a compact touch-first Linux GUI. Do not start Android/AOSP development. Do not flash for display experiments until kernel entry, RAM, PMIC, eMMC and recovery path are verified.

Source archives downloaded directly from Sharp's official SHL25 OSS page to Windows and verified against published sizes. Original archives remain intact under `Sharp-OEM-Sources`.

| Sharp release | Compressed archive size | SHA-256 |
| --- | ---: | --- |
| 01.00.05 kernel | 115,227,500 bytes | `2c1a3086332fb31d8c528a5548aedae175009b07b73a2869aa964a4affba5386` |
| 01.01.05 kernel | 116,260,461 bytes | `231315e67112ffa3b5311059ba8ad4f6b4f2213edea40a7fff001f5a3bdf27bb` |
| 01.00.05 hardware | 3,847 bytes | `8d710f766638842f15a77c2c436498dba5d8eeda3e83c4e26c2d84a385d48b5a` |

The small `hardware.tar.gz` is **not** complete board support. It contains only four source-like files under `hardware/qcom/wlan/qcwcn/wpa_supplicant_8_lib`. The actual kernel-side display/touch/power drivers are in `kernel.tar.gz`.

## Relevant Sharp 01.01.05 source paths

- `kernel/arch/arm/boot/dts/sharp-as99-shdisp.dtsi`: the board enables the Andy 1080p command-mode panel plus Sharp CLMR and BDIC, and selects DSI0 as primary; its old DT memory reservation is **not** safe to reuse without validating mainline memory layout.
- `kernel/arch/arm/boot/dts/sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi`: DSI command-mode sequence, timing and orientation for 1080 × 1920 at 60 Hz.
- `kernel/arch/arm/boot/dts/sharp-shdisp-clmr.dtsi`: Sharp CLMR on BLSP1 SPI and board-specific rails `pm8941_lvs2` / `pm8941_l2`, PM8941 GPIO 19, interrupt GPIO 75; uses old Qualcomm DT syntax.
- `kernel/arch/arm/boot/dts/sharp-shdisp-ir2e71y6-lcdc.dtsi`: SHARP BDIC IRQ GPIO 9; the AS99 board includes this LCDC variant rather than blindly including the alternative I2C variant.
- `kernel/drivers/sharp/shdisp/shdisp_andy.c`: Sharp panel handling.
- `kernel/drivers/sharp/shdisp/shdisp_bl71y6.c`: backlight/display IC control.
- `kernel/drivers/sharp/shdisp/shdisp_kerl.c`, `shdisp_panel.c`, `shdisp_pm.c`, `shdisp_system.c`: integration, panel, power and platform logic.
- `kernel/drivers/video/msm/mdss/mdss_dsi.c`, `mdss_dsi_panel.c`, `mdss_fb.c`: vendor MIPI-DSI and framebuffer driver used in original 3.4 kernel.

### Release differences that matter

- 01.00.05 `sharp-as99-shdisp.dtsi` references `sharp-shdisp-ir2e69y8.dtsi` and `shdisp-clmr.dtsi`; 01.01.05 references `sharp-shdisp-ir2e71y6-lcdc.dtsi` and `shdisp-clmr.dtsi`.
- 01.00.05 `drivers/sharp/shdisp` has 36 file members; 01.01.05 has 22. The older release includes `shdisp_clmr.c` and a substantial CLMR firmware header, while the newer listing omits those files and includes `shdisp_aria.c`. **This is a software architecture difference, not evidence the CLMR hardware was removed.**
- 01.01.05 contains a second, separate `sharp-shdisp-dsi-panel-andy-as99-1080p-video.dtsi`. Its existence does not mean the original AS99 board uses video mode: the included `sharp-as99-shdisp.dtsi` references the **command-mode** panel. Avoid mixing CMD and VIDEO mode settings.
- Original Sharp panel size in the board DTS is approximately 64 × 114 mm; native portrait resolution is 1080 × 1920.

## Migration to upstream Linux

1. **Boot gate:** prove upstream kernel PID1 marker and validate RAM/firmware carveouts. No display patches should be flashed when this is unproven.
2. **Panel electrical gate:** map Sharp CLMR/BDIC rails, enable GPIOs, reset path, SPI, IRQ and any firmware dependencies from the 2016 kernel. Verify against upstream PMIC and BLSP bindings; do not copy old DT nodes verbatim.
3. **DRM panel gate:** implement a contemporary `drm_panel` or bridge integration for Sharp Andy CMD 1080p, with correct MIPI DSI packets, regulators, reset timing and backlight/BDIC ordering; connect it to upstream Qualcomm DRM/MSM. A blank LCD or bootloader logo alone is **not** a PASS.
4. **Pixel gate:** render a reproducible test pattern using DRM/KMS to the physical display.
5. **Terminal gate:** build DRM/MSM and panel drivers in-kernel, enable DRM fbdev emulation, VT and framebuffer console, and launch shell on the local VT. Confirm a live readable prompt; USB keyboard/SSH can be used while native touch is unfinished.
6. **Input/UI gate:** port touch controller and evdev; only then use LVGL or another light direct DRM/KMS interface for mobile GUI.

Never assume generic Sony/Xperia panel/PMIC settings fit SHL25 just because both use MSM8974Pro. Sharp vendor 3.4 code is the authoritative device reference; upstream Linux 6.16 is the target API surface.
