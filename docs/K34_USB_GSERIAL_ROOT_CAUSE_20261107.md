# SHL25 / AS99 — Linux 3.4 USB serial reuse failure and source patch

Date: 2026-11-07. Device: Sharp SHL25 (AS99) on Windows S9X0R0.
Project: `thdangduy/shl25-linux` — native Linux/6.1 hardware-first port.

## Evidence observed on real TWRP Linux 3.4.0

The tested Sharp 2016 GPL kernel is `bld010105`, with
`CONFIG_USB_ANDROID_SH_CUST=y` and
`CONFIG_USB_ANDROID_SH_SERIALS=y`.

1. The TWRP baseline is `mtp,adb`, `enable=1`, `unlocked=0`.
2. The Sharp `android.c` `enable_store` suppresses gadget enable when
   `unlocked=0`. Correct documented transition: write `enable=0`,
   configure `f_modem/acm_transports=tty`, `functions=modem,adb`,
   `unlocked=1`, `enable=1`.
3. Corrected v2 script successfully reached `modem,adb` and Windows once
   enumerated `USB Serial Device (COM18)`. The 12-second test ended with
   `CONFIGURED`; script restored `mtp,adb`, `enable=1`,
   `unlocked=0`; ADB returned.
4. Repeated v3 bidirectional attempts remained inconclusive: `ttyGS0` was
   openable on the device but Windows failed to reopen COM18; host-to-device
   `SHL25PING` and response `SHL25PONG` were **NOT demonstrated**.
5. TWRP `dmesg` explains the repeated-bind failure:
   `cannot create duplicate filename .../tty/ttyGS0`, error `-EEXIST`,
   `gserial_setup: no classdev for port 0, err -17`.
   Stack: `tty_register_device` -> `gserial_setup` ->
   `acm_function_bind_config` -> `android_enable`.

The error reproduces while TWRP remains recoverable. No BOOT/Recovery flash.
TWRP Recovery p14 SHA256 remains:
`a8ef5821a0eeef0bbb1f3242a5fb382719e532409da8a0756ed62eb2149a0a52`.

## Source cause and proposed fix

Official Sharp GPL `kernel/drivers/usb/gadget/android.c`:
- `sh_serial_setup` calls `gserial_setup(gadget,2)`; selected MDLM
  and OBEX functions can initialize ttyGS0/1 before ACM is bound.
- `acm_function_bind_config` calls `acm_port_setup`, which calls
  `gserial_setup(gadget,no_acm_tty_ports)` again for `modem`.
- Original `u_serial.c:gserial_setup` unconditionally allocates and
  registers a new TTY driver and nodes; no guard for an existing instance.

Patch: `patches/oem34/0001-sharp-gserial-reuse-existing-ttygs.patch`
adds a `CONFIG_USB_ANDROID_SH_SERIALS`-gated check:
- when a TTY driver already exists and `count <= n_ports`, return success
  and reuse the registered ttyGS device nodes;
- when the request exceeds existing capacity, return `-EBUSY`;
- for first setup, retain original allocation path;
- for non-Sharp builds, retain original behavior.

This is a **candidate** fix, NOT a proven kernel fix. It must be
compiled against original Sharp 3.4, reviewed for serial function lifetime
and possible distinct port-number collisions, and tested on an actual
USB restart/ACM roundtrip before claiming resolution.

## Reproducibility

Original GPL archive:
`C:\Users\Admin\Downloads\SHL25-Linux-Lab\Sharp-OEM-Sources\bld010105\kernel.tar.gz`

Original `u_serial.c` SHA256:
`c335658bb106a1920b0562c37637f50b5de008604890f683a1897fbf8b21285a`.

Run `scripts/prepare_oem34_gserial_reuse_patch.py` with
`--archive`, `--out-patch`, `--out-source`, and `--out-manifest`.
It refuses unknown source hashes.

Local exact-source `git apply --check` and `git apply` passed with
`core.autocrlf=false`; the resulting patched SHA256 was
`0824f4470986ec843ded3da2f117041bf563fbb3a93550bf9b0a57343c1ada0c`.

**Caveat:** successful patch application and byte-for-byte source check
are not kernel compile PASS, USB roundtrip PASS, or live hardware PASS.

## Next gates

1. Build the patched 3.4 kernel with verified ARM EABI cross toolchain,
   preserving Sharp stock config, QCDT and the known-safe recovery path.
2. Validate a fresh-boot USB gadget: ACM endpoint + host COM port
   + PING/PONG roundtrip **twice**. Do not endlessly reconfigure the
   existing TWRP kernel that has already shown TTY reuse corruption.
3. Once USB debug is reliable, boot the standalone Linux 3.4 PID1
   image with a strictly verified BOOT p13 rollback and untouched TWRP p14.
4. Use mapped OEM dependencies to port PMIC, eMMC, USB, Sharp Andy DSI,
   IR2E71Y6/CLMR and SHTPS TM2979_001 to Linux 6.1 incrementally.

No VPS-ARM, no Android/AOSP system deployment, and do not use the
inaccurate TWRP battery percentage as a charge-status verdict.
