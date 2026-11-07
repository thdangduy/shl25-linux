#!/usr/bin/env python3
"""Offline fixture tests for future Linux 6.1 Pocket Lab hardware inventory."""
import json
import tempfile
import unittest
from pathlib import Path

from probe_readonly import CANDIDATES, MANIFEST, inventory


class ProbeReadOnlyTests(unittest.TestCase):
    def test_manifest_schema_and_unique_module_ids(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        mods = data["modules"]
        ids = [m["id"] for m in mods]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(mods), 10)
        for m in mods:
            self.assertTrue(m["label"])
            self.assertTrue(m["status"])
            self.assertTrue(m["needs"])
            self.assertTrue(m["source"])

    def test_empty_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = inventory(root)
            self.assertEqual(data["mode"], "READ_ONLY_NO_HARDWARE_IO")
            for m in data["modules"]:
                self.assertEqual(m["read_only_node_status"], "NO_CANDIDATE_NODE")
                self.assertEqual(m["candidate_paths"], [])

    def test_candidate_nodes_never_claim_hardware_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = [
                "sys/class/net/wlan0",
                "sys/class/bluetooth/hci0",
                "dev/dvb/adapter0/frontend0",
                "dev/input/event0",
                "dev/ttyGS0",
                "dev/snfc0",
            ]
            for path in candidates:
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch()
            before = [(p.relative_to(root).as_posix(), p.stat().st_size)
                      for p in root.rglob("*") if p.is_file()]
            data = inventory(root)
            after = [(p.relative_to(root).as_posix(), p.stat().st_size)
                     for p in root.rglob("*") if p.is_file()]
            self.assertEqual(before, after)
            found = {m["id"] for m in data["modules"]
                     if m["read_only_node_status"] == "NODE_FOUND_UNVERIFIED"}
            self.assertTrue({
                "wifi", "bluetooth", "tv_tuner", "display_touch",
                "usb", "felica_nfc",
            }.issubset(found))
            self.assertNotIn("subghz_txrx", found)
            self.assertNotIn("lf_rfid", found)
            self.assertNotIn("ibutton", found)
            for m in data["modules"]:
                self.assertNotEqual(m["read_only_node_status"], "PASS")
                self.assertNotEqual(m["read_only_node_status"], "HARDWARE_READY")

    def test_candidate_ids_are_manifest_ids(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ids = {m["id"] for m in data["modules"]}
        self.assertTrue(set(CANDIDATES).issubset(ids))


if __name__ == "__main__":
    unittest.main(verbosity=2)
