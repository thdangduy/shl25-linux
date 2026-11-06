#!/usr/bin/env python3
"""Reject recovery images with wrong OPPO A51w header/board/partition size."""
from pathlib import Path
from hashlib import sha256
import sys,struct,json
p=Path(sys.argv[1]); b=p.read_bytes()
assert b[:8]==b"ANDROID!", "NOT_ANDROID_RECOVERY_IMAGE"
ksz,ka,rsz,ra,ssz,sa,tags,page,dt_len=struct.unpack_from("<9I",b,8)
assert (ka,ra,tags,page)==(0x80008000,0x81000000,0x80000100,2048), "WRONG_LOAD_ADDRESSES"
assert len(b)<=33554432, "EXCEEDS_32_MIB_RECOVERY"
align=lambda n:(n+page-1)//page*page
dtoff=page+align(ksz)+align(rsz)+align(ssz)
dt=b[dtoff:dtoff+dt_len]
assert len(dt)==1687552 and dt[:4]==b"QCDT", "WRONG_QCDT"
expected="c740b0433fa07b3c9c7aa1ea153bb2b2a629d595f3cd7f8f6f7793c5bd79f79d"
assert sha256(dt).hexdigest()==expected, "NOT_ORIGINAL_A51W_A17_DT"
manifest=dict(image=p.name,bytes=len(b),sha256=sha256(b).hexdigest(),
              kernel_load=hex(ka),ramdisk_load=hex(ra),tags_load=hex(tags),
              pagesize=page,qcdt_bytes=len(dt),verification="OFFLINE_FORMAT_SHA256_PASS",
              phone_boot_test="NOT_PERFORMED",phone_flash="NEVER_PERFORMED")
(p.parent/"A51W_RECOVERY_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("A51W_OFFLINE_RECOVERY_VALIDATION_PASS",json.dumps(manifest),flush=True)
