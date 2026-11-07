/* SPDX-License-Identifier: GPL-2.0-only
 * SHL25 standalone Linux 3.4: 5-point and 3/4/5-finger visual touch test.
 * RAM-only, ARMv7 EABI no-libc. No Android framework, flash or power writes.
 *
 * The driver uses ABS_MT_TOUCH_MAJOR=0x30, NOT ABS_MT_SLOT=0x30!
 * Supports both type A (SYN_MT_REPORT) and type B (ABS_MT_SLOT=0x2f).
 * Only accepts multi-touch when UNIQUE target positions occur in the
 * SAME SYN_REPORT frame. Output: /tmp/shl25-touch-points.log and console.
 */
#include <linux/fb.h>
#include <linux/input.h>
#include <asm/unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <time.h>
#include <stdint.h>

static long sc3(long n,long a,long b,long c){
    register long r0 __asm__("r0")=a, r1 __asm__("r1")=b;
    register long r2 __asm__("r2")=c, r7 __asm__("r7")=n;
    __asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory","cc");
    return r0;
}
static long sc6(long n,long a,long b,long c,long d,long e,long f){
    register long r0 __asm__("r0")=a, r1 __asm__("r1")=b;
    register long r2 __asm__("r2")=c, r3 __asm__("r3")=d;
    register long r4 __asm__("r4")=e, r5 __asm__("r5")=f;
    register long r7 __asm__("r7")=n;
    __asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");
    return r0;
}
/* GCC ARM EABI division-by-zero fallback: fail closed, never continue. */
__attribute__((noreturn)) int raise(int signum){
    (void)signum;
    (void)sc3(__NR_exit,127,0,0);
    for(;;){}
}
static int fbf, evf, logf=-1;
static struct fb_var_screeninfo fbv;
static struct fb_fix_screeninfo fbfixed;
static volatile unsigned char *fb;
static unsigned char *backup;
static unsigned stride,total,offset;
static int points_x[5], points_y[5];
static int stage=0,tap_index=0,release_needed=1,quiet_frames=0;
static int multi_dwell=0,misses=0,has_slots=0,current_slot=0,need_redraw=1;
static unsigned rnd=0x51A99037;
static unsigned long start_sec;
static int last_contacts=0;
struct contact {int x,y,major,tracking,hx,hy,active;};
static struct contact slots[32],partial,frame[16];
static int frame_count=0, frame_activity=0;
struct glyph{char ch;unsigned char b[7];};
static const struct glyph fonts[]={
 {' ',{0,0,0,0,0,0,0}},
 {'0',{14,17,19,21,25,17,14}},
 {'1',{4,12,4,4,4,4,14}},
 {'2',{14,17,1,2,4,8,31}},
 {'3',{30,1,1,14,1,1,30}},
 {'4',{2,6,10,18,31,2,2}},
 {'5',{31,16,30,1,1,17,14}},
 {'A',{14,17,17,31,17,17,17}},
 {'B',{30,17,17,30,17,17,30}},
 {'C',{14,17,16,16,16,17,14}},
 {'D',{30,17,17,17,17,17,30}},
 {'E',{31,16,16,30,16,16,31}},
 {'F',{31,16,16,30,16,16,16}},
 {'G',{14,17,16,23,17,17,15}},
 {'H',{17,17,17,31,17,17,17}},
 {'I',{31,4,4,4,4,4,31}},
 {'L',{16,16,16,16,16,16,31}},
 {'M',{17,27,21,21,17,17,17}},
 {'N',{17,25,21,19,17,17,17}},
 {'O',{14,17,17,17,17,17,14}},
 {'P',{30,17,17,30,16,16,16}},
 {'R',{30,17,17,30,20,18,17}},
 {'S',{15,16,16,14,1,1,30}},
 {'T',{31,4,4,4,4,4,4}},
 {'U',{17,17,17,17,17,17,14}},
 {'V',{17,17,17,17,17,10,4}},
 {'W',{17,17,17,21,21,21,10}},
 {'X',{17,17,10,4,10,17,17}},
 {'Y',{17,17,10,4,4,4,4}},
 {'Z',{31,1,2,4,8,16,31}}
};
static void rawout(const char *s,int n){
    if(n>0){
        (void)sc3(__NR_write,1,(long)s,n);
        if(logf>=0)(void)sc3(__NR_write,logf,(long)s,n);
    }
}
static int append(char *dest,int size,int pos,const char *s){
    while(*s && pos<size-1)dest[pos++]=*s++;
    dest[pos]=0;return pos;
}
static int decimal(char *dest,int size,int pos,int value){
    char rev[16];unsigned v;int n=0;
    if(value<0){if(pos<size-1)dest[pos++]='-';v=(unsigned)(-(value+1))+1;}
    else v=(unsigned)value;
    do{rev[n++]=(char)('0'+(v%10));v/=10;}while(v && n<15);
    while(n && pos<size-1)dest[pos++]=rev[--n];
    dest[pos]=0;return pos;
}
static void record(const char *tag,int a,int b,int c,int d){
    char line[200];int n=0;
    n=append(line,200,n,"SHL25_TOUCH_");
    n=append(line,200,n,tag);
    n=append(line,200,n," a=");n=decimal(line,200,n,a);
    n=append(line,200,n," b=");n=decimal(line,200,n,b);
    n=append(line,200,n," c=");n=decimal(line,200,n,c);
    n=append(line,200,n," d=");n=decimal(line,200,n,d);
    n=append(line,200,n,"\n");
    rawout(line,n);
}
static unsigned random32(void){
    rnd ^= rnd<<13;rnd^=rnd>>17;rnd^=rnd<<5;return rnd;
}
static void delay_ms(unsigned ms){
    struct timespec t={(long)(ms/1000),(long)(ms%1000)*1000000L};
    (void)sc3(__NR_nanosleep,(long)&t,0,0);
}
static long monotime(void){
    struct timespec t={0,0};
    if(sc3(__NR_clock_gettime,1,(long)&t,0)<0)return 0;
    return t.tv_sec;
}
#define RGB(r,g,b) ((uint32_t)(((uint32_t)(r)<<24)|((uint32_t)(g)<<16)|((uint32_t)(b)<<8)|0xffU))
#define BG RGB(12,18,33)
#define WHITE RGB(239,245,255)
#define RED RGB(240,67,81)
#define GREEN RGB(50,223,149)
#define GOLD RGB(255,204,81)
#define BLUE RGB(38,72,124)
static void pixel(int x,int y,uint32_t color){
    if((unsigned)x>=1080U||(unsigned)y>=1920U)return;
    unsigned index=offset+(unsigned)y*stride+(unsigned)x*4;
    if(index+4>total)return;
    *(volatile uint32_t *)(fb+index)=color;
}
static void rect(int x,int y,int w,int h,uint32_t c){
    for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)pixel(xx,yy,c);
}
static void circle(int cx,int cy,int radius,int thick,uint32_t c){
    int r2=radius*radius,inside=(radius-thick)*(radius-thick);
    for(int y=cy-radius;y<=cy+radius;y++){
        int dy=(y-cy)*(y-cy);
        for(int x=cx-radius;x<=cx+radius;x++){
            int d=(x-cx)*(x-cx)+dy;
            if(d<=r2 && d>=inside)pixel(x,y,c);
        }
    }
}
static const struct glyph *getglyph(char ch){
    for(unsigned i=0;i<sizeof(fonts)/sizeof(fonts[0]);i++)if(fonts[i].ch==ch)return &fonts[i];
    return &fonts[0];
}
static void textat(const char *s,int x,int y,int scale,uint32_t color){
    while(*s){
        const struct glyph *g=getglyph(*s++);
        for(int row=0;row<7;row++)for(int col=0;col<5;col++)
            if((g->b[row]>>(4-col))&1)rect(x+col*scale,y+row*scale,scale,scale,color);
        x+=6*scale;
    }
}
static void refresh(void){
    __sync_synchronize();
    fbv.activate=FB_ACTIVATE_FORCE;
    long rc=sc3(__NR_ioctl,fbf,FBIOPUT_VSCREENINFO,(long)&fbv);
    if(rc<0)record("REFRESH_ERROR",(int)rc,stage,0,0);
}
static void targets_init(void){
    const int cx[5]={272,815,538,273,812};
    const int cy[5]={452,484,935,1490,1504};
    for(int i=0;i<5;i++){
        points_x[i]=cx[i]+(int)(random32()%101)-50;
        points_y[i]=cy[i]+(int)(random32()%121)-60;
        record("TARGET",i+1,points_x[i],points_y[i],116);
    }
}
static void draw(void){
    for(int y=0;y<1920;y++)for(int x=0;x<1080;x++)pixel(x,y,BG);
    rect(0,0,1080,18,RED);
    textat("SHL25 TOUCH",115,75,10,WHITE);
    rect(60,190,960,7,BLUE);
    if(stage==0){
        textat("TAP",170,240,11,GOLD);
        char n[2]={(char)('1'+tap_index),0};
        textat(n,445,240,11,GOLD);
        textat("1 2 3 4 5",165,350,6,WHITE);
    }else if(stage==1){textat("MULTI 3",235,247,11,GOLD);}
    else if(stage==2){textat("MULTI 4",235,247,11,GOLD);}
    else if(stage==3){textat("MULTI 5",235,247,11,GOLD);}
    else{textat("PASS",310,247,16,GREEN);}
    for(int i=0;i<5;i++){
        int passed=(stage==0 && i<tap_index);
        uint32_t ring=(passed||stage==4)?GREEN:(stage>=1?RED:GOLD);
        circle(points_x[i],points_y[i],114,15,ring);
        circle(points_x[i],points_y[i],91,3,BLUE);
        char n[2]={(char)('1'+i),0};
        textat(n,points_x[i]-34,points_y[i]-49,14,WHITE);
    }
    if(stage==0)textat("TAP IN ORDER",195,1770,8,WHITE);
    else if(stage<4)textat("HOLD TOGETHER",125,1770,8,WHITE);
    else textat("ALL PASS",275,1760,11,GREEN);
    refresh();need_redraw=0;
}
static int inradius(int x,int y,int i){
    int dx=x-points_x[i],dy=y-points_y[i];
    return dx*dx+dy*dy<=116*116;
}
static int countbits(unsigned value){
    int n=0;
    while(value){n+=(int)(value&1U);value>>=1;}
    return n;
}
static void push(struct contact c){
    if(c.hx && c.hy && c.active && frame_count<16)frame[frame_count++]=c;
}
static void frame_done(void){
    struct contact contacts[32];int n=0;
    if(has_slots){
        for(int i=0;i<32;i++)if(slots[i].active && slots[i].hx && slots[i].hy)
            contacts[n++]=slots[i];
    }else{
        push(partial);
        for(int i=0;i<frame_count;i++)contacts[n++]=frame[i];
    }
    frame_count=0;partial=(struct contact){0};
    if(!has_slots && !frame_activity){return;}
    frame_activity=0;last_contacts=n;
    if(n==0){
        if(quiet_frames<20)quiet_frames++;
        if(quiet_frames>=1){release_needed=0;multi_dwell=0;}
        return;
    }
    quiet_frames=0;
    if(release_needed || stage>=4)return;
    if(stage==0){
        if(n==1){
            int x=contacts[0].x,y=contacts[0].y;
            int target=tap_index;
            if(inradius(x,y,target)){
                int dx=x-points_x[target],dy=y-points_y[target];
                record("SINGLE_PASS",target+1,x,y,dx*dx+dy*dy);
                tap_index++;release_needed=1;
                if(tap_index==5){stage=1;record("STAGE_MULTI3",1,3,5,0);}
                need_redraw=1;
            }else if(misses++<20)record("SINGLE_MISS",target+1,x,y,0);
        }
        return;
    }
    unsigned mask=0;
    for(int j=0;j<n;j++){
        for(int i=0;i<5;i++)if(inradius(contacts[j].x,contacts[j].y,i))
            mask|=1U<<i;
    }
    unsigned expect=stage==1?0x15U:(stage==2?0x1bU:0x1fU);
    int desired=stage==1?3:(stage==2?4:5);
    if(n>=desired && countbits(mask&expect)==desired)multi_dwell++;
    else {multi_dwell=0;if(misses++<30)record("MULTI_FRAME",desired,n,(int)mask,(int)expect);}
    if(multi_dwell>=2){
        record("MULTI_PASS",desired,n,(int)mask,(int)expect);
        stage++;release_needed=1;multi_dwell=0;
        need_redraw=1;
    }
}
static void input_event(struct input_event e){
    if(e.type==EV_ABS){
        frame_activity=1;
        if(e.code==ABS_MT_SLOT){
            has_slots=1;
            if(e.value>=0 && e.value<32)current_slot=e.value;
            return;
        }
        if(has_slots){
            struct contact *p=&slots[current_slot];
            if(e.code==ABS_MT_TRACKING_ID){p->tracking=e.value;p->active=(e.value>=0);if(e.value<0){p->hx=0;p->hy=0;}}
            if(e.code==ABS_MT_POSITION_X){p->x=e.value;p->hx=1;p->active=1;}
            if(e.code==ABS_MT_POSITION_Y){p->y=e.value;p->hy=1;p->active=1;}
        }else{
            if(e.code==ABS_MT_TOUCH_MAJOR && partial.hx && partial.hy){
                push(partial);partial=(struct contact){0};
            }
            if(e.code==ABS_MT_TRACKING_ID && e.value<0){
                partial=(struct contact){0};return;
            }
            if(e.code==ABS_MT_POSITION_X){partial.x=e.value;partial.hx=1;partial.active=1;}
            if(e.code==ABS_MT_POSITION_Y){partial.y=e.value;partial.hy=1;partial.active=1;}
            if(e.code==ABS_MT_TOUCH_MAJOR)partial.major=e.value;
        }
    }else if(e.type==EV_SYN && e.code==SYN_MT_REPORT){
        frame_activity=1;
        if(!has_slots){push(partial);partial=(struct contact){0};}
    }else if(e.type==EV_SYN && e.code==SYN_REPORT){frame_done();}
}
__attribute__((noreturn)) static void finish(int code){
    if(fb && backup){
        for(unsigned i=0;i<1920U*stride;i++)fb[offset+i]=backup[i];
        refresh();
    }
    record(code==0?"ALL_PASS":code==1?"TIMEOUT":"FAIL",tap_index,stage,last_contacts,misses);
    if(fbf>=0)(void)sc3(__NR_close,fbf,0,0);
    if(evf>=0)(void)sc3(__NR_close,evf,0,0);
    if(logf>=0)(void)sc3(__NR_close,logf,0,0);
    (void)sc3(__NR_exit,code,0,0);
    for(;;){}
}
__attribute__((noreturn)) void _start(void){
    fbf=-1;evf=-1;
    logf=(int)sc3(__NR_open,(long)"/tmp/shl25-touch-points.log",O_WRONLY|O_CREAT|O_TRUNC,0644);
    rawout("SHL25_TOUCH_BEGIN_5_POINTS_AND_MULTI_3_4_5\n",(int)sizeof("SHL25_TOUCH_BEGIN_5_POINTS_AND_MULTI_3_4_5\n")-1);
    fbf=(int)sc3(__NR_open,(long)"/dev/graphics/fb0",O_RDWR,0);
    if(fbf<0){record("FB_OPEN_ERROR",fbf,0,0,0);finish(2);}
    if(sc3(__NR_ioctl,fbf,FBIOGET_VSCREENINFO,(long)&fbv)<0 ||
       sc3(__NR_ioctl,fbf,FBIOGET_FSCREENINFO,(long)&fbfixed)<0 ||
       fbv.xres!=1080 || fbv.yres!=1920 || fbv.bits_per_pixel!=32 ||
       fbv.red.offset!=24 || fbv.green.offset!=16 || fbv.blue.offset!=8 ||
       fbfixed.line_length!=4352){
        record("FB_LAYOUT_REFUSED",fbv.xres,fbv.yres,fbv.bits_per_pixel,fbfixed.line_length);finish(2);
    }
    stride=fbfixed.line_length;total=fbfixed.smem_len;
    offset=fbv.yoffset*stride+fbv.xoffset*4;
    if(offset+1920U*stride>total){record("FB_MEMORY_REFUSED",offset,total,0,0);finish(2);}
    long mmap_ret=sc6(__NR_mmap2,0,total,PROT_READ|PROT_WRITE,MAP_SHARED,fbf,0);
    if((unsigned long)mmap_ret>=0xfffff000UL){record("FB_MMAP_FAILED",(int)mmap_ret,0,0,0);finish(2);}
    fb=(volatile unsigned char *)mmap_ret;
    long saved=sc6(__NR_mmap2,0,1920U*stride,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if((unsigned long)saved>=0xfffff000UL){record("BACKUP_MMAP_FAILED",(int)saved,0,0,0);finish(2);}
    backup=(unsigned char *)saved;
    for(unsigned i=0;i<1920U*stride;i++)backup[i]=fb[offset+i];
    evf=(int)sc3(__NR_open,(long)"/dev/input/event3",O_RDONLY|O_NONBLOCK,0);
    if(evf<0){record("INPUT_OPEN_FAILED",evf,0,0,0);finish(2);}
    char name[64]={0};
    if(sc3(__NR_ioctl,evf,EVIOCGNAME(sizeof(name)),(long)name)<0 ||
       name[0]!='s'||name[1]!='h'||name[2]!='t'||name[3]!='p'){
        record("INPUT_NAME_REFUSED",name[0],name[1],name[2],name[3]);finish(2);
    }
    struct timespec ts={0,0};
    (void)sc3(__NR_clock_gettime,1,(long)&ts,0);
    rnd ^= (unsigned)ts.tv_nsec;
    start_sec=(unsigned long)ts.tv_sec;
    targets_init();
    draw();
    record("READY_TAP_1_TO_5",0,0,0,0);
    /* Wait for all fingers to be lifted before accepting first target. */
    long end=(long)start_sec+300;
    while(monotime()<end && stage<4){
        struct input_event events[32];
        long n=sc3(__NR_read,evf,(long)events,(long)sizeof(events));
        if(n>0){
            if(n%(long)sizeof(struct input_event)!=0){record("INPUT_RECORD_LENGTH_FAIL",(int)n,(int)sizeof(struct input_event),0,0);finish(2);}
            for(int i=0;i<n/(long)sizeof(struct input_event);i++)input_event(events[i]);
        }else{delay_ms(12);}
        if(need_redraw)draw();
    }
    finish(stage==4?0:1);
}
