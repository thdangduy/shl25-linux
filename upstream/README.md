# SHL25 clean upstream kernel strategy — November 2026

## Why replace msm8974-mainline/linux?
Earlier work **compiled from source** qcom-msm8974-6.16.y of the community MSM8x74 fork using qcom_defconfig and a partial SHL25 Device Tree. It was not a precompiled kernel or necessarily incompatible CPU; it was an external source tree with a set of fork patches not independently reviewed for SHL25. Experiment compiled, but Linux 6.16 did not produce the PID1 marker.

The new build pins official upstream https://github.com/torvalds/linux tag v6.16 at commit 038d61fd642278bab63ee8ef722c50d10ab01e8f. Original Linux includes Qualcomm msm8974 and msm8974pro DTS includes. GitHub Actions compiles natively from official source on an isolated Ubuntu runner, without the VPS-ARM.

## Source and drivers
- Linux upstream: immutable pinned source commit. No third-party fork for the kernel base.
- SHL25-specific board DTS, config overrides, and future patches reside in THIS repository, each change audited.
- Sharp official GPL 3.4 source and stock FDT: reference for physical wiring, RAM/SMEM reservations, PMIC rails, eMMC pins, screen initialization. The old drivers **cannot be copied unchanged** to kernel 6.16. Any custom driver requires migration to new kernel APIs, licensing audit and hardware verification.
- Pipeline output: kernel zImage, SHL25 DTB, config, SHA256 manifest. **No flashable BOOT image and never automatic flash.**
- Recovery/TWRP and user data remain untouched.

## Required bring-up milestones
1. Compile **pristine** upstream kernel v6.16 + MSM8974Pro SoC files + current draft SHL25 DTB. Compile passing ≠ boot passing.
2. Before a new flash: validate board memory/bootloader FDT fixups, reserved-memory areas, eMMC and PMIC regulator mappings, and boot protocol with stock Sharp image.
3. Early-stage kernel entry and PID1 marker test. Sharp 3.4 + static diagnostic init v3 already PASS with /cache/shl25-616-diag.log.
4. Port driver support in order: SoC clocks/RPM/PMIC → eMMC → USB/ConfigFS → Sharp panel with CLMR/IR2E71Y6 → touch → WLAN/audio/power.
5. Maintain separate patch series and hardware checks, avoid unreviewed copy-paste of vendor 3.4 driver code.

Linux 6.16 is used first solely to compare with previous 6.16 experiments. It is not LTS. An upstream supported LTS may be preferable for long-term product use once boot bring-up is proven.
