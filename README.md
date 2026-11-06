# OPPO Mirror 5 A51w — TWRP build experiment

A separate **orphan Git branch**, unrelated to Sharp SHL25 sources.

Goal: build Android 5.1 Omni TWRP for the **actual OPPO A51w**. It is not
Samsung Galaxy A51 and must not use a generic A51f binary unmodified.

## Verified A51w inputs

- A51w ADB reports `armv7l`, ABI `armeabi-v7a`, `zygote32`.
- Factory kernel contains **ARM zImage magic** `0x016f2818`, **NOT ARM64 Image**.
- Original A.17 BOOT SHA256: `36befcf242bf04d45c2bbff5b93976288aa3dfe2e1bfb7edca0abd5920fe258b`.
- Kernel load: 0x80008000; ramdisk: 0x81000000; tags 0x80000100; pagesize 2048.
- OEM QCDT v3: 1,687,552 bytes with 28 board selectors, nine unique FDTs.
- Live GPT: BOOT mmcblk0p22 / Recovery mmcblk0p23, both **32 MiB**.
- LCD: 540x960; Synaptics S3203 touchscreen; LM3630 backlight.
- Factory recovery fstab used for by-name paths. No imaginary `encrypt` partition.

TWRP architecture starts from the 32-bit path of the
[Hinokami-Kagura OPPO A51f tree](https://github.com/Hinokami-Kagura/twrp_device_oppo_a51f/tree/android-5.1),
but deliberately uses **only A51w OEM kernel/QCDT** retrieved during CI
from the original OPPO A.17 OTA, CRC and SHA-256 verified. Vendor binaries
are not committed to the git branch.

Build with `minimal-manifest-twrp/platform_manifest_twrp_omni`
branch `twrp-5.1`, using an Ubuntu 18.04 compatibility container
to provide Android's legacy Java 8/Python 2 dependencies. A CI success is
not equivalent to device boot success.

All output is experimental. **Never flash directly.** Test an image with
`fastboot boot` only after offline header, partition size, QCDT hash,
display/USB and file-system checks. Known-good reconstructed A51w A.17
stock recovery SHA256 `d1f75c58d189cd1abbae3725eecdbdcebd45126186145cfa3520a15607872f47`.

Main project data and raw dumps remain on owner's Windows in
`C:\Users\Admin\Downloads\SHL25-Linux-Lab\A51w-Lab`.
