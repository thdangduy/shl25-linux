#!/usr/bin/env python3
"""Generate and verify a minimal Sharp OEM Linux 3.4 gserial reuse patch.

Only modifies a COPY of GPL driver extracted from the known Sharp bld010105
kernel archive. Never touches live phone, TWRP, BOOT/Recovery or firmware.
This is not a claim of target kernel build or hardware PASS.
"""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import tarfile

ORIGINAL_SHA = "c335658bb106a1920b0562c37637f50b5de008604890f683a1897fbf8b21285a"
OEM_PATH = "kernel/drivers/usb/gadget/u_serial.c"
ORIGINAL_SNIPPET = """\
\tif (count == 0 || count > N_PORTS)
\t\treturn -EINVAL;

\tgs_tty_driver = alloc_tty_driver(count);
"""
PATCHED_SNIPPET = """\
\tif (count == 0 || count > N_PORTS)
\t\treturn -EINVAL;

#ifdef CONFIG_USB_ANDROID_SH_SERIALS
\t/*
\t * Sharp's MDLM/OBEX function initialization can register ttyGS0/1
\t * before the CDC-ACM modem function is bound. Re-registering them
\t * produces -EEXIST and can silently break USB serial enumeration.
\t * Reuse the existing gserial device nodes if they cover this request;
\t * do NOT expand a live tty driver or silently accept out-of-range
\t * port numbers.
\t */
\tif (gs_tty_driver) {
\t\tif (n_ports && count <= n_ports) {
\t\t\tpr_info("gserial_setup: reusing %u existing ttyGS ports\n",
\t\t\t\tn_ports);
\t\t\treturn 0;
\t\t}
\t\tpr_err("gserial_setup: requested %u ports, existing %u\n",
\t\t\tcount, n_ports);
\t\treturn -EBUSY;
\t}
#endif

\tgs_tty_driver = alloc_tty_driver(count);
"""
# The C compiler expects a literal escaped backslash-n inside strings.
PATCHED_SNIPPET = PATCHED_SNIPPET.replace('ttyGS ports\n"', 'ttyGS ports\\n"').replace('existing %u\n"', 'existing %u\\n"')
def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--out-patch", type=Path, required=True)
    ap.add_argument("--out-source", type=Path, required=True)
    ap.add_argument("--out-manifest", type=Path, required=True)
    args = ap.parse_args()
    with tarfile.open(args.archive, "r:gz") as tf:
        member=tf.getmember(OEM_PATH)
        original=tf.extractfile(member).read()
    if sha(original) != ORIGINAL_SHA:
        raise SystemExit("REFUSE_UNKNOWN_OEM_SOURCE_SHA")
    old=original.decode("utf8")
    if old.count(ORIGINAL_SNIPPET) != 1:
        raise SystemExit("REFUSE_ANCHOR_MISMATCH")
    new=old.replace(ORIGINAL_SNIPPET,PATCHED_SNIPPET,1)
    if new.count("#ifdef CONFIG_USB_ANDROID_SH_SERIALS\n\t/*\n\t * Sharp's MDLM/OBEX") != 1:
        raise SystemExit("PATCH_GUARD_MISSING")
    if new.index("if (gs_tty_driver)",new.index("int gserial_setup")) > new.index("alloc_tty_driver(count)",new.index("int gserial_setup")):
        raise SystemExit("REUSE_GUARD_NOT_BEFORE_TTY_ALLOCATION")
    assert "return -EBUSY;" in new
    diff=list(difflib.unified_diff(old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="a/"+OEM_PATH,tofile="b/"+OEM_PATH,n=5))
    if not diff:raise SystemExit("EMPTY_PATCH")
    patch="".join(diff)
    args.out_patch.parent.mkdir(parents=True,exist_ok=True)
    args.out_source.parent.mkdir(parents=True,exist_ok=True)
    args.out_manifest.parent.mkdir(parents=True,exist_ok=True)
    args.out_patch.write_text(patch,encoding="utf8",newline="\n")
    args.out_source.write_bytes(new.encode("utf8"))
    manifest={
      "source":"Sharp GPL bld010105 kernel.tar.gz, u_serial.c",
      "source_sha256":sha(original),
      "patched_sha256":sha(new.encode("utf8")),
      "patch_sha256":sha(patch.encode("utf8")),
      "guard":"CONFIG_USB_ANDROID_SH_SERIALS only",
      "expected":"if requested count <= already registered ttyGS port count, reuse; otherwise -EBUSY",
      "root_cause":"tty_register_device ttyGS0 duplicate -EEXIST in TWRP 3.4 dmesg",
      "caveat":"not compiled with OEM kernel/toolchain; not boot tested; kernel patch review required"
    }
    args.out_manifest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print("SHARP_OEM34_GSERIAL_PATCH_GENERATED")
    print(json.dumps(manifest,indent=2))
if __name__ == "__main__":main()
