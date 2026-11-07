/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SHL25_AS99_CLMR_POWER_H
#define SHL25_AS99_CLMR_POWER_H

#include <linux/types.h>

struct gpio_desc;
struct regulator;

/*
 * Resources from the future, board-verified Linux 6.1 regulator/GPIO
 * adapter. NO probe, initcall or DT enable path currently provides them.
 */
struct shl25_clmr_power_resources {
	struct regulator *vdd_18tx; /* PM8941 LVS2, OEM first rail */
	struct regulator *vdd_12lp; /* PM8941 L2, 1200000uV / 100000uA */
	struct gpio_desc *core_switch; /* PM8941 GPIO19, ACTIVE HIGH */
	bool power_on;
};

struct shl25_clmr_power_prereqs {
	bool oem_supply_mapping_verified;
	bool core_gpio_active_high_verified;
	bool as99_board_revision_verified;
	bool pm8941_parent_rails_verified;
};

/* Future caller MUST serialize power transitions. */
int shl25_as99_clmr_power_enable(
	struct shl25_clmr_power_resources *res,
	const struct shl25_clmr_power_prereqs *ready);
int shl25_as99_clmr_power_disable(
	struct shl25_clmr_power_resources *res,
	const struct shl25_clmr_power_prereqs *ready);

#endif
