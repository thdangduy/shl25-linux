#!/usr/bin/env python3
"""Stage C10: Sharp OEM AS99 CLMR DEVCODE preflight, source-pinned.

Software-source check only. No hardware / SPI transactions executed.
"""
import argparse
import hashlib
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BOOT=(ROOT/"drivers/spi/shl25-as99-clmr-boot.c").read_text(encoding="utf-8")
HDR=(ROOT/"drivers/spi/shl25-as99-clmr-boot.h").read_text(encoding="utf-8")
BRIDGE=(ROOT/"drivers/spi/shl25-as99-clmr-spi-bridge.c").read_text(encoding="utf-8")
SPI=(ROOT/"drivers/spi/spi-shl25-as99-clmr.c").read_text(encoding="utf-8")
DTS=(ROOT/"dts/shl25-as99-peripherals.dtsi").read_text(encoding="utf-8")
OEM_C_SHA="399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0"
OEM_H_SHA="1eb86c4756fd1afb5b815eb2739e2a5170f51ac4f9279b3917201edcc1c6249d"

parser=argparse.ArgumentParser()
parser.add_argument("--oem-clmr-c",type=Path)
parser.add_argument("--oem-clmr-h",type=Path)
args=parser.parse_args()
if bool(args.oem_clmr_c)!=bool(args.oem_clmr_h):
    raise SystemExit("need both OEM .c and .h to validate")
if args.oem_clmr_c:
    for name,path,expected in (
        ("shdisp_clmr.c",args.oem_clmr_c,OEM_C_SHA),
        ("shdisp_clmr.h",args.oem_clmr_h,OEM_H_SHA)):
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
    c=args.oem_clmr_c.read_text(encoding="utf-8",errors="replace")
    h=args.oem_clmr_h.read_text(encoding="utf-8",errors="replace")
    assert re.search(r"#define\s+SHDISP_CLMR_DEVCODE_VALUE\s+0x00004002",c)
    assert re.search(r"#define\s+SHDISP_CLMR_REG_DEVCODE\s+0x0300",h)
    check=c.split("static int shdisp_clmr_lcdc_devcheck(void)",2)[-1].split(
        "static int shdisp_clmr_gpio_reset_ctrl",1)[0]
    assert "shdisp_SYS_clmr_sio_transfer(SHDISP_CLMR_REG_DEVCODE" in check
    assert "SHDISP_CLMR_DEVCODE_VALUE != regVal" in check
    print("SHL25_AS99_C10_OEM_DEVCODE_SOURCE_HASH_PASS")

assert "#define SHL25_CLMR_REG_DEVCODE 0x0300" in BRIDGE
assert "#define SHL25_CLMR_DEVCODE_EXPECTED 0x00004002U" in BRIDGE
assert "int (*validate_device)(void *ctx);" in HDR
assert ".validate_device = shl25_clmr_bridge_validate_device" in BRIDGE
assert "ret = shl25_clmr_bridge_read(ctx, SHL25_CLMR_REG_DEVCODE," in BRIDGE
assert "devcode == SHL25_CLMR_DEVCODE_EXPECTED ? 0 : -ENODEV;" in BRIDGE
boot=BOOT.split("int shl25_as99_clmr_boot_sequence(",1)[1]
sha=boot.index("ret = shl25_clmr_verify_firmware_sha256(firmware, firmware_bytes);")
validate=boot.index("ret = ops->validate_device(ctx);")
first_write=boot.index("ret = shl25_clmr_apply_regops(ops, ctx, shl25_boot_fw_download,")
assert sha < validate < first_write
assert "if (!ops->validate_device ||" in boot
assert boot.index("if (ret)\n\t\treturn ret;",validate)<first_write
assert "shl25_clmr_bridge_validate_device(" not in SPI
assert "shl25_as99_clmr_bridge_boot(" not in SPI
assert 'status = "disabled";' in DTS

# Exact data-word C2/C4 decoding: 0x4002 must be BE32 bytes 00 00 40 02.
def read_reply(raw):
    assert len(raw)==5
    return int.from_bytes(raw[1:],"big")
assert read_reply(bytes.fromhex("c400004002"))==0x4002
assert read_reply(bytes.fromhex("c400004003"))!=0x4002
assert read_reply(bytes.fromhex("c400000000"))!=0x4002
assert "get_unaligned_be32(reply + 1)" in BRIDGE
print("SHL25_AS99_C10_CLMR_ROM_DEVCODE_CHECK_BEFORE_REG_WRITE_PASS")
print("SHL25_AS99_C10_DEVCODE_WRONG_TARGET_FAIL_CLOSED_PASS")
