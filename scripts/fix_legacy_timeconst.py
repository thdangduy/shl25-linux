#!/usr/bin/env python3
"""Adapt original Linux 3.4 timeconst.pl for current Perl (5.22+).

The old defined(@val) expression is invalid. Select the cached value
before dereferencing a possibly absent hash entry. Only applies to one
verified source layout in an extracted Sharp GPL tree.
"""
from pathlib import Path
import argparse

OLD = "\t@val = @{$canned_values{$hz}};\n\tif (!defined(@val)) {\n\t\t@val = compute_values($hz);\n\t}\n"
NEW = "\tif (defined($canned_values{$hz})) {\n\t\t@val = @{$canned_values{$hz}};\n\t} else {\n\t\t@val = compute_values($hz);\n\t}\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    args=ap.parse_args()
    raw=args.source.read_bytes()
    if raw.count(OLD.encode("ascii")) != 1:
        raise SystemExit("REFUSE_UNRECOGNIZED_LINUX34_TIMECONST_SOURCE")
    fixed=raw.replace(OLD.encode("ascii"),NEW.encode("ascii"),1)
    args.source.write_bytes(fixed)
    print("SHL25_LINUX34_TIMECONST_MODERN_PERL_FIX_PASS")
if __name__=="__main__":main()
