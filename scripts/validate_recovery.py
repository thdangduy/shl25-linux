#!/usr/bin/env python3
"""Validate OPPO A51w image header, QCDT, and board-specific recovery startup."""
from pathlib import Path
from hashlib import sha256
import gzip,json,struct,sys
p=Path(sys.argv[1]); b=p.read_bytes()
assert b[:8]==b"ANDROID!", "NOT_ANDROID_RECOVERY_IMAGE"
ksz,ka,rsz,ra,ssz,sa,tags,page,dt_len=struct.unpack_from("<9I",b,8)
assert (ka,ra,tags,page)==(0x80008000,0x81000000,0x80000100,2048), "WRONG_LOAD_ADDRESSES"
assert len(b)<=33554432, "EXCEEDS_32_MIB_RECOVERY"
align=lambda n:(n+page-1)//page*page
offset=page+align(ksz)
ram=b[offset:offset+rsz]
assert len(ram)==rsz and ram[:3]==b"\x1f\x8b\x08", "NOT_GZIP_RAMDISK"
dtoff=offset+align(rsz)+align(ssz)
dt=b[dtoff:dtoff+dt_len]
assert len(dt)==1687552 and dt[:4]==b"QCDT", "WRONG_QCDT"
expected="c740b0433fa07b3c9c7aa1ea153bb2b2a629d595f3cd7f8f6f7793c5bd79f79d"
assert sha256(dt).hexdigest()==expected, "NOT_ORIGINAL_A51W_A17_DT"
raw=gzip.decompress(ram); files={}; pos=0
targets=("init.rc","init.recovery.qcom.rc","init.recovery.service.rc",
         "init.recovery.usb.rc","sbin/recovery","sbin/adbd","sbin/twrp")
while pos+110<=len(raw):
    assert raw[pos:pos+6] in (b"070701",b"070702"),"INVALID_RECOVERY_CPIO_HEADER"
    fields=[int(raw[pos+i:pos+i+8],16) for i in range(6,110,8)]
    size,namesize=fields[6],fields[11]
    name=raw[pos+110:pos+110+namesize].rstrip(b"\0").decode("utf-8","replace")
    off=(pos+110+namesize+3)&~3
    if name=="TRAILER!!!": break
    if name in targets: files[name]=raw[off:off+size]
    pos=(off+size+3)&~3
for name in targets:
    assert name in files and files[name],f"MISSING_RECOVERY_FILE_{name}"
assert (b"import /init.recovery."+b"$"+b"{ro.hardware}.rc") in files["init.rc"],"NO_HARDWARE_INIT_IMPORT"
assert b"/sys/class/leds/lcd-backlight/brightness 102" in files["init.recovery.qcom.rc"],"NO_A51W_LCD_INIT"
assert b"setprop sys.usb.config adb" in files["init.recovery.qcom.rc"],"NO_A51W_ADB_INIT"
manifest=dict(image=p.name,bytes=len(b),sha256=sha256(b).hexdigest(),
              kernel_load=hex(ka),ramdisk_load=hex(ra),tags_load=hex(tags),
              pagesize=page,qcdt_bytes=len(dt),
              hardware_init="A51W_LCD_USB_ADB_PRESENT",
              verification="OFFLINE_HEADER_QCDT_RAMDISK_PASS",
              phone_boot_test="NOT_PERFORMED",phone_flash="NEVER_PERFORMED")
(p.parent/"A51W_RECOVERY_BUILD_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("A51W_OFFLINE_RECOVERY_VALIDATION_PASS",json.dumps(manifest),flush=True)
