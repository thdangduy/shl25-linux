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
    -e QCOM_SMD_RPM -e REGULATOR_QCOM_SMD_RPM \
    -d DEBUG_INFO_BTF -d DEBUG_INFO_BTF_MODULES
make -C "$SRC" O="$OBJ" olddefconfig
python3 - "$CONFIG" <<'PY'
import pathlib,sys
cfg=pathlib.Path(sys.argv[1]).read_text()
required=("ARCH_QCOM", "BLK_DEV_INITRD", "RD_GZIP", "DEVTMPFS", "MMC_SDHCI_MSM", "EXT4_FS", "QCOM_SMD_RPM", "REGULATOR_QCOM_SMD_RPM")
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
echo "SHL25_DTB_PREFLIGHT_PASS"
make -C "$SRC" O="$OBJ" -j"$(nproc)" zImage
cp "$OBJ/arch/arm/boot/zImage" "$DIST/zImage"
cp "$CONFIG" "$DIST/kernel.config"
cp "$DTS" "$DIST/qcom-msm8974-sharp-as99.dts"

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
Validated on device: NO, build/DTB check only
TWRP / Recovery: untouched
EOF
(cd "$DIST" && sha256sum zImage qcom-msm8974-sharp-as99.dtb kernel.config qcom-msm8974-sharp-as99.dts > SHA256SUMS)
echo "UPSTREAM_LINUX_6_1_BUILD_PASS"
cat "$DIST/SOURCE_MANIFEST.txt"
cat "$DIST/SHA256SUMS"
