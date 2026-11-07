#!/usr/bin/env python3
"""SHA-checked migration of Sharp OEM AS99 Andy DSI command packets.

OEM provenance:
 Sharp GPL bld010105/kernel/arch/arm/boot/dts/
 sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi

CI can verify the checked-in command manifest against generated
C arrays without the full OEM archive; source comparison can optionally
be run against the original OEM DTS extracted locally on Windows.

Usage:
  python upstream/verify_shl25_andy_panel.py --extract-oem original.dtsi --write
  python upstream/verify_shl25_andy_panel.py --verify
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "upstream" / "shl25-andy-oem-dsi.json"
DRIVER = ROOT / "drivers" / "gpu" / "drm" / "panel" / "panel-sharp-shl25-andy.c"
TRUTH = {
    "on": ("521f981db5686f8d11ff3b04404f29f0473b1b83bc4cd5c2ad56063535b2e499", 28),
    "off": ("c09f10cbd7e0150e77fab2922392201b033ffd19ea8c9afa596d65630aacdf10", 2),
}
MARKERS = {
    "on": ("/* OEM_INIT_ARRAY_BEGIN */", "/* OEM_INIT_ARRAY_END */", "OEM_INIT_SHA256"),
    "off": ("/* OEM_OFF_ARRAY_BEGIN */", "/* OEM_OFF_ARRAY_END */", "OEM_OFF_SHA256"),
}


def from_original(dtsi: Path):
    text = dtsi.read_text(encoding="utf-8")
    result = {}
    for name in ("on", "off"):
        match = re.search(
            r"qcom,mdss-dsi-" + name + r"-command\s*=\s*\[([0-9a-fA-F\s]+)\]",
            text,
        )
        if not match:
            raise AssertionError("Missing OEM " + name + " commands")
        raw = bytes.fromhex(match.group(1))
        result[name] = raw.hex()
    return result


def parse_raw(name: str, hexstr: str):
    raw = bytes.fromhex(hexstr)
    digest = hashlib.sha256(raw).hexdigest()
    expected, number = TRUTH[name]
    assert digest == expected, f"{name} vendor packet SHA-256 mismatch: {digest}"
    commands = []
    i = 0
    while i < len(raw):
        assert i + 7 <= len(raw), "Truncated OEM 7-byte command header"
        dtype, ack, zero1, zero2, delay, hi, lo = raw[i:i + 7]
        length = hi * 256 + lo
        i += 7
        payload = raw[i:i + length]
        i += length
        assert len(payload) == length, "OEM command payload truncation"
        assert dtype in (0x23, 0x29, 0x05), "Unexpected DSI packet type"
        assert (ack, zero1, zero2) == (1, 0, 0), "Unexpected OEM flags"
        assert 1 <= length <= 16, "Command exceeds compiled payload bound"
        if dtype == 0x23:
            assert length == 2, "Generic short write must have 2 bytes"
        if dtype == 0x05:
            assert length == 2 and payload[1] == 0, "Invalid DCS short command"
        if dtype == 0x29:
            assert length >= 3, "Generic long write invalid"
        commands.append((dtype, delay, length, payload))
    assert len(commands) == number, f"Expected {number} {name} commands"
    return commands, digest


def render(commands, name):
    output = f"static const struct shl25_andy_cmd shl25_andy_{name}[] = {{\n"
    for dtype, delay, length, payload in commands:
        data = ", ".join(f"0x{x:02x}" for x in payload)
        output += f"\t{{ 0x{dtype:02x}, {delay}, {length}, {{ {data} }} }},\n"
    return output + "};\n"


def generated(text: str, fixture: dict):
    for name in ("on", "off"):
        commands, digest = parse_raw(name, fixture[name + "_raw_hex"])
        start, end, digest_key = MARKERS[name]
        assert text.count(start) == 1 and text.count(end) == 1, "C marker missing"
        # Replace only the bounded command arrays, not driver logic.
        before, remaining = text.split(start, 1)
        _, after = remaining.split(end, 1)
        text = before + start + "\n" + render(commands, name) + end + after
        text = re.sub(
            r"(/\* " + digest_key + r"=)[^*]+(\*/)",
            r"\g<1>" + digest + r" \g<2>",
            text,
            count=1,
        )
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-oem", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.extract_oem:
        raw = from_original(args.extract_oem)
        for name in ("on", "off"):
            parse_raw(name, raw[name])
        manifest = {
            "provenance": "Sharp 2016 GPL bld010105 sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi",
            "panel": "SHL25 AS99 1080x1920 Sharp Andy CMD mode",
            "on_raw_hex": raw["on"],
            "off_raw_hex": raw["off"],
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    fixture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name in ("on", "off"):
        commands, digest = parse_raw(name, fixture[name + "_raw_hex"])
        print(f"OEM_AS99_ANDY_{name.upper()}_SHA256_PASS "
              f"packet_count={len(commands)} sha256={digest}")

    if args.extract_oem and not args.write:
        print("OEM_SOURCE_EXTRACTED_AND_VERIFIED")
    if args.write or args.verify:
        current = DRIVER.read_text(encoding="utf-8")
        expected = generated(current, fixture)
        if args.write:
            DRIVER.write_text(expected, encoding="utf-8")
            print("SHL25_ANDY_DRIVER_COMMAND_ARRAYS_WRITTEN")
        else:
            assert expected == current, "DRM panel DSI array differs from OEM SHA-pinned manifest"
            print("SHL25_ANDY_DRIVER_MATCHES_OEM_DSI_BYTES_PASS")
    # Fixed geometry from Sharp GPL, not an assumption about refresh rate.
    if args.verify:
        for fragment in (".clock = 144070", ".hdisplay = 1080", ".vdisplay = 1920",
                         "dsi->lanes = 4", "dsi->format = MIPI_DSI_FMT_RGB888",
                         "dsi->mode_flags = MIPI_DSI_MODE_LPM",
                         '"sharp,shl25-andy"'):
            assert fragment in expected, f"Missing Sharp panel characteristic: {fragment}"
        assert not re.search(r"dsi->mode_flags\s*=\s*MIPI_DSI_MODE_VIDEO", expected), "Panel must remain CMD mode"
        print("SHL25_ANDY_PANEL_MODE_PORCHES_AND_DSI_LANES_PASS")


if __name__ == "__main__":
    main()
