# SHL25 Linux 6.1: native UI/USB transport built-in prerequisite

2026-11-07, source/CI only. SHL25 is powered off for battery charging. No hardware interaction.

## Defect discovered in CI baseline

Earlier Linux 6.1 CI `42377191376` shipped **only** `zImage`, board DTB and config.
Its `kernel.config` contained:
- `CONFIG_DRM_MSM=m`: Qualcomm MDSS/DSI/Adreno DRM driver is a module, **not inside** the compressed kernel.
- `# CONFIG_USB_CONFIGFS_ACM is not set`: configfs gadget could not create a USB CDC ACM function even with the controller and configfs core enabled.
- `CONFIG_DRM_MSM_DSI=y`, `CONFIG_DRM_PANEL=y`,
  `CONFIG_DRM_FBDEV_EMULATION=y`,
  `CONFIG_FRAMEBUFFER_CONSOLE=y`, `CONFIG_VT=y`,
  `CONFIG_USB_CHIPIDEA=y`, `CONFIG_USB_CONFIGFS=y`.

Therefore the previous kernel-only release payload was incomplete for
standalone phone LCD and native CDC ACM USB user console.
Correcting the build config is not a hardware-port PASS:
SHL25 still needs Sharp Andy DSI panel/CLMR/BDIC driver and actual USB
gadget function setup in initramfs.

## Build changes

`scripts/build-upstream-linux61.sh` explicitly enables and **asserts
builtin=y** for:
- `DRM_MSM`, `DRM_FBDEV_EMULATION`, `FRAMEBUFFER_CONSOLE`, `VT`:
  required to embed the Qualcomm DRM/KMS stack in `zImage` rather than
  relying on omitted loadable modules for a future text/GUI display.
- `USB_CONFIGFS_ACM`: provides a CDC ACM function available for a
  native BusyBox gadget setup in initramfs.

Existing RMI4 SPI/F11/F12 are also kept built into the kernel and must
not be mistaken for a working SHL25 touch driver. RMI4 generic SPI
compatible is not the Sharp `shtps_rmi` compatible and lacks verified
board power/IRQ support.

## Next hardware-dependent acceptance gates

1. Complete Sharp Andy cmd-mode DRM panel and CLMR/BDIC driver and
   regulator sequencing in Linux 6.1.
2. Complete an actual configfs gadget bring-up initramfs for
   USB CDC ACM via Linux 6.1.
3. Prove mainline 6.1 CPU boots and reaches PID1 *without overwriting*
   TWRP Recovery p14.
4. Show on-device 1080x1920 DRM pixel pattern and interactive console;
   prove five-target and five simultaneous touch coordinates against
   the native Linux 3.4 golden test.

The CI checks compilation and built-in symbol constraints, not device
function. Any CI failure must be fixed from its actual logs before
claiming a PASS.
