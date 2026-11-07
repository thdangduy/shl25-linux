// SPDX-License-Identifier: GPL-2.0-only
/*
 * Sharp SHL25 / AS99 1080x1920 CMD-mode Andy panel, Linux 6.1 DRM port.
 *
 * Derived by translating the DSI command records in Sharp's released
 * bld010105/sharp-shdisp-dsi-panel-andy-1080p-cmd.dtsi into generic
 * MIPI DSI operations; see upstream/verify_shl25_andy_panel.py.
 *
 * SAFETY: This driver only sends panel DSI commands. It does NOT yet
 * control the Sharp CLMR/BDIC, reset GPIO, PM8941 supplies, TE wiring,
 * or other board power/clock sequencing. The matching AS99 DTS node
 * remains disabled until these dependencies are implemented and proved.
 * Compiling this driver alone is NOT hardware success.
 */
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/slab.h>
#include <video/mipi_display.h>
#include <drm/drm_connector.h>
#include <drm/drm_device.h>
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_panel.h>
#include <drm/drm_modes.h>

struct shl25_andy {
	struct drm_panel panel;
	struct mipi_dsi_device *dsi;
	bool prepared;
	bool enabled;
};

struct shl25_andy_cmd {
	u8 packet_type;
	u8 delay_ms;
	u8 length;
	u8 payload[16];
};

/* OEM_INIT_SHA256=521f981db5686f8d11ff3b04404f29f0473b1b83bc4cd5c2ad56063535b2e499 */
/* OEM_INIT_ARRAY_BEGIN */
static const struct shl25_andy_cmd shl25_andy_on[] = {
	{ 0x23, 10, 2, { 0xb0, 0x00 } },
	{ 0x23, 10, 2, { 0xb2, 0x00 } },
	{ 0x23, 10, 2, { 0xb3, 0x0c } },
	{ 0x23, 10, 2, { 0xb4, 0x02 } },
	{ 0x29, 0, 6, { 0xc0, 0x40, 0x02, 0x7f, 0xc8, 0x08 } },
	{ 0x29, 0, 16, { 0xc1, 0x00, 0xa8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x9d, 0x08, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00 } },
	{ 0x29, 0, 6, { 0xc2, 0x00, 0x00, 0x09, 0x00, 0x00 } },
	{ 0x23, 10, 2, { 0xc3, 0x04 } },
	{ 0x29, 0, 4, { 0xc4, 0x4d, 0x83, 0x00 } },
	{ 0x29, 0, 11, { 0xc6, 0x12, 0x00, 0x08, 0x71, 0x00, 0x00, 0x00, 0x80, 0x00, 0x04 } },
	{ 0x23, 10, 2, { 0xc7, 0x22 } },
	{ 0x29, 0, 5, { 0xc8, 0x4c, 0x0c, 0x0c, 0x0c } },
	{ 0x29, 0, 14, { 0xc9, 0x00, 0x40, 0x00, 0x16, 0x32, 0x2e, 0x3a, 0x43, 0x3e, 0x3c, 0x45, 0x79, 0x3f } },
	{ 0x29, 0, 14, { 0xca, 0x00, 0x46, 0x1a, 0x23, 0x21, 0x1c, 0x25, 0x31, 0x2d, 0x49, 0x5f, 0x7f, 0x3f } },
	{ 0x29, 0, 14, { 0xcb, 0x00, 0x4c, 0x20, 0x3a, 0x42, 0x40, 0x47, 0x4b, 0x42, 0x3e, 0x46, 0x7e, 0x3f } },
	{ 0x29, 0, 14, { 0xcc, 0x00, 0x41, 0x19, 0x21, 0x1d, 0x14, 0x18, 0x1f, 0x1d, 0x25, 0x3f, 0x73, 0x3f } },
	{ 0x29, 0, 14, { 0xcd, 0x23, 0x79, 0x5a, 0x5f, 0x57, 0x4c, 0x51, 0x51, 0x45, 0x3f, 0x4b, 0x7f, 0x3f } },
	{ 0x29, 0, 14, { 0xce, 0x00, 0x40, 0x14, 0x20, 0x1a, 0x0e, 0x0e, 0x13, 0x08, 0x00, 0x05, 0x46, 0x1c } },
	{ 0x29, 0, 4, { 0xd0, 0x6a, 0x64, 0x01 } },
	{ 0x29, 0, 3, { 0xd1, 0x77, 0xd4 } },
	{ 0x23, 10, 2, { 0xd3, 0x33 } },
	{ 0x29, 0, 3, { 0xd5, 0x0f, 0x0f } },
	{ 0x29, 0, 7, { 0xd8, 0x34, 0x64, 0x23, 0x25, 0x62, 0x32 } },
	{ 0x29, 0, 12, { 0xde, 0x10, 0x7b, 0x11, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 } },
	{ 0x29, 0, 9, { 0xfd, 0x04, 0x55, 0x53, 0x00, 0x70, 0xff, 0x10, 0x73 } },
	{ 0x23, 10, 2, { 0xe2, 0x00 } },
	{ 0x05, 120, 2, { 0x11, 0x00 } },
	{ 0x05, 50, 2, { 0x29, 0x00 } },
};
/* OEM_INIT_ARRAY_END */

/* OEM_OFF_SHA256=c09f10cbd7e0150e77fab2922392201b033ffd19ea8c9afa596d65630aacdf10 */
/* OEM_OFF_ARRAY_BEGIN */
static const struct shl25_andy_cmd shl25_andy_off[] = {
	{ 0x05, 50, 2, { 0x28, 0x00 } },
	{ 0x05, 120, 2, { 0x10, 0x00 } },
};
/* OEM_OFF_ARRAY_END */

static inline struct shl25_andy *to_shl25_andy(struct drm_panel *panel)
{
	return container_of(panel, struct shl25_andy, panel);
}

static int shl25_andy_send(struct shl25_andy *ctx,
			   const struct shl25_andy_cmd *cmd)
{
	struct mipi_dsi_device *dsi = ctx->dsi;
	ssize_t ret;
	u8 dcs;

	switch (cmd->packet_type) {
	case 0x23: /* vendor generic short write with two parameters */
		if (cmd->length != 2)
			return -EINVAL;
		ret = mipi_dsi_generic_write(dsi, cmd->payload, 2);
		if (ret >= 0 && ret != 2)
			return -EIO;
		break;
	case 0x29: /* vendor generic long write */
		if (cmd->length < 3)
			return -EINVAL;
		ret = mipi_dsi_generic_write(dsi, cmd->payload,
					     cmd->length);
		if (ret >= 0 && ret != cmd->length)
			return -EIO;
		break;
	case 0x05: /* DCS short no-param command with OEM padding byte */
		if (cmd->length != 2 || cmd->payload[1] != 0)
			return -EINVAL;
		dcs = cmd->payload[0];
		ret = mipi_dsi_dcs_write_buffer(dsi, &dcs, 1);
		if (ret >= 0 && ret != 1)
			return -EIO;
		break;
	default:
		return -EOPNOTSUPP;
	}

	if (ret < 0)
		return (int)ret;

	if (cmd->delay_ms)
		msleep(cmd->delay_ms);

	return 0;
}

static int shl25_andy_run(struct shl25_andy *ctx,
			   const struct shl25_andy_cmd *cmds, size_t count)
{
	size_t i;
	int ret;

	for (i = 0; i < count; i++) {
		ret = shl25_andy_send(ctx, &cmds[i]);
		if (ret) {
			dev_err(&ctx->dsi->dev,
				"Sharp Andy DSI command %zu type 0x%02x failed: %d\n",
				i, cmds[i].packet_type, ret);
			return ret;
		}
	}
	return 0;
}

static int shl25_andy_prepare(struct drm_panel *panel)
{
	struct shl25_andy *ctx = to_shl25_andy(panel);
	int ret;

	if (ctx->prepared)
		return 0;

	ctx->dsi->mode_flags |= MIPI_DSI_MODE_LPM;
	ret = shl25_andy_run(ctx, shl25_andy_on,
			      ARRAY_SIZE(shl25_andy_on));
	if (ret)
		return ret;

	ctx->prepared = true;
	return 0;
}

static int shl25_andy_unprepare(struct drm_panel *panel)
{
	struct shl25_andy *ctx = to_shl25_andy(panel);
	int ret;

	if (!ctx->prepared)
		return 0;

	/* OEM off command state: high-speed mode. */
	ctx->dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
	ret = shl25_andy_run(ctx, shl25_andy_off,
			      ARRAY_SIZE(shl25_andy_off));
	if (!ret)
		ctx->prepared = false;
	return ret;
}

static int shl25_andy_enable(struct drm_panel *panel)
{
	to_shl25_andy(panel)->enabled = true;
	return 0;
}

static int shl25_andy_disable(struct drm_panel *panel)
{
	to_shl25_andy(panel)->enabled = false;
	return 0;
}

/*
 * Vendor DSI0 timing:
 * 1080x1920 @ 60 Hz, horizontal FP=120, SYNC=20, BP=12;
 * vertical FP=18, SYNC=7, BP=4. Pixel clock = 144070.08 kHz.
 * The panel is command mode; do not set MIPI_DSI_MODE_VIDEO.
 */
static const struct drm_display_mode shl25_andy_mode = {
	.clock = 144070,
	.hdisplay = 1080,
	.hsync_start = 1080 + 120,
	.hsync_end = 1080 + 120 + 20,
	.htotal = 1080 + 120 + 20 + 12,
	.vdisplay = 1920,
	.vsync_start = 1920 + 18,
	.vsync_end = 1920 + 18 + 7,
	.vtotal = 1920 + 18 + 7 + 4,
};

static int shl25_andy_get_modes(struct drm_panel *panel,
				 struct drm_connector *connector)
{
	struct drm_display_mode *mode;

	mode = drm_mode_duplicate(connector->dev, &shl25_andy_mode);
	if (!mode)
		return -ENOMEM;
	mode->type |= DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
	drm_mode_set_name(mode);
	drm_mode_probed_add(connector, mode);
	connector->display_info.width_mm = 64;
	connector->display_info.height_mm = 114;
	return 1;
}

static const struct drm_panel_funcs shl25_andy_panel_funcs = {
	.prepare = shl25_andy_prepare,
	.unprepare = shl25_andy_unprepare,
	.enable = shl25_andy_enable,
	.disable = shl25_andy_disable,
	.get_modes = shl25_andy_get_modes,
};

static int shl25_andy_probe(struct mipi_dsi_device *dsi)
{
	struct shl25_andy *ctx;
	int ret;

	ctx = devm_kzalloc(&dsi->dev, sizeof(*ctx), GFP_KERNEL);
	if (!ctx)
		return -ENOMEM;

	ctx->dsi = dsi;
	dsi->lanes = 4;
	dsi->format = MIPI_DSI_FMT_RGB888;
	dsi->mode_flags = MIPI_DSI_MODE_LPM; /* CMD mode + low-power init */
	mipi_dsi_set_drvdata(dsi, ctx);

	drm_panel_init(&ctx->panel, &dsi->dev, &shl25_andy_panel_funcs,
		       DRM_MODE_CONNECTOR_DSI);
	ret = drm_panel_of_backlight(&ctx->panel);
	if (ret)
		return ret;
	drm_panel_add(&ctx->panel);

	ret = mipi_dsi_attach(dsi);
	if (ret) {
		drm_panel_remove(&ctx->panel);
		return ret;
	}
	return 0;
}

static void shl25_andy_remove(struct mipi_dsi_device *dsi)
{
	struct shl25_andy *ctx = mipi_dsi_get_drvdata(dsi);
	int ret;

	ret = drm_panel_disable(&ctx->panel);
	if (ret)
		dev_warn(&dsi->dev, "disable failed: %d\n", ret);
	ret = drm_panel_unprepare(&ctx->panel);
	if (ret)
		dev_warn(&dsi->dev, "unprepare failed: %d\n", ret);
	ret = mipi_dsi_detach(dsi);
	if (ret)
		dev_warn(&dsi->dev, "detach failed: %d\n", ret);
	drm_panel_remove(&ctx->panel);
}

static const struct of_device_id shl25_andy_of_match[] = {
	{ .compatible = "sharp,shl25-andy" },
	{ }
};
MODULE_DEVICE_TABLE(of, shl25_andy_of_match);

static struct mipi_dsi_driver shl25_andy_driver = {
	.probe = shl25_andy_probe,
	.remove = shl25_andy_remove,
	.driver = {
		.name = "panel-sharp-shl25-andy",
		.of_match_table = shl25_andy_of_match,
	},
};
module_mipi_dsi_driver(shl25_andy_driver);

MODULE_DESCRIPTION("Sharp AS99 / SHL25 Andy 1080p command-mode DSI panel");
MODULE_LICENSE("GPL");
