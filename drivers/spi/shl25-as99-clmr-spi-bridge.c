// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 AS99 CLMR SPI ROM/firmware transport adapter (C6).
 *
 * OEM: bld010105 drivers/sharp/shdisp_lcdc/shdisp_system.c
 * SHA256 985c833167b4ae4863dddfaad805ded68e94195b60496f6472d2a9b90165f21f
 *
 * Compiled code only. No probe/initcall/DT enablement or direct caller.
 * Board supply/reset/PLL/IRQ must be source- and hardware-verified
 * before calling this adapter. This file never controls regulators.
 */
#include <linux/errno.h>
#include <linux/firmware.h>
#include <linux/kernel.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#include <linux/spi/spi.h>
#include <asm/unaligned.h>

#include "shl25-as99-clmr-boot.h"
#include "shl25-as99-clmr-spi-bridge.h"

#define SHL25_CLMR_FIRMWARE_NAME "sharp/shl25-as99-clmr.bin"
#define SHL25_CLMR_SPI_WRITE_HZ 50000000U
#define SHL25_CLMR_SPI_READ_HZ  20000000U
#define SHL25_CLMR_SPI_FRAME_MAX 6144U
#define SHL25_CLMR_SPI_FRAME_OVERHEAD 4U
#define SHL25_CLMR_SPI_FW_PAYLOAD 6128U
#define SHL25_CLMR_SPI_FW_BLOCK 16U

#define SHL25_CLMR_REG_DEVCODE 0x0300
#define SHL25_CLMR_DEVCODE_EXPECTED 0x00004002U
#define SHL25_CLMR_OP_REG_WRITE 0xc0
#define SHL25_CLMR_OP_REG_SELECT 0xc2
#define SHL25_CLMR_OP_REG_FETCH 0xc4
#define SHL25_CLMR_OP_FW_BEGIN 0xc7
#define SHL25_CLMR_OP_FW_CONT 0xc8

struct shl25_clmr_bridge {
	struct spi_device *spi;
	struct mutex lock;
	const struct shl25_clmr_board_irq_ops *irq_ops;
	void *irq_ctx;
	/* Only enabled inside checked bridge_boot(), never from probe. */
	bool rom_io_authorized;
};

static int shl25_clmr_bridge_write(void *ctx, u16 reg, u32 value)
{
	struct shl25_clmr_bridge *bridge = ctx;
	struct spi_transfer transfer = { };
	u8 frame[7];
	int ret;

	if (!bridge->rom_io_authorized)
		return -EOPNOTSUPP;

	/* OEM shdisp_clmr_regSet() applies htonl before copying raw bytes.
	 * Thus C0 + address BE16 + register value BE32 on the wire.
	 */
	frame[0] = SHL25_CLMR_OP_REG_WRITE;
	put_unaligned_be16(reg, frame + 1);
	put_unaligned_be32(value, frame + 3);

	transfer.tx_buf = frame;
	transfer.len = sizeof(frame);
	transfer.bits_per_word = 8;
	transfer.speed_hz = SHL25_CLMR_SPI_WRITE_HZ;

	mutex_lock(&bridge->lock);
	ret = spi_sync_transfer(bridge->spi, &transfer, 1);
	mutex_unlock(&bridge->lock);
	return ret;
}

static int shl25_clmr_bridge_read(void *ctx, u16 reg, u32 *value)
{
	struct shl25_clmr_bridge *bridge = ctx;
	struct spi_transfer transfer = { };
	u8 select[3] = { SHL25_CLMR_OP_REG_SELECT };
	u8 fetch[5] = { SHL25_CLMR_OP_REG_FETCH, 0, 0, 0, 0 };
	u8 reply[5] = { };
	int ret;

	if (!value)
		return -EINVAL;
	if (!bridge->rom_io_authorized)
		return -EOPNOTSUPP;

	put_unaligned_be16(reg, select + 1);
	transfer.tx_buf = select;
	transfer.len = sizeof(select);
	transfer.bits_per_word = 8;
	transfer.speed_hz = SHL25_CLMR_SPI_READ_HZ;
	transfer.cs_change = 1;

	mutex_lock(&bridge->lock);
	/* Preserve two distinct OEM spi_sync() messages. */
	ret = spi_sync_transfer(bridge->spi, &transfer, 1);
	if (ret)
		goto out;

	transfer.tx_buf = fetch;
	transfer.rx_buf = reply;
	transfer.len = sizeof(fetch);
	transfer.cs_change = 1;
	ret = spi_sync_transfer(bridge->spi, &transfer, 1);
	if (!ret)
		*value = get_unaligned_be32(reply + 1);
out:
	mutex_unlock(&bridge->lock);
	return ret;
}

/* OEM shdisp_clmr_lcdc_devcheck() compares DEVCODE 0x00004002.
 * Reject wrong hardware identity before the first register write.
 */
static int shl25_clmr_bridge_validate_device(void *ctx)
{
	u32 devcode;
	int ret;

	ret = shl25_clmr_bridge_read(ctx, SHL25_CLMR_REG_DEVCODE,
				     &devcode);
	if (ret)
		return ret;
	return devcode == SHL25_CLMR_DEVCODE_EXPECTED ? 0 : -ENODEV;
}

/*
 * OEM eDram_transfer() copies 6128 payload bytes at offset 1 in each
 * 6144-byte frame and transmits 4 + payload length. Its trailing three
 * scratch bytes have no defined content. We zero them deterministically
 * and leave board activation blocked until the protocol is validated.
 */
static int shl25_clmr_bridge_stream(void *ctx, const u8 *fw, size_t bytes)
{
	struct shl25_clmr_bridge *bridge = ctx;
	struct spi_transfer transfer = { };
	u8 *frame;
	size_t start, chunk;
	int ret = 0;

	if (!bridge->rom_io_authorized)
		return -EOPNOTSUPP;
	if (!fw || bytes != 59136U || bytes % SHL25_CLMR_SPI_FW_BLOCK)
		return -EINVAL;
	BUILD_BUG_ON(SHL25_CLMR_SPI_FW_PAYLOAD % SHL25_CLMR_SPI_FW_BLOCK);
	BUILD_BUG_ON(SHL25_CLMR_SPI_FW_PAYLOAD +
		     SHL25_CLMR_SPI_FRAME_OVERHEAD > SHL25_CLMR_SPI_FRAME_MAX);

	frame = kmalloc(SHL25_CLMR_SPI_FRAME_MAX, GFP_KERNEL);
	if (!frame)
		return -ENOMEM;

	transfer.tx_buf = frame;
	transfer.bits_per_word = 8;
	transfer.speed_hz = SHL25_CLMR_SPI_WRITE_HZ;
	mutex_lock(&bridge->lock);
	for (start = 0; start < bytes; start += chunk) {
		chunk = min_t(size_t, SHL25_CLMR_SPI_FW_PAYLOAD,
			      bytes - start);
		memset(frame, 0, chunk + SHL25_CLMR_SPI_FRAME_OVERHEAD);
		frame[0] = start ? SHL25_CLMR_OP_FW_CONT :
			SHL25_CLMR_OP_FW_BEGIN;
		memcpy(frame + 1, fw + start, chunk);
		transfer.len = chunk + SHL25_CLMR_SPI_FRAME_OVERHEAD;
		ret = spi_sync_transfer(bridge->spi, &transfer, 1);
		if (ret)
			break;
	}
	mutex_unlock(&bridge->lock);
	kfree(frame);
	return ret;
}

static int shl25_clmr_bridge_arm_boot_irq(void *ctx)
{
	struct shl25_clmr_bridge *bridge = ctx;

	if (!bridge->rom_io_authorized ||
	    !bridge->irq_ops || !bridge->irq_ops->arm_boot_completion)
		return -EOPNOTSUPP;
	return bridge->irq_ops->arm_boot_completion(bridge->irq_ctx);
}

static int shl25_clmr_bridge_wait_boot_irq(void *ctx,
					   unsigned int timeout_ms)
{
	struct shl25_clmr_bridge *bridge = ctx;

	if (!bridge->rom_io_authorized ||
	    !bridge->irq_ops || !bridge->irq_ops->wait_boot_completion)
		return -EOPNOTSUPP;
	return bridge->irq_ops->wait_boot_completion(bridge->irq_ctx,
						    timeout_ms);
}

/*
 * Entry point for a FUTURE verified board driver. It is not called
 * from any registered device, initcall or boot path in Stage C6.
 * request_firmware() does not embed or ship proprietary OEM bytes.
 */
int shl25_as99_clmr_bridge_boot(
	struct spi_device *spi,
	const struct shl25_clmr_boot_prereqs *prereqs,
	const struct shl25_clmr_board_irq_ops *irq_ops, void *irq_ctx)
{
	const struct shl25_clmr_boot_ops ops = {
		.validate_device = shl25_clmr_bridge_validate_device,
		.write_reg = shl25_clmr_bridge_write,
		.read_reg = shl25_clmr_bridge_read,
		.stream_firmware = shl25_clmr_bridge_stream,
		.arm_boot_completion = shl25_clmr_bridge_arm_boot_irq,
		.wait_boot_completion = shl25_clmr_bridge_wait_boot_irq,
	};
	struct shl25_clmr_boot_prereqs ready;
	struct shl25_clmr_bridge bridge = { };
	const struct firmware *firmware;
	int ret;

	if (!spi || !prereqs || !irq_ops || !irq_ctx)
		return -EINVAL;
	if (!irq_ops->arm_boot_completion ||
	    !irq_ops->wait_boot_completion)
		return -EOPNOTSUPP;
	if (!prereqs->pmic_rails_verified ||
	    !prereqs->clmr_reset_verified ||
	    !prereqs->spi_bus_verified ||
	    !prereqs->clock_pll_verified ||
	    !prereqs->boot_irq_verified ||
	    prereqs->det_mode == SHL25_CLMR_DET_UNVERIFIED)
		return -EOPNOTSUPP;
	/* Sharp AS99 DTS pins mode 3 and active-high CS; do not alter
	 * mode during the boot sequence or synthesize unknown pinctrl.
	 */
	if ((spi->mode & (SPI_CPOL | SPI_CPHA | SPI_CS_HIGH)) !=
	    (SPI_CPOL | SPI_CPHA | SPI_CS_HIGH))
		return -EINVAL;
	if (spi->chip_select != 0)
		return -EINVAL;

	ret = request_firmware(&firmware, SHL25_CLMR_FIRMWARE_NAME,
			       &spi->dev);
	if (ret)
		return ret;
	/* The C3 executor checks the actual 59136 bytes against the
	 * pinned SHA-256 before invoking *any* callback / SPI transfer.
	 */
	if (firmware->size != 59136U) {
		ret = -EINVAL;
		goto release;
	}

	bridge.spi = spi;
	bridge.irq_ops = irq_ops;
	bridge.irq_ctx = irq_ctx;
	mutex_init(&bridge.lock);
	bridge.rom_io_authorized = true;
	ready = *prereqs;
	/* This flag allows entry into C3, but cannot bypass its mandatory
	 * in-kernel sha256 digest check (returns -EKEYREJECTED).
	 */
	ready.firmware_sha_verified = true;
	ret = shl25_as99_clmr_boot_sequence(&ops, &bridge, &ready,
					  firmware->data, firmware->size);
	bridge.rom_io_authorized = false;
release:
	release_firmware(firmware);
	return ret;
}
