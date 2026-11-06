# SHL25 hardware bring-up evidence (mainline Linux v6.16)

## Verified references

Source of device-specific facts: Sharp's released GPL Linux 3.4 DTS in local SHL25 Lab, not Sony hardware assumptions. This is a migration record; **it does not establish mainline hardware boot**.

| Component | Sharp GPL evidence | Upstream v6.16 SHL25 DTS |
| --- | --- | --- |
| Qualcomm SoC | SHL25/AS99, MSM8974Pro AB, QCDT board-id 50 | `qcom,sharp-as99`, `qcom,msm8974pro`, `qcom,msm8974`; board-id 50 |
| eMMC SDHC1 | `sharp-common-sdcc.dtsi`: VDD PM8941 L20 at 2,950,000 uV, VDD IO PM8941 S3 at 1,800,000 uV | `&sdhc_1` vmmc=L20, vqmmc=S3; `non-removable` |
| eMMC pad strength | `sharp-as99-sdcc.dtsi`: CLK 12mA, CMD/DATA 10mA | `as99_sdc1_default` pinctrl |
| PM8941 S1 | `sharp-common-pm8941.dtsi`: 1,300,000 uV always-on | S1 at 1,300,000 uV, always-on |
| PM8941 S2 | Same: 2,150,000 uV always-on | S2 at 2,150,000 uV, always-on |
| PM8941 S3 | Same: 1,800,000 uV always-on | S3 at 1,800,000 uV, always-on |
| PM8941 L6 | Same: 1,800,000 uV always-on | L6 at 1,800,000 uV, always-on |
| PM8941 L20 | Same: 2,950,000 uV always-on | L20 at 2,950,000 uV, always-on |
| PM8941 L24 | Same: 3,075,000 uV, not always-on | L24 at 3,075,000 uV, boot-on for USB bring-up; needs verification |
| Display | `sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi`: Sharp 1080×1920 DSI command-mode, complex Sharp init commands | Intentionally not enabled; panel/CLMR/IR2E71Y6 driver port not complete |

## Important unverified boundaries

- Original Sharp 3.4 QCDT FDT has ~913 nodes; draft mainline v6.16 DTB has ~423 nodes. These quantities are **not** direct evidence of a defect; binding structures differ.
- Mainline SoC DTS defines a memory node whose `reg` is initially empty. A bootloader memory fixup may be expected; **do not insert RAM mappings guessed from TWRP /proc/iomem** until bootloader protocol and protected regions have been checked.
- PM8841 voltage and SPMI mappings, SMEM/TZ memory, USB PHY rails and system clocks need deeper board-by-board confirmation.
- Mainline build proves kernel and DT compile; not proof that Sharp bootloader passes compatible DT or that regulators/eMMC enumerate.
- `CONFIG_PSTORE` is disabled; a ramoops region MUST NOT be fabricated from random free RAM. Early diagnostic /init must first prove kernel, MMC and ext4.
- Stock TWRP Recovery is separate from BOOT, and must not be overwritten.
- Source upstream stays pinned to commit `038d61fd642278bab63ee8ef722c50d10ab01e8f`; the Sharp board DTS and any driver patches belong to this repository, not a third-party fork.
