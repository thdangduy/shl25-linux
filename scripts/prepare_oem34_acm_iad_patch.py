#!/usr/bin/env python3
"""Create/review Sharp 2016 GPL Linux 3.4 CDC ACM IAD compatibility patch.

For Sharp's CONFIG_USB_ANDROID_SH_SERIALS, the f_acm.c firmware currently
omits IAD even though its CDC ACM function has TWO interface descriptors.
Windows usbccgp consequently creates separate MI_00 and MI_01 PDOs and
usbser.sys can fail start (Code 10, STATUS_NO_SUCH_DEVICE 0xc000000e).
Enabling the already-implemented IAD descriptor plus setting device
class/subclass/protocol to EF/02/01 during *native boot* should allow Windows
to treat this two-interface ACM as one function. This is an unproven hypothesis
until the recompiled OEM kernel is booted and enumerated.

This generator never changes a handset or the GPL source archive. It outputs a
reproducible git-format patch with a pinned source SHA.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import tarfile

SOURCE="kernel/drivers/usb/gadget/f_acm.c"
PINNED_SHA="c92f419579eb648d12df41873aa9944fcbbaf890c4e720f941e1029e0b05c039"

def digest(buf):return hashlib.sha256(buf).hexdigest()

def replace_exact(data,old,new,count):
    observed=data.count(old)
    if observed!=count:
        raise RuntimeError(f"REFUSE_UNEXPECTED_F_ACM_PATTERN expected={count} observed={observed} pattern={old[:90]!r}")
    return data.replace(old,new)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",required=True,type=Path)
    ap.add_argument("--out-patch",required=True,type=Path)
    ap.add_argument("--out-source",required=True,type=Path)
    ap.add_argument("--out-manifest",required=True,type=Path)
    args=ap.parse_args()

    with tarfile.open(args.archive,"r:gz") as tar:
        original=tar.extractfile(SOURCE).read()
    if digest(original)!=PINNED_SHA:
        raise RuntimeError("REFUSE_UNKNOWN_OEM_F_ACM_SOURCE")
    src=original.decode("utf8")
    # Remove the Sharp-exclusive conditional around the existing IAD object.
    old="#ifndef CONFIG_USB_ANDROID_SH_SERIALS\nstatic struct usb_interface_assoc_descriptor\nacm_iad_descriptor = {"
    new="static struct usb_interface_assoc_descriptor\nacm_iad_descriptor = {"
    src=replace_exact(src,old,new,1)
    old="};\n#endif /* CONFIG_USB_ANDROID_SH_SERIALS */\n\nstatic struct usb_interface_descriptor acm_control_interface_desc"
    new="};\n\nstatic struct usb_interface_descriptor acm_control_interface_desc"
    src=replace_exact(src,old,new,1)
    # Include IAD before control+data interface descriptor for FS, HS and SS.
    old="#ifndef CONFIG_USB_ANDROID_SH_SERIALS\n\t(struct usb_descriptor_header *) &acm_iad_descriptor,\n#endif /* CONFIG_USB_ANDROID_SH_SERIALS */"
    new="\t(struct usb_descriptor_header *) &acm_iad_descriptor,"
    src=replace_exact(src,old,new,3)
    # Set first interface index for Sharp as well; avoid hardcoding MI_00.
    old="#ifndef CONFIG_USB_ANDROID_SH_SERIALS\n\tacm_iad_descriptor.bFirstInterface = status;\n#endif /* CONFIG_USB_ANDROID_SH_SERIALS */"
    new="\tacm_iad_descriptor.bFirstInterface = status;"
    src=replace_exact(src,old,new,1)
    # Sharp uses string indexes only for 2 interfaces. Keep IAD iFunction=0.
    # Non-Sharp existing ACM_IAD_IDX allocation remains conditional and untouched.
    if src.count("acm_iad_descriptor.iFunction = status;")!=1:
        raise RuntimeError("IAD_I_FUNCTION_PRESENT_UNEXPECTEDLY")
    if "#ifndef CONFIG_USB_ANDROID_SH_SERIALS\n\t\tstatus = usb_string_id" not in src:
        raise RuntimeError("NON_SHARP_IAD_STRING_GUARD_CHANGED")
    diff="".join(difflib.unified_diff(original.decode("utf8").splitlines(keepends=True),
        src.splitlines(keepends=True),fromfile="a/"+SOURCE,tofile="b/"+SOURCE,n=5))
    if not diff:raise RuntimeError("EMPTY_PATCH")
    for p in [args.out_patch,args.out_source,args.out_manifest]:
        p.parent.mkdir(parents=True,exist_ok=True)
    args.out_patch.write_text(diff,encoding="utf8",newline="\n")
    args.out_source.write_text(src,encoding="utf8",newline="\n")
    manifest={"source":SOURCE,"sha_original":digest(original),
      "sha_patched":digest(src.encode("utf8")),"sha_patch":digest(diff.encode("utf8")),
      "applies_only_to":"OEM 3.4 kernel source copied from verified Sharp GPL bld010105",
      "expected":"Expose 2-interface CDC ACM as one USB function (IAD), all speeds",
      "test_requirements":"CI zImage compile, boot native, verify Windows usbser Code10 clears and serial read/write",
      "limitations":"No claim of USB PING/PONG PASS from static patch"}
    args.out_manifest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
