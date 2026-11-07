#!/usr/bin/env python3
"""Prepare Sharp SHL25 native Linux 3.4 IAD v4 experiment.

Makes guarded edits to the existing offline build script and PID1 source.
No USB/device/ADB access, flash, or runtime host-driver changes.
"""
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parent.parent

def rewrite(path, edits):
    original=path.read_text(encoding="utf8")
    data=original
    for before,after in edits:
        count=data.count(before)
        if count!=1:
            raise SystemExit("REFUSE_UNEXPECTED_ANCHOR "+str(path)+" count="+str(count)+" before="+repr(before[:70]))
        data=data.replace(before,after,1)
    path.write_text(data,encoding="utf8",newline="\n")
    print("IAD_V4_SOURCE_READY",path.name,"SHA256="+sha256(path.read_bytes()).hexdigest())

build=ROOT/"scripts"/"build-oem-kernel34-gserial.sh"
old='PATCH="$ROOT/patches/oem34/0001-sharp-gserial-reuse-existing-ttygs.patch"'
new=old+'''
PATCH_IAD="$ROOT/patches/oem34/0002-sharp-usb-acm-enable-iad.patch"
EXPECTED_PATCHED_F_ACM="4fe8207f89b6f8e803018da346bc07d809ff3af7d54a78f6daa17d7df0e61509"'''
old2='echo "OEM_SHARP_GSERIAL_PATCH_APPLY_PASS"'
new2=old2+'''
git -C "$EXTRACT" apply --check "$PATCH_IAD"
git -C "$EXTRACT" apply "$PATCH_IAD"
ACTUAL_IAD_SHA="$(sha256sum "$SRC/drivers/usb/gadget/f_acm.c" | cut -d' ' -f1)"
[ "$ACTUAL_IAD_SHA" = "$EXPECTED_PATCHED_F_ACM" ] || {
    echo "SHL25_IAD_SOURCE_MISMATCH=$ACTUAL_IAD_SHA"; exit 12;
}
echo "OEM_SHARP_CDC_ACM_IAD_PATCH_APPLY_PASS"'''
rewrite(build,[
    (old,new),
    (old2,new2),
    ('Patched u_serial.c SHA256: $ACTUAL_PATCH_SHA',
     'Patched u_serial.c SHA256: $ACTUAL_PATCH_SHA\nAdditional patch: patches/oem34/0002-sharp-usb-acm-enable-iad.patch\nPatched f_acm.c SHA256: $ACTUAL_IAD_SHA')
])

pid=ROOT/"diagnostics"/"k34_native_init.c"
rewrite(pid,[
  ('trace_usb("START native_v3 CDC_ACM_without_adbd");',
   'trace_usb("START native_v4 CDC_ACM_IAD_EF0201_without_adbd");'),
  ('if(usb_write("idProduct","0001")<0)return -1;',
   'if(usb_write("idProduct","0002")<0)return -1;'),
  ('    if(usb_write("f_modem/acm_transports","tty")<0)return -1;',
   '    if(usb_write("bDeviceClass","239")<0)return -1;\n'
   '    if(usb_write("bDeviceSubClass","2")<0)return -1;\n'
   '    if(usb_write("bDeviceProtocol","1")<0)return -1;\n'
   '    if(usb_write("f_modem/acm_transports","tty")<0)return -1;')
])
print("SHL25_K34_USB_IAD_V4_SOURCE_TRANSFORM_PASS")
