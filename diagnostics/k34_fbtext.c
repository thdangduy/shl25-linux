/* SPDX-License-Identifier: GPL-2.0-only
 * SHL25 kernel 3.4 RAM-only framebuffer text test.
 * Creates a visible diagnostic title for five seconds on fb0 and restores
 * the original framebuffer bytes. No partition or panel power writes.
 * This is NOT fbcon, a virtual terminal, or an interactive Linux shell.
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
typedef struct {char c;uint8_t row[7];} glyph;
static const glyph glyphs[]={
 {' ',{0,0,0,0,0,0,0}},
 {'.',{0,0,0,0,0,12,12}},
 {'2',{14,17,1,2,4,8,31}},
 {'3',{30,1,1,14,1,1,30}},
 {'4',{2,6,10,18,31,2,2}},
 {'5',{31,16,30,1,1,17,14}},
 {'C',{14,17,16,16,16,17,14}},
 {'D',{30,17,17,17,17,17,30}},
 {'E',{31,16,16,30,16,16,31}},
 {'H',{17,17,17,31,17,17,17}},
 {'I',{31,4,4,4,4,4,31}},
 {'K',{17,18,20,24,20,18,17}},
 {'L',{16,16,16,16,16,16,31}},
 {'N',{17,25,21,19,17,17,17}},
 {'R',{30,17,17,30,20,18,17}},
 {'S',{15,16,16,14,1,1,30}},
 {'T',{31,4,4,4,4,4,4}},
 {'U',{17,17,17,17,17,17,14}},
 {'X',{17,17,10,4,10,17,17}}
};
static uint8_t *mem;
static size_t stride, base, total;
static unsigned xbase,ybase,sw=650,sh=320;
static uint8_t *saved;
static int restored;
static void pixel(unsigned x,unsigned y,uint32_t c) {
    size_t o=base+(size_t)y*stride+(size_t)x*4;
    if(o+4<=total)memcpy(mem+o,&c,4);
}
static void restore_region(void){
    if(!saved || !mem || restored)return;
    for(unsigned y=0;y<sh;y++){
        size_t o=base+(size_t)(ybase+y)*stride+(size_t)xbase*4;
        memcpy(mem+o,saved+(size_t)y*sw*4,(size_t)sw*4);
    }
    __sync_synchronize();
    restored=1;
}
static void fill(unsigned x,unsigned y,unsigned w,unsigned h,uint32_t c){
    for(unsigned j=0;j<h;j++)for(unsigned i=0;i<w;i++)pixel(x+i,y+j,c);
}
static const glyph *get(char c){
    for(unsigned k=0;k<sizeof(glyphs)/sizeof(glyphs[0]);k++)
        if(glyphs[k].c==c)return &glyphs[k];
    return &glyphs[0];
}
static void line(const char *s,unsigned x,unsigned y,unsigned scale,uint32_t c) {
    while(*s){
        const glyph *g=get(*s++);
        for(unsigned row=0;row<7;row++)for(unsigned col=0;col<5;col++)
            if((g->row[row]>>(4-col))&1)
                fill(x+col*scale,y+row*scale,scale,scale,c);
        x+=6*scale;
    }
}
int main(void){
    int fd=open("/dev/graphics/fb0",O_RDWR|O_CLOEXEC);
    if(fd<0){perror("open");return 2;}
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    if(ioctl(fd,FBIOGET_VSCREENINFO,&v)<0||ioctl(fd,FBIOGET_FSCREENINFO,&f)<0){
        perror("ioctl");close(fd);return 3;
    }
    if(v.xres!=1080||v.yres!=1920||v.bits_per_pixel!=32||
       v.red.offset!=24||v.green.offset!=16||v.blue.offset!=8||
       f.line_length!=4352||f.smem_len < (uint64_t)f.line_length*(v.yoffset+v.yres)){
        puts("SHL25_LAYOUT_GUARD_FAIL");close(fd);return 4;
    }
    stride=f.line_length;total=f.smem_len;
    mem=mmap(NULL,total,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(mem==MAP_FAILED){perror("mmap");close(fd);return 5;}
    base=(size_t)v.yoffset*stride+(size_t)v.xoffset*4;
    xbase=(v.xres-sw)/2;ybase=(v.yres-sh)/2;
    saved=malloc((size_t)sw*sh*4);
    if(!saved){munmap(mem,total);close(fd);return 6;}
    for(unsigned y=0;y<sh;y++){
        size_t o=base+(size_t)(ybase+y)*stride+(size_t)xbase*4;
        memcpy(saved+(size_t)y*sw*4,mem+o,(size_t)sw*4);
    }
    fill(xbase,ybase,sw,sh,0x102238ffu);
    fill(xbase,ybase,sw,8,0x00d6caffu);
    line("SHL25",xbase+80,ybase+42,9,0xffffffffu);
    line("LINUX 3.4",xbase+80,ybase+132,6,0x00f0d0ffu);
    line("LCD TEST",xbase+80,ybase+216,6,0xffffffffu);
    __sync_synchronize();
    puts("SHL25_FB_TEXT_DRAWN 1080x1920 hold_ms=5000");
    fflush(stdout);
    usleep(5000*1000);
    restore_region();
    puts("SHL25_FB_TEXT_RESTORED");
    free(saved);munmap(mem,total);close(fd);
    return 0;
}
