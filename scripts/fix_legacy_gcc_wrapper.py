#!/usr/bin/env python3
"""Adapt Sharp GPL 3.4 GCC warning wrapper (Python 2) for Python 3 host.

Changes ONLY the extracted source copy in .build; does not edit the
official archive, the kernel driver patch, BOOT, or the device.
"""
from pathlib import Path
import argparse

REWRITES = [
    ('print "error, forbidden warning:", m.group(2)',
     'print("error, forbidden warning:", m.group(2))'),
    ('proc = subprocess.Popen(args, stderr=subprocess.PIPE)',
     'proc = subprocess.Popen(args, stderr=subprocess.PIPE, universal_newlines=True)'),
    ('            print line,',
     '            print(line, end="")'),
    ("print args[0] + ':',e.strerror",
     "print(args[0] + ':', e.strerror)"),
    ("print 'Is your PATH set correctly?'",
     "print('Is your PATH set correctly?')"),
    ("print ' '.join(args), str(e)",
     "print(' '.join(args), str(e))"),
]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("wrapper",type=Path)
    args=p.parse_args()
    data=args.wrapper.read_text(encoding="utf8")
    for before,after in REWRITES:
        if data.count(before)!=1:
            raise SystemExit(f"UNKNOWN_SHARP_GCC_WRAPPER_LAYOUT: {before!r}")
        data=data.replace(before,after,1)
    compile(data,str(args.wrapper),"exec")
    args.wrapper.write_text(data,encoding="utf8",newline="\n")
    print("SHL25_LEGACY_GCC_WRAPPER_PY3_CONVERT_PASS")
if __name__=="__main__":main()
