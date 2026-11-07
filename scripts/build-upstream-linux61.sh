#!/usr/bin/env bash
set -Eeuo pipefail
# Compile original Linux v6.1 for ARMv7 and SHL25. No flashable image.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL_REMOTE="https://github.com/torvalds/linux.git"
KERNEL_TAG="v6.1"
KERNEL_COMMIT="830b3c68c1fb1e9176028d02ef86f3cf76aa2476"
WORK="$ROOT/.build/upstream61"
SRC="$WORK/linux"
OBJ="$WORK/out"
DIST="$ROOT/dist-upstream61"
DTS="$ROOT/dts/qcom-msm8974-sharp-as99.dts"
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-

for tool in git make gcc arm-linux-gnueabihf-gcc arm-linux-gnueabihf-ld dtc sha256sum python3; do
    command -v "$tool" >/dev/null || { echo "MISSING_TOOL: $tool"; exit 2; }
done
mkdir -p "$WORK" "$OBJ" "$DIST"
if [ ! -d "$SRC/.git" ]; then
    git clone --depth=1 --single-branch --branch "$KERNEL_TAG" "$KERNEL_REMOTE" "$SRC"
fi
git -C "$SRC" fetch --depth=1 origin "refs/tags/$KERNEL_TAG:refs/tags/$KERNEL_TAG"
git -C "$SRC" checkout --detach "$KERNEL_TAG"
ACTUAL="$(git -C "$SRC" rev-parse HEAD)"
if [ "$ACTUAL" != "$KERNEL_COMMIT" ]; then
    echo "UPSTREAM_COMMIT_MISMATCH: $ACTUAL"; exit 3
fi
# Out-of-tree Sharp OEM Andy command-mode panel driver: graft onto
# clean, SHA-pinned vanilla 6.1 source for compiler/API validation.
# The SHL25 board DTS keeps panel + DSI0 disabled until CLMR/BDIC power
# sequencing is verified; built-in code alone is NOT hardware PASS.
python3 "$ROOT/upstream/verify_shl25_andy_panel.py" --verify
python3 "$ROOT/upstream/build_shl25_andy_runtime.py" --verify
PANEL_SRC="$ROOT/drivers/gpu/drm/panel/panel-sharp-shl25-andy.c"
PANEL_DIR="$SRC/drivers/gpu/drm/panel"
test -s "$PANEL_SRC"
cp "$PANEL_SRC" "$PANEL_DIR/panel-sharp-shl25-andy.c"
RUNTIME_SRC="$ROOT/drivers/gpu/drm/panel/shl25-andy-as99-runtime.h"
test -s "$RUNTIME_SRC"
cp "$RUNTIME_SRC" "$PANEL_DIR/shl25-andy-as99-runtime.h"
echo SHL25_AS99_RUNTIME_SOURCE_PINNED_AND_COPIED
if ! grep -q '^config DRM_PANEL_SHARP_SHL25_ANDY$' "$PANEL_DIR/Kconfig"; then
    cat >> "$PANEL_DIR/Kconfig" <<'PANEL_KCONFIG'

config DRM_PANEL_SHARP_SHL25_ANDY
    tristate "Sharp SHL25 AS99 Andy 1080p command-mode panel"
    depends on OF
    depends on DRM_MIPI_DSI
    depends on BACKLIGHT_CLASS_DEVICE
    help
      Vendor GPL-derived Sharp Andy MIPI DSI command transport port.
      Board CLMR/BDIC regulators and power sequencing are not yet
      completed; keep board display node disabled until verified.
PANEL_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_DRM_PANEL_SHARP_SHL25_ANDY) += panel-sharp-shl25-andy.o' \
      >> "$PANEL_DIR/Makefile"
fi
echo SHL25_ANDY_PANEL_VENDOR_CMDS_CHECKED_AND_SOURCE_STAGED
# Selected AS99 CLMR transport, exact OEM SPI1 protocol. Compiled built-in
# but hardware DT stays disabled and probe never powers the device.
python3 "$ROOT/upstream/verify_shl25_clmr_spi.py"
python3 "$ROOT/upstream/verify_shl25_clmr_fw_packets.py"
python3 "$ROOT/upstream/verify_shl25_bdic_fwcmd.py"
CLMR_SPI_SRC="$ROOT/drivers/spi/spi-shl25-as99-clmr.c"
CLMR_SPI_DIR="$SRC/drivers/spi"
test -s "$CLMR_SPI_SRC"
cp "$CLMR_SPI_SRC" "$CLMR_SPI_DIR/spi-shl25-as99-clmr.c"
if ! grep -q '^config SPI_SHL25_AS99_CLMR$' "$CLMR_SPI_DIR/Kconfig"; then
    cat >> "$CLMR_SPI_DIR/Kconfig" <<'CLMR_SPI_KCONFIG'

config SPI_SHL25_AS99_CLMR
    tristate "Sharp SHL25 AS99 CLMR command SPI transport"
    depends on SPI && OF
    help
      Board-disabled prototype for Sharp CLMR SPI reg access.
      Does NOT load firmware or power regulators.
CLMR_SPI_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_SPI_SHL25_AS99_CLMR) += spi-shl25-as99-clmr.o' \
      >> "$CLMR_SPI_DIR/Makefile"
fi
echo SHL25_AS99_CLMR_SPI_SOURCE_STAGED_POWER_DISABLED
# Stage C3: source-pinned CLMR boot register programs and isolated
# callback-based boot sequence. No board hardware adapter or probe hook.
python3 "$ROOT/upstream/build_shl25_clmr_boot.py" --verify
python3 "$ROOT/upstream/verify_shl25_clmr_boot_sequence.py"
python3 "$ROOT/upstream/verify_shl25_clmr_firmware_sha.py"
CLMR_BOOT_C="$ROOT/drivers/spi/shl25-as99-clmr-boot.c"
CLMR_BOOT_H="$ROOT/drivers/spi/shl25-as99-clmr-boot.h"
CLMR_BOOT_TABLES="$ROOT/drivers/spi/shl25-as99-clmr-boot-tables.h"
test -s "$CLMR_BOOT_C" && test -s "$CLMR_BOOT_H" && test -s "$CLMR_BOOT_TABLES"
cp "$CLMR_BOOT_C" "$CLMR_SPI_DIR/shl25-as99-clmr-boot.c"
cp "$CLMR_BOOT_H" "$CLMR_SPI_DIR/shl25-as99-clmr-boot.h"
cp "$CLMR_BOOT_TABLES" "$CLMR_SPI_DIR/shl25-as99-clmr-boot-tables.h"
if ! grep -q '^config SPI_SHL25_AS99_CLMR_BOOT$' "$CLMR_SPI_DIR/Kconfig"; then
    cat >> "$CLMR_SPI_DIR/Kconfig" <<'CLMR_BOOT_KCONFIG'

config SPI_SHL25_AS99_CLMR_BOOT
    bool "Sharp SHL25 AS99 CLMR firmware boot sequence (unwired)"
    depends on SPI_SHL25_AS99_CLMR && CRYPTO_SHA256
    help
      Source-verified CLMR firmware-boot register program and sequence
      executor. No caller or platform adapter, no hardware I/O in probe.
CLMR_BOOT_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_SPI_SHL25_AS99_CLMR_BOOT) += shl25-as99-clmr-boot.o' \
      >> "$CLMR_SPI_DIR/Makefile"
fi
echo SHL25_AS99_CLMR_BOOT_SEQUENCE_STAGED_DT_DISABLED
# Stage C4: source-verified BDIC VSP/VSN commands via CLMR FWCMD,
# with explicit chip-version TS1 branch and no registered driver.
python3 "$ROOT/upstream/build_shl25_bdic_power.py" --verify
python3 "$ROOT/upstream/verify_shl25_bdic_power.py"
BDIC_C="$ROOT/drivers/spi/shl25-as99-bdic-power.c"
BDIC_H="$ROOT/drivers/spi/shl25-as99-bdic-power.h"
BDIC_TABLES="$ROOT/drivers/spi/shl25-as99-bdic-power-tables.h"
test -s "$BDIC_C" && test -s "$BDIC_H" && test -s "$BDIC_TABLES"
cp "$BDIC_C" "$CLMR_SPI_DIR/shl25-as99-bdic-power.c"
cp "$BDIC_H" "$CLMR_SPI_DIR/shl25-as99-bdic-power.h"
cp "$BDIC_TABLES" "$CLMR_SPI_DIR/shl25-as99-bdic-power-tables.h"
if ! grep -q '^config SPI_SHL25_AS99_BDIC_POWER$' "$CLMR_SPI_DIR/Kconfig"; then
    cat >> "$CLMR_SPI_DIR/Kconfig" <<'BDIC_POWER_KCONFIG'

config SPI_SHL25_AS99_BDIC_POWER
    bool "Sharp SHL25 AS99 BDIC VSP/VSN command sequences (unwired)"
    depends on SPI_SHL25_AS99_CLMR_BOOT
    help
      Source-verified BDIC power tables through CLMR FWCMD callbacks,
      no hardware transport, probe, or power enable path connected.
BDIC_POWER_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_SPI_SHL25_AS99_BDIC_POWER) += shl25-as99-bdic-power.o' \
      >> "$CLMR_SPI_DIR/Makefile"
fi
echo SHL25_AS99_BDIC_POWER_TABLES_STAGED_DT_DISABLED
# Stage C6: actual Sharp CLMR SPI transport/firmware-loader callback bridge,
# compiled as built-in but NEVER invoked from SPI probe or enabled DTS.
python3 "$ROOT/upstream/verify_shl25_clmr_spi_bridge.py"
CLMR_BRIDGE_SRC="$ROOT/drivers/spi/shl25-as99-clmr-spi-bridge.c"
CLMR_BRIDGE_HDR="$ROOT/drivers/spi/shl25-as99-clmr-spi-bridge.h"
test -s "$CLMR_BRIDGE_SRC" && test -s "$CLMR_BRIDGE_HDR"
cp "$CLMR_BRIDGE_SRC" "$CLMR_SPI_DIR/shl25-as99-clmr-spi-bridge.c"
cp "$CLMR_BRIDGE_HDR" "$CLMR_SPI_DIR/shl25-as99-clmr-spi-bridge.h"
if ! grep -q '^config SPI_SHL25_AS99_CLMR_BRIDGE$' "$CLMR_SPI_DIR/Kconfig"; then
    cat >> "$CLMR_SPI_DIR/Kconfig" <<'CLMR_BRIDGE_KCONFIG'

config SPI_SHL25_AS99_CLMR_BRIDGE
    bool "Sharp SHL25 AS99 guarded CLMR SPI/firmware bridge (unwired)"
    depends on SPI_SHL25_AS99_CLMR_BOOT && FW_LOADER
    help
      OEM C0/C2/C4 register SPI, C7/C8 eDRAM stream and firmware loader.
      No probe caller, no board power/reset/IRQ wiring, AS99 DT disabled.
CLMR_BRIDGE_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_SPI_SHL25_AS99_CLMR_BRIDGE) += shl25-as99-clmr-spi-bridge.o' \
      >> "$CLMR_SPI_DIR/Makefile"
fi
echo SHL25_AS99_CLMR_C6_BRIDGE_SOURCE_STAGED_NO_PROBE
# Stage C7: selected Sharp AS99 PM8941 LVS2 + L2 + GPIO19 power order.
# Source-pinned only; no kernel device probe calls the power operations.
python3 "$ROOT/upstream/verify_shl25_clmr_power.py"
CLMR_PWR_SRC="$ROOT/drivers/spi/shl25-as99-clmr-power.c"
CLMR_PWR_HDR="$ROOT/drivers/spi/shl25-as99-clmr-power.h"
test -s "$CLMR_PWR_SRC" && test -s "$CLMR_PWR_HDR"
cp "$CLMR_PWR_SRC" "$CLMR_SPI_DIR/shl25-as99-clmr-power.c"
cp "$CLMR_PWR_HDR" "$CLMR_SPI_DIR/shl25-as99-clmr-power.h"
if ! grep -q '^config SPI_SHL25_AS99_CLMR_POWER$' "$CLMR_SPI_DIR/Kconfig"; then
    cat >> "$CLMR_SPI_DIR/Kconfig" <<'CLMR_PWR_KCONFIG'

config SPI_SHL25_AS99_CLMR_POWER
    bool "Sharp SHL25 AS99 PM8941 CLMR two-rail power sequence (unwired)"
    depends on SPI_SHL25_AS99_CLMR_BRIDGE && REGULATOR && GPIOLIB
    help
      Verified PM8941 LVS2 then L2 1.2V with PMIC GPIO19 core switch.
      No DT supply binding, IRQ, or board probe hook in this stage.
CLMR_PWR_KCONFIG
    printf '%s\n' 'obj-$(CONFIG_SPI_SHL25_AS99_CLMR_POWER) += shl25-as99-clmr-power.o' \
      >> "$CLMR_SPI_DIR/Makefile"
fi
echo SHL25_AS99_C7_POWER_SEQUENCE_STAGED_NOT_ENABLED
KVER="$(make -s -C "$SRC" kernelversion)"
case "$KVER" in 6.1|6.1.0) ;; *) echo "WRONG_UPSTREAM_VERSION: $KVER"; exit 4;; esac

# Native upstream SoC/PMIC includes. Our SHL25 DTS lives in our own repository.
for file in \
    "$SRC/arch/arm/boot/dts/qcom-msm8974.dtsi" \
    "$SRC/arch/arm/boot/dts/qcom-msm8974pro.dtsi" \
    "$SRC/arch/arm/boot/dts/qcom-pm8841.dtsi" \
    "$SRC/arch/arm/boot/dts/qcom-pm8941.dtsi"; do
    test -s "$file" || { echo "MISSING_UPSTREAM_SOC_BINDING=$file"; exit 5; }
done
test -s "$DTS" || { echo NO_SHL25_DTS; exit 6; }
make -C "$SRC" O="$OBJ" qcom_defconfig
CONFIG="$OBJ/.config"
"$SRC/scripts/config" --file "$CONFIG" \
    -e BLK_DEV_INITRD -e RD_GZIP \
    -e DEVTMPFS -e DEVTMPFS_MOUNT \
    -e ARM_APPENDED_DTB -e ARM_ATAG_DTB_COMPAT \
    -e ARM_ATAG_DTB_COMPAT_CMDLINE_FROM_BOOTLOADER \
    -e MMC_SDHCI_MSM -e EXT4_FS \
    -e SPI -e SPI_MASTER -e SPI_QUP -e I2C -e I2C_QUP -e INPUT -e INPUT_EVDEV -e IIO \
    -e SPI_SHL25_AS99_CLMR -e SPI_SHL25_AS99_CLMR_BOOT -e SPI_SHL25_AS99_BDIC_POWER -e SPI_SHL25_AS99_CLMR_BRIDGE -e SPI_SHL25_AS99_CLMR_POWER -e CRYPTO_SHA256 -e FW_LOADER -e GPIOLIB \
    -e RMI4_CORE -e RMI4_SPI -e RMI4_F11 -e RMI4_F12 \
    -e DRM -e DRM_MSM -e DRM_PANEL -e DRM_FBDEV_EMULATION -e FB -e FRAMEBUFFER_CONSOLE -e VT \
    -e DRM_PANEL_SHARP_SHL25_ANDY \
    -e USB_GADGET -e USB_CONFIGFS -e USB_CONFIGFS_ACM \
    -e QCOM_SMD_RPM -e REGULATOR_QCOM_SMD_RPM \
    -d ATA -d SATA_AHCI -d DEBUG_INFO_BTF -d DEBUG_INFO_BTF_MODULES
make -C "$SRC" O="$OBJ" olddefconfig
python3 - "$CONFIG" <<'PY'
import pathlib,sys
cfg=pathlib.Path(sys.argv[1]).read_text()
required=("ARCH_QCOM", "BLK_DEV_INITRD", "RD_GZIP", "DEVTMPFS", "MMC_SDHCI_MSM", "EXT4_FS", "QCOM_SMD_RPM", "REGULATOR_QCOM_SMD_RPM", "SPI_QUP", "SPI_SHL25_AS99_CLMR", "SPI_SHL25_AS99_CLMR_BOOT", "SPI_SHL25_AS99_BDIC_POWER", "SPI_SHL25_AS99_CLMR_BRIDGE", "SPI_SHL25_AS99_CLMR_POWER", "CRYPTO_SHA256", "FW_LOADER", "GPIOLIB", "I2C_QUP", "INPUT_EVDEV", "IIO", "RMI4_CORE", "RMI4_SPI", "RMI4_F11", "RMI4_F12", "DRM_MSM", "DRM_PANEL_SHARP_SHL25_ANDY", "DRM_FBDEV_EMULATION", "FRAMEBUFFER_CONSOLE", "VT", "USB_CONFIGFS_ACM")
missing=[key for key in required if f"CONFIG_{key}=y" not in cfg]
if missing: raise SystemExit("REQUIRED_UPSTREAM_CONFIG_NOT_BUILTIN: "+", ".join(missing))
print("UPSTREAM_SHL25_MINIMAL_CONFIG_PASS", len(required), "required built-ins")
PY
# Compile and validate the board DTS before the expensive full kernel build.
# This fails fast for syntax or board property regressions.
gcc -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
    -I "$SRC/include" \
    -I "$SRC/arch/arm/boot/dts" \
    -I "$SRC/arch/arm/boot/dts/qcom" \
    "$DTS" -o "$WORK/shl25.preprocessed.dts"
dtc -I dts -O dtb -o "$DIST/qcom-msm8974-sharp-as99.dtb" "$WORK/shl25.preprocessed.dts"
python3 "$ROOT/upstream/verify_shl25_dtb.py" "$DIST/qcom-msm8974-sharp-as99.dtb"
python3 "$ROOT/upstream/verify_shl25_peripherals.py" "$DIST/qcom-msm8974-sharp-as99.dtb"
echo "SHL25_DTB_PREFLIGHT_PASS"
make -C "$SRC" O="$OBJ" -j"$(nproc)" zImage
test -s "$OBJ/drivers/gpu/drm/panel/panel-sharp-shl25-andy.o" ||
    { echo "SHL25_ANDY_PANEL_DRIVER_OBJECT_MISSING"; exit 14; }
echo SHL25_ANDY_DRM_PANEL_61_COMPILED_BUILTIN_PASS
test -s "$OBJ/drivers/spi/spi-shl25-as99-clmr.o" ||
    { echo "SHL25_CLMR_SPI_OBJECT_MISSING"; exit 15; }
echo SHL25_CLMR_SPI_61_COMPILED_BUILTIN_PASS
test -s "$OBJ/drivers/spi/shl25-as99-clmr-boot.o" ||
    { echo "SHL25_CLMR_BOOT_OBJECT_MISSING"; exit 16; }
echo SHL25_CLMR_BOOT_SEQUENCE_61_COMPILED_BUILTIN_PASS
test -s "$OBJ/drivers/spi/shl25-as99-bdic-power.o" ||
    { echo "SHL25_BDIC_POWER_OBJECT_MISSING"; exit 17; }
echo SHL25_BDIC_POWER_SEQUENCE_61_COMPILED_BUILTIN_PASS
test -s "$OBJ/drivers/spi/shl25-as99-clmr-spi-bridge.o" ||
    { echo "SHL25_CLMR_SPI_BRIDGE_OBJECT_MISSING"; exit 18; }
echo SHL25_CLMR_C6_SPI_BRIDGE_61_COMPILED_BUILTIN_PASS
test -s "$OBJ/drivers/spi/shl25-as99-clmr-power.o" ||
    { echo "SHL25_CLMR_C7_POWER_OBJECT_MISSING"; exit 19; }
echo SHL25_CLMR_C7_POWER_61_COMPILED_BUILTIN_PASS
cp "$OBJ/arch/arm/boot/zImage" "$DIST/zImage"
cp "$CONFIG" "$DIST/kernel.config"
cp "$DTS" "$DIST/qcom-msm8974-sharp-as99.dts"
cp "$PANEL_SRC" "$DIST/panel-sharp-shl25-andy.c"
cp "$RUNTIME_SRC" "$DIST/shl25-andy-as99-runtime.h"
cp "$CLMR_SPI_SRC" "$DIST/spi-shl25-as99-clmr.c"
cp "$CLMR_BOOT_C" "$DIST/shl25-as99-clmr-boot.c"
cp "$CLMR_BOOT_H" "$DIST/shl25-as99-clmr-boot.h"
cp "$CLMR_BOOT_TABLES" "$DIST/shl25-as99-clmr-boot-tables.h"
cp "$BDIC_C" "$DIST/shl25-as99-bdic-power.c"
cp "$BDIC_H" "$DIST/shl25-as99-bdic-power.h"
cp "$BDIC_TABLES" "$DIST/shl25-as99-bdic-power-tables.h"
cp "$CLMR_BRIDGE_SRC" "$DIST/shl25-as99-clmr-spi-bridge.c"
cp "$CLMR_BRIDGE_HDR" "$DIST/shl25-as99-clmr-spi-bridge.h"
cp "$CLMR_PWR_SRC" "$DIST/shl25-as99-clmr-power.c"
cp "$CLMR_PWR_HDR" "$DIST/shl25-as99-clmr-power.h"
cp "$ROOT/upstream/shl25-as99-clmr-board-power.json" "$DIST/shl25-as99-clmr-board-power.json"
cp "$ROOT/upstream/shl25-andy-as99-runtime.json" "$DIST/shl25-andy-as99-runtime.json"
cp "$ROOT/upstream/shl25-andy-oem-dsi.json" "$DIST/shl25-andy-oem-dsi.json"

python3 - "$DIST/qcom-msm8974-sharp-as99.dtb" <<'PY'
from pathlib import Path
import struct,sys
b=Path(sys.argv[1]).read_bytes()
assert len(b)>0x2000 and struct.unpack_from(">I",b)[0]==0xd00dfeed
assert struct.unpack_from(">I",b,4)[0]==len(b)
assert b"qcom,sharp-as99" in b
print("UPSTREAM_SHL25_DTB_COMPILE_PASS", len(b))
PY
cat > "$DIST/SOURCE_MANIFEST.txt" <<EOF
Kernel repository: $KERNEL_REMOTE
Upstream annotated tag: $KERNEL_TAG
Verified upstream Linux commit: $ACTUAL
Arch: ARMv7 / Krait / Qualcomm MSM8974Pro
Config: vanilla qcom_defconfig + explicit minimal boot requirements
SoC files: original Linux upstream; SHL25 DTS: thdangduy/shl25-linux
Third-party precompiled kernel: NONE
Flashable image: NONE (output zImage, DTB, config only)
Sharp AS99 Andy DRM driver: compiled into zImage; DSI0 DT node disabled
Andy OEM DSI commands: 28 on + 2 off, SHA-pinned against Sharp GPL
AS99 CLMR runtime: 16 groups, 662 DCS records; per-unit calibration not active
AS99 CLMR SPI register transport compiled; DT client disabled, no firmware/power initialization
AS99 CLMR boot sequence callback executor compiled; SHA-256 firmware gate before I/O, no SPI adapter/probe caller
AS99 BDIC VSP/VSN and TS1 callback programs compiled; no FWCMD adapter or hardware probe caller
AS99 C6 SPI/firmware-loader transport bridge compiled; no power/IRQ device adapter or hardware probe caller
AS99 C7 PM8941 LVS2/L2 two-rail source-pinned power sequencing compiled; no GPIO/regulator DT adapter or probe caller
Validated on device: NO, build/DTB check only
TWRP / Recovery: untouched
EOF
(cd "$DIST" && sha256sum zImage qcom-msm8974-sharp-as99.dtb kernel.config qcom-msm8974-sharp-as99.dts panel-sharp-shl25-andy.c shl25-andy-oem-dsi.json shl25-andy-as99-runtime.h shl25-andy-as99-runtime.json spi-shl25-as99-clmr.c shl25-as99-clmr-boot.c shl25-as99-clmr-boot.h shl25-as99-clmr-boot-tables.h shl25-as99-bdic-power.c shl25-as99-bdic-power.h shl25-as99-bdic-power-tables.h shl25-as99-clmr-spi-bridge.c shl25-as99-clmr-spi-bridge.h shl25-as99-clmr-power.c shl25-as99-clmr-power.h shl25-as99-clmr-board-power.json > SHA256SUMS)
echo "UPSTREAM_LINUX_6_1_BUILD_PASS"
cat "$DIST/SOURCE_MANIFEST.txt"
cat "$DIST/SHA256SUMS"
