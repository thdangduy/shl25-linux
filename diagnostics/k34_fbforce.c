/* SPDX-License-Identifier: GPL-2.0-only
 * SHL25 native K34: single, same-mode framebuffer force-kickoff probe.
 *
 * Runs on ARMv7 Linux without libc, Android, external libraries or files.
 * Uses only open(/dev/graphics/fb0), FBIOGET_VSCREENINFO,
 * FBIOPUT_VSCREENINFO with FB_ACTIVATE_FORCE, close, write and exit.
 *
 * Sharp Linux 3.4 fb_set_var updates info->var.activate before
 * fb_pan_display(); mdss_mdp_overlay_pan_display only calls kickoff_fnc
 * when info->var.activate contains FB_ACTIVATE_FORCE or VBL.
 *
 * Not flashable; do not modify pixel RAM, panel power or BOOT.
 * The ioctl returning 0 means driver accepted request, not visible LCD PASS.
 */
#include <linux/fb.h>
#include <asm/unistd.h>
#include <fcntl.h>

static struct fb_var_screeninfo v;
static const char fb_path[]="/dev/graphics/fb0";
static long call3(long nr,long a,long b,long c){
    register long r0 __asm__("r0")=a;
    register long r1 __asm__("r1")=b;
    register long r2 __asm__("r2")=c;
    register long r7 __asm__("r7")=nr;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1),"r"(r2),"r"(r7) : "memory","cc");
    return r0;
}
static void msg(const char *s,long n){
    (void)call3(__NR_write,1,(long)s,n);
}
#define SAY(x) msg(x,(long)sizeof(x)-1)
__attribute__((noreturn)) static void die(long ec){
    (void)call3(__NR_exit,ec,0,0);
    for(;;){}
}
__attribute__((noreturn)) void _start(void){
    long fd=call3(__NR_open,(long)fb_path,O_RDWR,0);
    if(fd<0){SAY("SHL25_FBFORCE_OPEN_FAILED\n");die(2);}
    long rc=call3(__NR_ioctl,fd,FBIOGET_VSCREENINFO,(long)&v);
    if(rc<0){SAY("SHL25_FBFORCE_GET_FAILED\n");(void)call3(__NR_close,fd,0,0);die(3);}
    if(v.xres!=1080 || v.yres!=1920 || v.bits_per_pixel!=32 ||
       v.xres_virtual<1080 || v.yres_virtual<1920 ||
       v.yoffset>v.yres_virtual-v.yres ||
       v.xoffset>v.xres_virtual-v.xres){
       SAY("SHL25_FBFORCE_LAYOUT_REFUSED\n");
       (void)call3(__NR_close,fd,0,0);die(4);
    }
    v.activate=FB_ACTIVATE_FORCE;
    rc=call3(__NR_ioctl,fd,FBIOPUT_VSCREENINFO,(long)&v);
    if(rc<0){SAY("SHL25_FBFORCE_PUT_FAILED\n");(void)call3(__NR_close,fd,0,0);die(5);}
    SAY("SHL25_FBFORCE_IOCTL_SUCCESS (visual result unverified)\n");
    (void)call3(__NR_close,fd,0,0);
    die(0);
}
