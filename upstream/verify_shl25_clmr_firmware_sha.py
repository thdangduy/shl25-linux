#!/usr/bin/env python3
"""Source-pinned firmware SHA-256 guard for the C3 CLMR boot executor.

This tests source and known OEM firmware bytes locally, without board I/O.
CI runs without including or distributing the vendor firmware.
"""
import argparse
import hashlib
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"drivers/spi/shl25-as99-clmr-boot.c"
EXPECTED="a3da76d0bbc1154a774e097bfd851026cde7a09c3983ea9315181835510145f5"
SIZE=59136

def check(filename=None):
    c=SOURCE.read_text(encoding="utf-8")
    m=re.search(r"static const u8 shl25_clmr_fw_digest\[32\]\s*=\s*\{([^}]+)\};",c,re.S)
    assert m,"SOURCE_SHA_DIGEST_ARRAY_MISSING"
    vals=[int(x,16) for x in re.findall(r"0x([0-9a-fA-F]{2})",m.group(1))]
    assert len(vals)==32 and bytes(vals).hex()==EXPECTED,"CLMR_SHA_CONSTANT_MISMATCH"
    assert "crypto_alloc_shash(\"sha256\", 0, 0)" in c
    assert "crypto_shash_digest(desc, fw, len, digest)" in c
    assert "memcmp(digest, shl25_clmr_fw_digest, sizeof(digest))" in c
    assert "ret = -EKEYREJECTED;" in c
    assert "crypto_free_shash(tfm)" in c
    assert "if (!fw || len != SHL25_CLMR_FW_BYTES)" in c
    boot=c.split("int shl25_as99_clmr_boot_sequence(",1)[1]
    guard=boot.index("ret = shl25_clmr_verify_firmware_sha256(firmware, firmware_bytes);")
    first_io=boot.index("shl25_clmr_apply_regops(ops, ctx, shl25_boot_fw_download")
    assert guard<first_io,"UNVERIFIED_FIRMWARE_SENT_TO_CLMR"
    assert boot.index("if (ret)\n\t\treturn ret;",guard)<first_io
    if filename:
        b=Path(filename).read_bytes()
        assert len(b)==SIZE,"OEM_CLMR_FW_LENGTH_MISMATCH"
        assert hashlib.sha256(b).hexdigest()==EXPECTED,"OEM_CLMR_FW_SHA_MISMATCH"
        corrupt=bytearray(b)
        corrupt[0]^=1
        assert hashlib.sha256(corrupt).hexdigest()!=EXPECTED,"CORRUPT_IMAGE_ACCEPTED"
        print("SHL25_AS99_CLMR_OEM_FW_REAL_BYTES_SHA_PASS",SIZE)
        print("SHL25_AS99_CLMR_FW_CORRUPTION_REJECT_TEST_PASS")
    print("SHL25_AS99_CLMR_C5_KERNEL_SHA256_PRE_IO_GATE_SOURCE_PASS")
    print("SHL25_AS99_CLMR_C5_NO_VENDOR_BINARY_IN_GIT_PASS")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--oem-firmware",type=Path)
    args=ap.parse_args()
    check(args.oem_firmware)
