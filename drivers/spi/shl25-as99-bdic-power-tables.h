/* SPDX-License-Identifier: GPL-2.0-only */
/* Sharp OEM AS99 BDIC VSP/VSN register tables, source-pinned. */
/* Not executable until CLMR firmware queue and power gates verified. */
#ifndef SHL25_AS99_BDIC_POWER_TABLES_H
#define SHL25_AS99_BDIC_POWER_TABLES_H
#define SHL25_BDIC_OP_STR 0
#define SHL25_BDIC_OP_SET 1
#define SHL25_BDIC_OP_CLR 2
#define SHL25_BDIC_OP_RMW 3
#define SHL25_BDIC_OP_BANK 4
struct shl25_bdic_regop {
	u8 reg;
	u8 op;
	u8 data;
	u8 mask;
	u32 wait_us;
};
static const struct shl25_bdic_regop shl25_bdic_active[] = {
	{ 0xff, 4, 0x00, 0x00, 0 }, /* BDIC_REG_BANKSEL */
	{ 0x00, 1, 0x80, 0x80, 1000 }, /* BDIC_REG_SYSTEM1 */
	{ 0x02, 1, 0x02, 0x02, 0 }, /* BDIC_REG_SYSTEM3 */
};
static const struct shl25_bdic_regop shl25_bdic_standby[] = {
	{ 0xff, 4, 0x00, 0x00, 0 }, /* BDIC_REG_BANKSEL */
	{ 0x02, 2, 0x00, 0x02, 0 }, /* BDIC_REG_SYSTEM3 */
	{ 0x00, 2, 0x00, 0x80, 0 }, /* BDIC_REG_SYSTEM1 */
};
static const struct shl25_bdic_regop shl25_bdic_vsp_on[] = {
	{ 0xff, 4, 0x00, 0x00, 0 }, /* BDIC_REG_BANKSEL */
	{ 0x57, 0, 0x00, 0xff, 0 }, /* BDIC_REG_DCDC2_TEST_57 */
	{ 0x01, 1, 0x01, 0x01, 3000 }, /* BDIC_REG_SYSTEM2 */
};
static const struct shl25_bdic_regop shl25_bdic_vsp_off[] = {
	{ 0x01, 2, 0x00, 0x01, 0 }, /* BDIC_REG_SYSTEM2 */
	{ 0x57, 0, 0x80, 0xff, 2000 }, /* BDIC_REG_DCDC2_TEST_57 */
};
static const struct shl25_bdic_regop shl25_bdic_vsn_on[] = {
	{ 0x01, 3, 0x10, 0x50, 0 }, /* BDIC_REG_SYSTEM2 */
};
static const struct shl25_bdic_regop shl25_bdic_vsn_on_ts1[] = {
	{ 0x2a, 0, 0x05, 0xff, 0 }, /* BDIC_REG_CPM1 */
	{ 0x01, 2, 0x00, 0x20, 0 }, /* BDIC_REG_SYSTEM2 */
	{ 0x01, 3, 0x10, 0x50, 16000 }, /* BDIC_REG_SYSTEM2 */
	{ 0x01, 1, 0x20, 0x20, 0 }, /* BDIC_REG_SYSTEM2 */
};
static const struct shl25_bdic_regop shl25_bdic_vsn_off[] = {
	{ 0x01, 3, 0x40, 0x50, 1000 }, /* BDIC_REG_SYSTEM2 */
};
#endif /* SHL25_AS99_BDIC_POWER_TABLES_H */
