/* SPDX-License-Identifier: GPL-2.0-only */
/* Generated from pinned Sharp GPL SHL25 AS99 CLMR boot tables. */
/* Do not use before hardware power/reset/clock and firmware validation. */
#ifndef SHL25_AS99_CLMR_BOOT_TABLES_H
#define SHL25_AS99_CLMR_BOOT_TABLES_H
#define SHL25_CLMR_FW_BYTES 59136U
#define SHL25_CLMR_FW_BLOCKS 3696U
#define SHL25_CLMR_HOSTAEY_BOOT_VALUE 3695U
#define SHL25_CLMR_BOOT_IRQ_TIMEOUT_MS 2100U
#define SHL25_CLMR_DMA_POLL_LIMIT 100U
#define SHL25_CLMR_OP_STR 0U
#define SHL25_CLMR_OP_OR 1U
struct shl25_clmr_regop {
	u16 reg;
	u8 op;
	u32 data;
};
static const struct shl25_clmr_regop shl25_boot_fw_download[] = {
	{ 0x0e00, 0, 0x00000012 }, /* SHDISP_CLMR_REG_HOSTSYS */
	{ 0x0e04, 0, 0x00000000 }, /* SHDISP_CLMR_REG_HOSTCTL */
	{ 0x0e1c, 0, 0x00007ce0 }, /* SHDISP_CLMR_REG_HOSTBASE */
	{ 0x0e18, 0, 0x00000001 }, /* SHDISP_CLMR_REG_HOSTHW */
	{ 0x0e08, 0, 0x00000000 }, /* SHDISP_CLMR_REG_HOSTASX */
	{ 0x0e10, 0, 0x00000000 }, /* SHDISP_CLMR_REG_HOSTASY */
	{ 0x0e0c, 0, 0x00000000 }, /* SHDISP_CLMR_REG_HOSTAEX */
};
static const struct shl25_clmr_regop shl25_boot_arm_init_det[] = {
	{ 0x0104, 1, 0x00030000 }, /* SHDISP_CLMR_REG_INTM */
	{ 0x1880, 0, 0x00000000 }, /* SHDISP_CLMR_REG_ARMSRAMCTL */
	{ 0x1804, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMDEBEN */
	{ 0x1800, 0, 0x00000003 }, /* SHDISP_CLMR_REG_ARMHOSTSYS */
	{ 0x1808, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMCONTCLKEN */
	{ 0x1810, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMSLPCLKEN */
};
static const struct shl25_clmr_regop shl25_boot_arm_init_no_det[] = {
	{ 0x0104, 1, 0x00010000 }, /* SHDISP_CLMR_REG_INTM */
	{ 0x1880, 0, 0x00000000 }, /* SHDISP_CLMR_REG_ARMSRAMCTL */
	{ 0x1804, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMDEBEN */
	{ 0x1800, 0, 0x00000003 }, /* SHDISP_CLMR_REG_ARMHOSTSYS */
	{ 0x1808, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMCONTCLKEN */
	{ 0x1810, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMSLPCLKEN */
};
static const struct shl25_clmr_regop shl25_boot_arm_sram2fw[] = {
	{ 0x1824, 0, 0x00000010 }, /* SHDISP_CLMR_REG_ARMDMA */
	{ 0x1838, 0, 0x00000001 }, /* SHDISP_CLMR_REG_ARMDMAHW */
	{ 0x1828, 0, 0x00000000 }, /* SHDISP_CLMR_REG_ARMSRAMBASE */
	{ 0x182c, 0, 0x00007ce0 }, /* SHDISP_CLMR_REG_ARMEDRAMBASE */
	{ 0x1830, 0, 0x00000000 }, /* SHDISP_CLMR_REG_ARMEDRAMSTART */
	{ 0x1834, 0, 0x00000080 }, /* SHDISP_CLMR_REG_ARMDMASIZE */
	{ 0x1824, 0, 0x00000011 }, /* SHDISP_CLMR_REG_ARMDMA */
};
static const struct shl25_clmr_regop shl25_boot_arm_boot[] = {
	{ 0x1800, 0, 0x00000013 }, /* SHDISP_CLMR_REG_ARMHOSTSYS */
};
#endif /* SHL25_AS99_CLMR_BOOT_TABLES_H */
