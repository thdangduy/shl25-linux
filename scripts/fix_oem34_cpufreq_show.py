#!/usr/bin/env python3
"""Fix a Sharp GPL 3.4 cpufreq_interactive.c undefined-sequencing bug.

Original show_target_loads() and show_above_hispeed_delay() have:
    ret += sprintf(buf + --ret, "\n");
This modifies ret both through pre-decrement and compound assignment,
without valid sequencing, and GCC 4.9 warns -Wsequence-point.

The replacement overwrites the existing trailing separator with newline,
leaving the original snprintf trailing NUL in place, and handles zero entries
without writing before the start of buf.

The official source archive is unmodified; only an extracted working copy
with the pinned original SHA256 is accepted.
"""
from pathlib import Path
import argparse
import hashlib

EXPECTED_SHA256 = "a25c5b37f3debc6eaf844c684adbeb45a60cde7618007b0b2182e87db21a183b"
BEFORE = b'\tret += sprintf(buf + --ret, "\\n");'
AFTER = b'\tif (ret > 0)\n\t\tbuf[ret - 1] = \'\\n\';\n\telse\n\t\tret = sprintf(buf, "\\n");'

def main():
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    args=p.parse_args()
    data=args.source.read_bytes()
    h=hashlib.sha256(data).hexdigest()
    if h!=EXPECTED_SHA256:
        raise SystemExit("REFUSE_CPUSOURCE_HASH_MISMATCH: "+h)
    if data.count(BEFORE)!=2:
        raise SystemExit("REFUSE_CPUSOURCE_ANCHOR_MISMATCH")
    result=data.replace(BEFORE,AFTER)
    if result.count(BEFORE)!=0 or result.count(AFTER)!=2:
        raise SystemExit("CPUFREQ_REPLACEMENT_INTEGRITY_FAIL")
    args.source.write_bytes(result)
    print("SHL25_OEM34_CPUFREQ_SEQUENCE_POINT_FIXED sha256="+hashlib.sha256(result).hexdigest())

if __name__=="__main__":
    main()
