#!/usr/bin/env python3
"""Read-only board facts validator for a compiled SHL25 FDT (standard library).

Checks the actual DTB, not source grep. These constraints are grounded in
Sharp's GPL 3.4 sharp-common-pm8941.dtsi / sharp-common-sdcc.dtsi.
This validation does NOT establish bootability or validate memory carveouts.
"""
from pathlib import Path
import struct
import sys

def parse_fdt(b):
    if len(b) < 40 or b[:4] != bytes.fromhex("d00dfeed"):
        raise ValueError("not a valid FDT")
    totalsize, off_struct, off_strings, _, ver, _, _, size_strings, size_struct = struct.unpack_from(">9I", b, 4)
    if totalsize != len(b) or ver < 16:
        raise ValueError("invalid FDT header")
    data = b[off_struct:off_struct + size_struct]
    strings = b[off_strings:off_strings + size_strings]
    if len(data) != size_struct or len(strings) != size_strings:
        raise ValueError("truncated FDT")
    result = {}
    stack = []
    pos = 0
    while pos < len(data):
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == 1:
            end = data.index(b"\x00", pos)
            name = data[pos:end].decode("ascii")
            pos = (end + 4) & ~3
            stack.append(name)
            result["/" + "/".join(s for s in stack if s)] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            end = strings.index(b"\x00", nameoff)
            key = strings[nameoff:end].decode("ascii")
            result["/" + "/".join(s for s in stack if s)][key] = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            break
        else:
            raise ValueError("unknown FDT token: " + str(token))
    return result

def be32(prop):
    if len(prop) != 4:
        raise ValueError("bad 32-bit FDT cell")
    return struct.unpack(">I", prop)[0]

def node_by_suffix(tree, suffix):
    matches = [node for path, node in tree.items() if path.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one {suffix} node; found {len(matches)}")
    return matches[0]

def main():
    if len(sys.argv) != 2:
        sys.exit("usage: verify_shl25_dtb.py <path_to_compiled_dtb>")
    tree = parse_fdt(Path(sys.argv[1]).read_bytes())
    root = tree["/"]
    compat = root["compatible"].split(b"\x00")
    for part in (b"qcom,sharp-as99", b"qcom,msm8974pro", b"qcom,msm8974"):
        assert part in compat, f"missing SoC compatible: {part!r}"
    rail = {}
    for name, voltage in (("s1", 1300000), ("s2", 2150000), ("s3", 1800000),
                          ("l6", 1800000), ("l20", 2950000)):
        node = node_by_suffix(tree, "/rpm-requests/regulators-1/" + name)
        assert be32(node["regulator-min-microvolt"]) == voltage, name
        assert be32(node["regulator-max-microvolt"]) == voltage, name
        assert "regulator-always-on" in node, f"Sharp {name} should be always-on"
        rail[name] = node

    sdhc1 = node_by_suffix(tree, "/soc/mmc@f9824900")
    assert sdhc1.get("status", b"okay\x00").rstrip(b"\x00") in (b"okay", b"ok")
    assert "non-removable" in sdhc1
    assert "vmmc-supply" in sdhc1 and "vqmmc-supply" in sdhc1
    # Prove MMC supply phandles resolve to Sharp regulator L20 / S3,
    # not merely that the DTB happens to contain all those nodes.
    assert be32(sdhc1["vmmc-supply"]) == be32(rail["l20"]["phandle"])
    assert be32(sdhc1["vqmmc-supply"]) == be32(rail["s3"]["phandle"])

    # Sharp's known-good stock BOOT QCDT FDT uses exactly /memory with
    # an empty reg to be populated by the bootloader. The pristine
    # upstream msm8974 base instead uses /memory@0, which may miss a
    # Sharp-specific fixup by path. Keep the vendor node name.
    memory = tree.get("/memory")
    assert memory is not None, "SHL25 /memory node is absent"
    assert "/memory@0" not in tree, "unverified upstream /memory@0 still present"
    assert memory.get("device_type", b"").rstrip(bytes([0])) == b"memory"
    assert memory.get("reg") == b"", "SHL25 memory must await bootloader fixup"
    print("SHL25_STOCK_COMPATIBLE_MEMORY_NODE=PASS")
    print("BOOTLOADER_FIXUP_NOT_YET_PROVEN: /memory reg remains empty")
    print("SHL25_BOARD_RAILS_AND_EMMC_FDT_VALIDATED=PASS")
    print("WARNING: compile/FDT validation does NOT prove CPU boot or eMMC power-up")

if __name__ == "__main__":
    main()
