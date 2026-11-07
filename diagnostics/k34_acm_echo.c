/* SPDX-License-Identifier: GPL-2.0-only
 * SHL25 kernel 3.4 CDC ACM host/device roundtrip proof.
 * Only reads/writes ephemeral USB gadget ttyGS0 and /tmp status.
 * MUST run during a bounded TWRP USB "modem,adb" session.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#define OUT "/tmp/shl25_acm_echo_result.txt"
static void record(const char *s) {
    int fd=open(OUT,O_WRONLY|O_APPEND|O_CREAT|O_CLOEXEC,0600);
    if(fd<0)return;
    size_t n=strlen(s),off=0;
    while(off<n){ssize_t r=write(fd,s+off,n-off);if(r<=0)break;off+=(size_t)r;}
    (void)close(fd);
}
static long now_ms(void){
    struct timespec ts;
    if(clock_gettime(CLOCK_MONOTONIC,&ts)<0)return 0;
    return ts.tv_sec*1000L+ts.tv_nsec/1000000L;
}
int main(void){
    record("ACM_ECHO_START\n");
    int fd=-1;
    long end=now_ms()+11500;
    char line[128]={0};
    size_t used=0;
    while(now_ms()<end){
        if(fd<0){
            fd=open("/dev/ttyGS0",O_RDWR|O_NOCTTY|O_NONBLOCK|O_CLOEXEC);
            if(fd<0){usleep(180000);continue;}
            struct termios term;
            if(tcgetattr(fd,&term)==0){cfmakeraw(&term);(void)tcsetattr(fd,TCSANOW,&term);}
            record("ACM_TTYGS0_OPEN\n");
        }
        struct pollfd p={.fd=fd,.events=POLLIN};
        int rv=poll(&p,1,300);
        if(rv<0 && errno==EINTR)continue;
        if(rv<0 || (rv>0 && (p.revents&(POLLERR|POLLHUP|POLLNVAL)))){
            close(fd);fd=-1;usleep(120000);continue;
        }
        if(rv==0)continue;
        char buf[48];
        ssize_t n=read(fd,buf,sizeof(buf));
        if(n<0 && (errno==EINTR||errno==EAGAIN))continue;
        if(n<=0){close(fd);fd=-1;continue;}
        for(ssize_t i=0;i<n;i++){
            unsigned char c=(unsigned char)buf[i];
            if(c=='\r')continue;
            if(c=='\n'){
                line[used]=0;
                if(!strcmp(line,"SHL25PING")){
                    const char *pong="SHL25PONG\n";
                    size_t left=strlen(pong),at=0;
                    while(left){
                        ssize_t w=write(fd,pong+at,left);
                        if(w>0){at+=(size_t)w;left-=(size_t)w;continue;}
                        if(w<0 && errno==EINTR)continue;
                        if(w<0 && errno==EAGAIN){usleep(30000);continue;}
                        break;
                    }
                    if(left==0){record("SHL25_ACM_BIDIRECTIONAL_PASS\n");close(fd);return 0;}
                    record("SHL25_ACM_WRITE_FAIL\n");
                }
                used=0;
            } else if(c>=32 && c<127 && used+1<sizeof(line)){
                line[used++]=(char)c;
            }
        }
    }
    if(fd>=0)close(fd);
    record("SHL25_ACM_NO_ROUNDTRIP\n");
    return 1;
}
