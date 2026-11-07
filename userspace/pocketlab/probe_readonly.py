#!/usr/bin/env python3
"""SHL25 Pocket Lab: strictly READ-ONLY hardware node discovery.

This is a userspace discovery baseline for the future Linux 6.1 GUI.
It does NOT probe by opening device nodes, enabling RF, changing GPIOs,
requesting firmware, issuing ioctls, scanning wireless channels or
running system commands. Mere presence of a node is never "PASS".
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "hardware-manifest.json"

# A /dev entry may be a stale dummy: it is only a NODE_FOUND candidate.
CANDIDATES = {
    "display_touch": [
        ("dev/dri", "card[0-9]*"), ("dev", "fb[0-9]*"),
        ("dev/input", "event*"),
    ],
    "wifi": [("sys/class/net", "wlan*"), ("sys/class/net", "wlp*")],
    "bluetooth": [("sys/class/bluetooth", "hci*")],
    "felica_nfc": [
        ("dev", "felica*"), ("dev", "snfc*"), ("dev", "pn54x*"),
        ("sys/class/nfc", "nfc*"),
    ],
    "infrared": [("dev", "*irda*"), ("dev", "*shirda*")],
    "tv_tuner": [
        ("dev/dvb", "adapter*/frontend*"),
        ("dev", "tuner*"), ("dev", "isdb*"),
    ],
    "sensors_grip": [
        ("sys/bus/iio/devices", "iio:device*"),
        ("dev/input", "event*"),
    ],
    "usb": [("dev", "ttyGS*"), ("dev", "ttyACM*"), ("sys/class/udc", "*")],
}

def inventory(root: Path) -> dict:
    """Report only host kernel node presence, never hardware readiness."""
    root = root.resolve()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = []
    for module in data["modules"]:
        seen = set()
        for base, pattern in CANDIDATES.get(module["id"], []):
            directory = root / base
            if directory.is_dir():
                for path in directory.glob(pattern):
                    try:
                        # symlinks to kernel devices still count as
                        # candidate paths, never as hardware proof.
                        rel = path.relative_to(root).as_posix()
                    except ValueError:
                        continue
                    seen.add("/" + rel)
        result.append({
            "id": module["id"],
            "label": module["label"],
            "source_status": module["status"],
            "read_only_node_status": "NODE_FOUND_UNVERIFIED" if seen else "NO_CANDIDATE_NODE",
            "candidate_paths": sorted(seen),
        })
    return {
        "schema_version": 1,
        "device": data["project"],
        "mode": "READ_ONLY_NO_HARDWARE_IO",
        "warning": "No node presence or OEM source alone proves Linux 6.1 hardware functionality.",
        "modules": result,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"),
                        help="Read-only root for probe; test fixtures may use a temp dir")
    parser.add_argument("--module", help="Display just one module ID")
    args = parser.parse_args()
    result = inventory(args.root)
    if args.module:
        result["modules"] = [m for m in result["modules"] if m["id"] == args.module]
        if not result["modules"]:
            parser.error("Unknown module ID: " + args.module)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
