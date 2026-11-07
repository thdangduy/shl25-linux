// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 CLMR PM8941 supply sequencing (C7, unwired).
 *
 * Provenance: Sharp GPL bld010105 shdisp_lcdc/shdisp_clmr.c,
 * sharp-shdisp-clmr.dtsi; no generic regulator shortcuts.
 *
 * This code has no probe/initcall/incoming caller. The actual PM8941
 * supplies and GPIO must be resolved and validated by future board code
 * before these entry points may be used. CLMR and DSI DT remain disabled.
 */
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/gpio/consumer.h>
#include <linux/regulator/consumer.h>

#include "shl25-as99-clmr-power.h"

#define SHL25_CLMR_LP_UV 1200000
#define SHL25_CLMR_LP_LOAD_UA 100000

static int shl25_clmr_power_gate(
	const struct shl25_clmr_power_resources *res,
	const struct shl25_clmr_power_prereqs *ready)
{
	if (!res || !ready)
		return -EINVAL;
	if (!ready->oem_supply_mapping_verified ||
	    !ready->core_gpio_active_high_verified ||
	    !ready->as99_board_revision_verified ||
	    !ready->pm8941_parent_rails_verified)
		return -EOPNOTSUPP;
	if (!res->vdd_18tx || !res->vdd_12lp || !res->core_switch)
		return -EINVAL;
	return 0;
}

int shl25_as99_clmr_power_enable(
	struct shl25_clmr_power_resources *res,
	const struct shl25_clmr_power_prereqs *ready)
{
	int ret;

	ret = shl25_clmr_power_gate(res, ready);
	if (ret)
		return ret;
	if (res->power_on)
		return -EALREADY;

	/* OEM shdisp_clmr_config_reg() configures L2 1.2V + load
	 * before enable. Do not silently ignore a regulator failure.
	 */
	ret = regulator_set_voltage(res->vdd_12lp,
				    SHL25_CLMR_LP_UV, SHL25_CLMR_LP_UV);
	if (ret)
		return ret;
	ret = regulator_set_load(res->vdd_12lp, SHL25_CLMR_LP_LOAD_UA);
	if (ret)
		return ret;

	/* CLMR VDD PMIC GPIO19 must be held LOW until BOTH rails
	 * are independently stable. A future board adapter must supply
	 * an active-high descriptor, not an unverified raw GPIO number.
	 */
	ret = gpiod_direction_output(res->core_switch, 0);
	if (ret)
		return ret;

	ret = regulator_enable(res->vdd_18tx); /* OEM first, LVS2 */
	if (ret)
		return ret;
	usleep_range(1000, 1100);

	ret = regulator_enable(res->vdd_12lp); /* OEM second, L2 */
	if (ret)
		goto disable_first;
	usleep_range(1000, 1100);

	gpiod_set_value_cansleep(res->core_switch, 1);
	res->power_on = true;
	return 0;

disable_first:
	regulator_disable(res->vdd_18tx);
	return ret;
}

int shl25_as99_clmr_power_disable(
	struct shl25_clmr_power_resources *res,
	const struct shl25_clmr_power_prereqs *ready)
{
	int ret, err;

	ret = shl25_clmr_power_gate(res, ready);
	if (ret)
		return ret;
	if (!res->power_on)
		return -EALREADY;

	/* OEM reverse order, VDD core switch low first. */
	gpiod_set_value_cansleep(res->core_switch, 0);
	ret = regulator_disable(res->vdd_12lp);
	err = regulator_disable(res->vdd_18tx);
	if (!ret)
		ret = err;
	if (!ret)
		res->power_on = false;
	return ret;
}
