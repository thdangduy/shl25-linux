#!/usr/bin/env python3
"""Fix two proven unsequenced accesses in Sharp GPL 3.4 cpufreq_interactive.c.

Exact-layout, source-copy-only compatibility fix for the OEM Linux 3.4
kernel build. Refuses unknown source and never changes device state.
"""
from pathlib import Path
import argparse

OLD = '\tret += sprintf(buf + --ret, "\\n");'
NEW = '\tif (ret > 0)\n\t\t--ret;\n\tret += sprintf(buf + ret, "\\n");'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    args=parser.parse_args()
    raw=args.source.read_bytes()
    old=OLD.encode("ascii")
    if raw.count(old)!=2:
        raise SystemExit("UNKNOWN_SHARP_CPUFREQ_SOURCE_REFUSING_PATCH")
    modified=raw.replace(old,NEW.encode("ascii"),2)
    args.source.write_bytes(modified)
    print("SHL25_OEM34_CPUFREQ_SEQUENCE_POINT_FIX_PASS")
if __name__=="__main__":
    main()
