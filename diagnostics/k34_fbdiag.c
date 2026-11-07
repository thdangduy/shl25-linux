/* SPDX-License-Identifier: GPL-2.0-only
 * Sharp SHL25 kernel 3.4 framebuffer live RAM test.
 * Default mode is read-only. --overlay writes a small 96x96 rectangle and
 * restores the original pixels after 1500ms; never alters panel control,
 * kernel settings, storage, BOOT, Recovery, or input state.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

static uint32_t fnv1a(const void *data, size_t size, uint32_t acc) {
    const uint8_t *p = (const uint8_t *)data;
    for (size_t i=0; i<size; ++i) { acc ^= p[i]; acc *= 16777619u; }
    return acc;
}
int main(int argc, char **argv) {
    int draw = argc==2 && !strcmp(argv[1],"--overlay");
    if(argc>2 || (argc==2 && !draw)) { fputs("usage: k34_fbdiag [--overlay]\n",stderr); return 64; }
    int fd=open("/dev/graphics/fb0", (draw?O_RDWR:O_RDONLY)|O_CLOEXEC);
    if(fd<0){perror("open fb0");return 2;}
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    if(ioctl(fd,FBIOGET_VSCREENINFO,&v)<0 || ioctl(fd,FBIOGET_FSCREENINFO,&f)<0){
        perror("fb ioctl");close(fd);return 3;
    }
    printf("FB0_META xres=%u yres=%u virtual=%ux%u offset=%u,%u bpp=%u stride=%u smem=%u\n",
       v.xres,v.yres,v.xres_virtual,v.yres_virtual,v.xoffset,v.yoffset,
       v.bits_per_pixel,f.line_length,f.smem_len);
    if(v.xres!=1080||v.yres!=1920||v.bits_per_pixel!=32||f.line_length!=4352||
       v.xres_virtual<1080||v.yres_virtual<v.yoffset+v.yres||
       f.smem_len < (uint64_t)f.line_length*(v.yoffset+v.yres)){
       puts("FB0_LAYOUT_MISMATCH_REFUSING_MMAP");close(fd);return 4;
    }
    size_t len=(size_t)f.smem_len;
    uint8_t *fb=mmap(NULL,len,draw?PROT_READ|PROT_WRITE:PROT_READ,MAP_SHARED,fd,0);
    if(fb==MAP_FAILED){printf("FB0_MMAP_FAIL errno=%d\n",errno);close(fd);return 5;}
    uint32_t hash=2166136261u, nonzero=0, samples=0;
    for(uint32_t y=0;y<v.yres;y+=40)for(uint32_t x=0;x<v.xres;x+=40){
        uint32_t pixel;
        size_t off=(size_t)(v.yoffset+y)*f.line_length+(size_t)(v.xoffset+x)*4;
        memcpy(&pixel,fb+off,4);
        hash=fnv1a(&pixel,4,hash);samples++;if(pixel)nonzero++;
    }
    printf("FB0_READ_PASS samples=%u nonzero=%u fnv1a=0x%08x\n",samples,nonzero,hash);
    if(draw) {
        const unsigned w=96,h=96;
        const unsigned x=v.xres/2-w/2,y=v.yres/2-h/2;
        const size_t row=(size_t)w*4;
        uint8_t *backup=malloc(h*row);
        if(!backup){puts("FB0_BACKUP_ALLOC_FAIL");munmap(fb,len);close(fd);return 6;}
        for(unsigned j=0;j<h;j++){
            size_t off=(size_t)(v.yoffset+y+j)*f.line_length+(size_t)(v.xoffset+x)*4;
            memcpy(backup+j*row,fb+off,row);
            for(unsigned k=0;k<w;k++){
                uint32_t c= k<w/3?0xffff00ffu:(k<2*w/3?0xff00ff00u:0xff0000ffu);
                memcpy(fb+off+k*4,&c,4);
            }
        }
        __sync_synchronize();
        printf("FB0_OVERLAY_WRITTEN x=%u y=%u w=%u h=%u visible_for_ms=1500\n",x,y,w,h);
        fflush(stdout);
        usleep(1500*1000);
        for(unsigned j=0;j<h;j++){
            size_t off=(size_t)(v.yoffset+y+j)*f.line_length+(size_t)(v.xoffset+x)*4;
            memcpy(fb+off,backup+j*row,row);
        }
        __sync_synchronize();
        puts("FB0_OVERLAY_RESTORED");
        free(backup);
    }
    munmap(fb,len);close(fd);return 0;
}
