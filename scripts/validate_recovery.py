#!/usr/bin/env python3
"""Offline validation: A51w OEM ARM32 kernel, DT/QCDT and TWRP 5.1 ramdisk.

This does not prove the phone boots. Do NOT flash based on an offline PASS.
"""
from pathlib import Path
from hashlib import sha256
import gzip,json,struct,sys
p=Path(sys.argv[1])
b=p.read_bytes()
assert b[:8]==b"ANDROID!", "NOT_ANDROID_RECOVERY"
ksz,kaddr,rsz,raddr,ssz,saddr,taddr,page,dt_len=struct.unpack_from("<9I",b,8)
assert (kaddr,raddr,taddr,page)==(0x80008000,0x81000000,0x80000100,2048),"A51W_LOAD_ADDRESSES_CHANGED"
assert 0<len(b)<=33554432,"RECOVERY_EXCEEDS_32MiB"
pad=lambda n:(n+page-1)//page*page
kernel=b[page:page+ksz]
ramoffset=page+pad(ksz)
ram=b[ramoffset:ramoffset+rsz]
dtoff=ramoffset+pad(rsz)+pad(ssz)
dt=b[dtoff:dtoff+dt_len]
assert kernel[0x24:0x28]==bytes.fromhex("18286f01"),"NOT_ARM32_STOCK_KERNEL"
assert sha256(kernel).hexdigest()=="163d25276cb4bb264d58a342a1853b552fd50a0c3425e544a8f65a270572fce4","WRONG_A51W_KERNEL"
assert dt_len==1687552 and dt[:4]==b"QCDT","NOT_A51W_QCDT"
assert sha256(dt).hexdigest()=="c740b0433fa07b3c9c7aa1ea153bb2b2a629d595f3cd7f8f6f7793c5bd79f79d","WRONG_A51W_DT"
assert ram[:3]==b"\x1f\x8b\x08","NOT_GZIP_RAMDISK"
raw=gzip.decompress(ram); files={};pos=0
while pos+110<=len(raw):
    assert raw[pos:pos+6] in (b"070701",b"070702"),"RAMDISK_CPIO_HEADER_INVALID"
    x=[int(raw[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
    size,nlen=x[6],x[11]
    assert 0<nlen<2000 and 0<=size<=len(raw),"RAMDISK_CPIO_BOUNDS"
    name=raw[pos+110:pos+110+nlen].rstrip(b"\0").decode("utf-8","replace")
    off=(pos+110+nlen+3)&~3
    if name=="TRAILER!!!":break
    if name in ("init","init.rc","init.recovery.qcom.rc","sbin/recovery",
                "sbin/adbd","sbin/twrp","etc/recovery.fstab"):
        files[name]=raw[off:off+size]
    pos=(off+size+3)&~3
for name in ("init","init.rc","init.recovery.qcom.rc","sbin/recovery",
             "sbin/adbd","etc/recovery.fstab"):
    assert files.get(name),f"RAMDISK_MISSING_{name}"
assert files["init"].startswith(b"\x7fELF"),"INIT_NOT_ELF"
assert files["sbin/recovery"].startswith(b"\x7fELF"),"RECOVERY_NOT_ELF"
assert (b"TWRP" in files["sbin/recovery"] or b"twrp" in files["sbin/recovery"].lower()),"RECOVERY_BIN_NO_TWRP_SIGNATURE"
assert b"/sys/class/leds/lcd-backlight/brightness 102" in files["init.recovery.qcom.rc"],"A51W_LCD_BACKLIGHT_INIT_MISSING"
assert b"setprop sys.usb.config adb" in files["init.recovery.qcom.rc"],"A51W_ADB_TRIGGER_MISSING"
report=dict(image=p.name,bytes=len(b),sha256=sha256(b).hexdigest(),
  kernel_sha256=sha256(kernel).hexdigest(),dt_sha256=sha256(dt).hexdigest(),
  ramdisk_file_count=len(files),ramdisk_bytes=len(raw),
  twrp_executable_detected=True,
  verification="OFFLINE_OEM_KERNEL_QCDT_RAMDISK_AND_TWRP_PRESENT_PASS",
  phone_boot_test="NOT_PERFORMED",phone_flash="NEVER_PERFORMED")
(p.parent/"A51W_RECOVERY_BUILD_MANIFEST.json").write_text(json.dumps(report,indent=2)+"\n")
print("A51W_TWRP51_OFFLINE_PASS",json.dumps(report),flush=True)
