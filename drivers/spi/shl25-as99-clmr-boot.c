// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 CLMR firmware bootstrap plan (Linux 6.1 Stage C3).
 *
 * Selection is pinned to OEM bld010105 shdisp_lcdc/shdisp_clmr.c,
 * source sha256 399f2b8f050709f6c8c08c56e22260e13ba46b2edde363555ebb69487933e7f0.
 *
 * This object has NO registered device, callback adapter, initcall, probe
 * or exported symbol. The real SPI device and display DT nodes remain
 * disabled. Successful source compilation is NOT a hardware boot.
 */
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/types.h>

#include "shl25-as99-clmr-boot.h"
#include "shl25-as99-clmr-boot-tables.h"

#define SHL25_CLMR_REG_HOSTAEY 0x0e14
#define SHL25_CLMR_REG_ARMDMA  0x1824

static int shl25_clmr_apply_regops(
	const struct shl25_clmr_boot_ops *ops, void *ctx,
	const struct shl25_clmr_regop *entries, size_t count)
{
	size_t i;
	int ret;
	u32 data;

	for (i = 0; i < count; i++) {
		data = entries[i].data;
		if (entries[i].op == SHL25_CLMR_OP_OR) {
			ret = ops->read_reg(ctx, entries[i].reg, &data);
			if (ret)
				return ret;
			data |= entries[i].data;
		} else if (entries[i].op != SHL25_CLMR_OP_STR) {
			return -EOPNOTSUPP;
		}
		ret = ops->write_reg(ctx, entries[i].reg, data);
		if (ret)
			return ret;
	}
	return 0;
}

/*
 * A testable sequence executor, not attached to shl25_clmr_spi_probe().
 * OEM shdisp_clmr_boot_fw: fw_download -> arm_init -> arm_sram2fw
 * -> arm_boot -> wait4fw_boot_comp. All I/O is through injected ops.
 */
int shl25_as99_clmr_boot_sequence(
	const struct shl25_clmr_boot_ops *ops, void *ctx,
	const struct shl25_clmr_boot_prereqs *ready,
	const u8 *firmware, size_t firmware_bytes)
{
	const struct shl25_clmr_regop *arm_init;
	size_t arm_init_count;
	u32 dma_state = 0;
	unsigned int attempt;
	int ret;

	if (!ops || !ctx || !ready || !firmware)
		return -EINVAL;
	if (firmware_bytes != SHL25_CLMR_FW_BYTES)
		return -EINVAL;
	if (!ready->pmic_rails_verified || !ready->clmr_reset_verified ||
	    !ready->spi_bus_verified || !ready->clock_pll_verified ||
	    !ready->firmware_sha_verified || !ready->boot_irq_verified)
		return -EOPNOTSUPP;
	if (ready->det_mode == SHL25_CLMR_DET_ENABLED) {
		arm_init = shl25_boot_arm_init_det;
		arm_init_count = ARRAY_SIZE(shl25_boot_arm_init_det);
	} else if (ready->det_mode == SHL25_CLMR_DET_NOT_SUPPORTED) {
		arm_init = shl25_boot_arm_init_no_det;
		arm_init_count = ARRAY_SIZE(shl25_boot_arm_init_no_det);
	} else {
		return -EOPNOTSUPP;
	}
	if (!ops->write_reg || !ops->read_reg || !ops->stream_firmware ||
	    !ops->arm_boot_completion || !ops->wait_boot_completion)
		return -EOPNOTSUPP;

	/* OEM fw_download[] and then HOSTAEY = htonl(fw_blocks - 1).
	 * Injected write_reg accepts host-order u32 and must serialize
	 * register words into the exact OEM big-endian SPI bytes.
	 */
	ret = shl25_clmr_apply_regops(ops, ctx, shl25_boot_fw_download,
				    ARRAY_SIZE(shl25_boot_fw_download));
	if (ret)
		return ret;
	ret = ops->write_reg(ctx, SHL25_CLMR_REG_HOSTAEY,
			     SHL25_CLMR_HOSTAEY_BOOT_VALUE);
	if (ret)
		return ret;
	ret = ops->stream_firmware(ctx, firmware, firmware_bytes);
	if (ret)
		return ret;

	ret = shl25_clmr_apply_regops(ops, ctx, arm_init, arm_init_count);
	if (ret)
		return ret;
	ret = shl25_clmr_apply_regops(ops, ctx, shl25_boot_arm_sram2fw,
				    ARRAY_SIZE(shl25_boot_arm_sram2fw));
	if (ret)
		return ret;
	/* OEM shdisp_clmr_arm_sram2fw polls ARMDMA bit0 <= 100 times. */
	for (attempt = 0; attempt < SHL25_CLMR_DMA_POLL_LIMIT; attempt++) {
		ret = ops->read_reg(ctx, SHL25_CLMR_REG_ARMDMA, &dma_state);
		if (ret)
			return ret;
		if (!(dma_state & 1U))
			break;
	}
	if (attempt == SHL25_CLMR_DMA_POLL_LIMIT)
		return -ETIMEDOUT;

	/* Original shdisp_clmr_boot_start() arms completion before boot. */
	ret = ops->arm_boot_completion(ctx);
	if (ret)
		return ret;
	ret = shl25_clmr_apply_regops(ops, ctx, shl25_boot_arm_boot,
				    ARRAY_SIZE(shl25_boot_arm_boot));
	if (ret)
		return ret;
	return ops->wait_boot_completion(ctx,
					SHL25_CLMR_BOOT_IRQ_TIMEOUT_MS);
}
