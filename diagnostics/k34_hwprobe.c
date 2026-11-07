/*
 * SHL25/AS99 kernel 3.4 hardware probe (read-only).
 *
 * Reads legacy framebuffer/ioctl and input event metadata without drawing,
 * grabbing devices, writing nodes, changing display state or flashing.
 * Intended to run from TWRP with existing root ADB shell.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int framebuffer(const char *path)
{
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("FB_OPEN_FAIL %s errno=%d\n", path, errno);
        return 0;
    }
    if (ioctl(fd, FBIOGET_VSCREENINFO, &v) < 0 ||
        ioctl(fd, FBIOGET_FSCREENINFO, &f) < 0) {
        printf("FB_IOCTL_FAIL %s errno=%d\n", path, errno);
        close(fd);
        return 0;
    }
    printf("FB_OK %s name=%.*s xres=%u yres=%u xvirt=%u yvirt=%u bpp=%u stride=%u size=%u "
           "rgba=%u:%u,%u:%u,%u:%u,%u:%u rotate=%u\n",
           path, (int)sizeof(f.id), f.id, v.xres, v.yres,
           v.xres_virtual, v.yres_virtual, v.bits_per_pixel,
           f.line_length, f.smem_len,
           v.red.offset, v.red.length, v.green.offset, v.green.length,
           v.blue.offset, v.blue.length, v.transp.offset, v.transp.length,
           v.rotate);
    close(fd);
    return 1;
}

static void print_abs(int fd, const char *label, unsigned int code)
{
    struct input_absinfo a;
    if (ioctl(fd, EVIOCGABS(code), &a) == 0)
        printf("INPUT_AXIS %s min=%d max=%d fuzz=%d flat=%d resolution=%d\n",
               label, a.minimum, a.maximum, a.fuzz, a.flat, a.resolution);
}

static int input_device(const char *path, const char *required_name)
{
    char name[128];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("INPUT_OPEN_FAIL %s errno=%d\n", path, errno);
        return 0;
    }
    memset(name, 0, sizeof(name));
    if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) < 0) {
        printf("INPUT_NAME_FAIL %s errno=%d\n", path, errno);
        close(fd);
        return 0;
    }
    printf("INPUT_OK %s name=%s\n", path, name);
    print_abs(fd, "ABS_X", ABS_X);
    print_abs(fd, "ABS_Y", ABS_Y);
    print_abs(fd, "ABS_MT_POSITION_X", ABS_MT_POSITION_X);
    print_abs(fd, "ABS_MT_POSITION_Y", ABS_MT_POSITION_Y);
    print_abs(fd, "ABS_MT_TRACKING_ID", ABS_MT_TRACKING_ID);
    close(fd);
    return required_name != NULL && strstr(name, required_name) != NULL;
}

int main(void)
{
    int fb0 = framebuffer("/dev/graphics/fb0");
    (void)framebuffer("/dev/graphics/fb1");
    int touch = 0;
    static const char *inputs[] = {
        "/dev/input/event0", "/dev/input/event1", "/dev/input/event2",
        "/dev/input/event3", "/dev/input/event4"
    };
    for (unsigned i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i)
        touch |= input_device(inputs[i], "shtps_rmi");
    printf("SHL25_K34_HWPROBE_RESULT fb0=%s touch=%s\n",
           fb0 ? "PASS" : "NOT_PROVEN", touch ? "PASS" : "NOT_PROVEN");
    /* Read-only. Never writes to /dev/graphics, /dev/input or any partition. */
    return fb0 && touch ? 0 : 2;
}
