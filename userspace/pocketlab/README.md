# SHL25 Pocket Lab (Flipper-style Linux userspace)

This is the initial **read-only** userspace foundation for a
touchscreen-first SHL25 multi-tool. It is a future native Linux 6.1
application, **not** Flipper firmware, an Android app, a
working Qt launcher, or a hardware enablement script.

Architecture and exact Sharp OEM provenance:
`../../upstream/SHL25_POCKET_LAB_FLIPPER_STYLE_PLAN_20261107.md`.

## Files

- `hardware-manifest.json`: audited and explicitly unverified
  hardware/driver capabilities, grouped for the future GUI launcher.
- `probe_readonly.py`: pure Python, standard library only;
  enumerates candidate sysfs/dev paths without touching devices.
- `test_probe_readonly.py`: offline tests with synthetic device
  nodes and capability mapping.

Usage on future Linux rootfs with Python 3:

```bash
python3 probe_readonly.py
python3 probe_readonly.py --module tv_tuner
python3 test_probe_readonly.py
```

Offline fixture root (no device access):

```bash
python3 probe_readonly.py --root /path/to/fake-root
```

`NODE_FOUND_UNVERIFIED` indicates a path exists only, NOT a successful
probe, functional driver or confirmed radio. Full hardware test results
require separate bounded operations and owner consent.

The roadmap keeps kernel/display/CLMR DTS status `disabled` until
board source and safe bringup are proven. No radio TX or credential
emulation is implied by the manifest.
