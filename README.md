# SHL25 Linux (Sharp AQUOS SERIE / AS99)

Experimental ARMv7 mainline Linux port for **Sharp SHL25 / AS99** (Qualcomm MSM8974Pro).

**Status: buildable kernel and board Device Tree; NOT yet a working Ubuntu Server boot.**

The first Linux 6.16 BOOT trial did not show a console or return ADB. The phone's TWRP recovery remains accessible and the original BOOT backups remain on the operator's Windows machine.

## Build with GitHub Actions

Open **Actions > SHL25 Linux 6.16 Cross Build > Run workflow**. The workflow runs on GitHub-hosted Ubuntu 24.04; it does not need a VPS, a phone, or private keys in GitHub. The downloadable artifact contains:

- armv7 kernel zImage
- Sharp AS99 board DTB and its DTS source
- kernel .config and checksums
- build metadata with exact upstream commit

Pushing updates to main also triggers the same build.

## Source

Kernel source: https://github.com/msm8974-mainline/linux (branch qcom-msm8974-6.16.y, pinned commit 888dd19735240b640f925a6da4affc082c5c48a9)

Official Sharp GPL kernel source: https://k-tai.sharp.co.jp/support/developers/oss/shl25/index.html

The mainline board DTS is an experimental adaptation from vendor Sharp 3.4 hardware descriptions. Unported devices include Sharp DSI panel, CLMR/IR2E71Y6 backlight, SPI touch and AR6004 HSIC Wi-Fi.

**Build output is NOT a ready-to-flash BOOT image.** Never directly flash a bare zImage or DTB into mmcblk0p13. See docs/BOOT_DIAGNOSTICS.md.

## Windows repository SSH key

Use your locally managed key at C:/Users/Admin/Desktop/KEY_VPS/github-shl25-linux-ed25519 for pushing from Windows. The private key is not part of this repo and is not required for GitHub Actions.
