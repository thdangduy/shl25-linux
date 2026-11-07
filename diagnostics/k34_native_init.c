/* SPDX-License-Identifier: GPL-2.0-only
 * Sharp SHL25 / AS99 Linux 3.4 independent diagnostic PID1, EXPERIMENTAL.
 *
 * This is NOT Android userspace. It mounts proc/sysfs and tmpfs /dev,
 * creates a verified /cache boot marker, and attempts a restricted
 * CDC ACM USB diagnostic console via Sharp's vendor kernel gadget.
 *
 * IMPORTANT: compiled/staged OFFLINE only until USB transport and rollback
 * are preflighted. No booting this from TWRP and no automatic flash.
 * USB function name "modem" is from Sharp 2016 GPL android.c with
 * CONFIG_USB_ANDROID_SH_SERIALS=y; requires host-side USB verification.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <poll.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <termios.h>
#include <unistd.h>

static void say(const char *fmt, ...) {
    char msg[512];
    va_list ap;
    va_start(ap,fmt);
    int n=vsnprintf(msg,sizeof(msg),fmt,ap);
    va_end(ap);
    if(n<=0 || (size_t)n>=sizeof(msg))return;
    int fd=open("/dev/kmsg",O_WRONLY|O_NONBLOCK|O_CLOEXEC);
    if(fd>=0){ssize_t written=write(fd,msg,(size_t)n);(void)written;close(fd);}
}

static void mkdir_ok(const char *p) {
    if(mkdir(p,0755)<0 && errno!=EEXIST)say("SHL25_NATIVE mkdir failed %s\n",p);
}
static int read_text(const char *path, char *b,size_t cap) {
    if(cap<2)return -1;
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if(fd<0)return -1;
    ssize_t n=read(fd,b,cap-1);
    close(fd);
    if(n<=0)return -1;
    b[n]=0;
    return (int)n;
}
static int write_text(const char *path,const char *s) {
    int fd=open(path,O_WRONLY|O_CLOEXEC);
    if(fd<0){say("SHL25_NATIVE write_open_fail %s errno=%d\n",path,errno);return -1;}
    ssize_t n=write(fd,s,strlen(s));
    int ok=(n==(ssize_t)strlen(s))?0:-1;
    close(fd);
    if(ok)say("SHL25_NATIVE write_fail %s errno=%d\n",path,errno);
    return ok;
}
static int dev_node(const char *path,const char *sysfs,mode_t type) {
    char b[80];
    unsigned maj=0,min=0;
    struct stat st;
    if(read_text(sysfs,b,sizeof(b))<0 || sscanf(b,"%u:%u",&maj,&min)!=2 ||
       maj<1 || maj>4095 || min>1048575)return -1;
    if(stat(path,&st)==0)
        return ((type==S_IFCHR?S_ISCHR(st.st_mode):S_ISBLK(st.st_mode)) &&
                st.st_rdev==makedev(maj,min))?0:-1;
    if(mknod(path,type|0600,makedev(maj,min))<0 && errno!=EEXIST)return -1;
    return 0;
}
static void setup_fs(void) {
    mkdir_ok("/dev");mkdir_ok("/proc");mkdir_ok("/sys");mkdir_ok("/cache");
    if(mount("tmpfs","/dev","tmpfs",MS_NOSUID,"mode=0755")<0)
        say("SHL25_NATIVE dev_tmpfs_mount_errno=%d\n",errno);
    (void)mknod("/dev/kmsg",S_IFCHR|0600,makedev(1,11));
    (void)mknod("/dev/console",S_IFCHR|0600,makedev(5,1));
    (void)mknod("/dev/null",S_IFCHR|0666,makedev(1,3));
    (void)mknod("/dev/tty",S_IFCHR|0666,makedev(5,0));
    if(mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL)<0)
        say("SHL25_NATIVE proc_errno=%d\n",errno);
    if(mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL)<0)
        say("SHL25_NATIVE sysfs_errno=%d\n",errno);
}
static void persist_marker(void) {
    char b[256];
    if(read_text("/sys/class/block/mmcblk0p32/uevent",b,sizeof(b))<0 ||
       !strstr(b,"PARTNAME=cache")){
        say("SHL25_NATIVE cache_name_unverified\n");return;
    }
    if(dev_node("/dev/mmcblk0p32","/sys/class/block/mmcblk0p32/dev",S_IFBLK)<0){
        say("SHL25_NATIVE cache_node_failed\n");return;
    }
    if(mount("/dev/mmcblk0p32","/cache","ext4",MS_RDONLY|MS_NOATIME,NULL)<0){
        say("SHL25_NATIVE cache_mount_failed errno=%d\n",errno);return;
    }
    if(mount(NULL,"/cache",NULL,MS_REMOUNT|MS_NOATIME,NULL)<0){
        say("SHL25_NATIVE cache_remount_failed\n");
        (void)umount("/cache");return;
    }
    int fd=open("/cache/shl25-k34-native.pid1.log",
                O_WRONLY|O_CREAT|O_APPEND|O_NOFOLLOW|O_CLOEXEC,0644);
    if(fd>=0){
        struct utsname u;
        if(uname(&u)==0){
            char line[160];
            int n=snprintf(line,sizeof(line),"SHL25_NATIVE_PID1 kernel=%s arch=%s\n",u.release,u.machine);
            if(n>0 && (size_t)n<sizeof(line)){
                ssize_t written=write(fd,line,(size_t)n); if(written!=(ssize_t)n)say("SHL25_NATIVE marker_write_short\n");
                (void)fsync(fd);
            }
        }
        close(fd);
    }
    /* Keep the verified ext4 /cache mounted for synchronous boot tracing. */
    say("SHL25_NATIVE cache_marker_attempted; cache_mounted\n");
}

#define SHL25_NATIVE_USB_V3_TRACE 1
static void trace_usb(const char *fmt, ...) {
    char msg[320];
    va_list ap;
    va_start(ap,fmt);
    int n=vsnprintf(msg,sizeof(msg),fmt,ap);
    va_end(ap);
    if(n<=0 || (size_t)n>=sizeof(msg))return;
    int fd=open("/cache/shl25-k34-native.usb.trace",
                O_CREAT|O_APPEND|O_WRONLY|O_CLOEXEC|O_NOFOLLOW,0644);
    if(fd>=0){
        ssize_t w=write(fd,msg,(size_t)n);
        (void)w;
        ssize_t newline_written=write(fd,"\n",1);
        (void)newline_written;
        (void)fsync(fd);
        close(fd);
    }
    say("SHL25_NATIVE_USB: %s\n",msg);
}
static int usb_write(const char *leaf, const char *val) {
    const char *root="/sys/class/android_usb/android0/";
    char path[160],actual[110];
    snprintf(path,sizeof(path),"%s%s",root,leaf);
    errno=0;
    int result=write_text(path,val);
    int failed_errno=result<0?errno:0;
    int got=read_text(path,actual,sizeof(actual));
    if(got<=0)snprintf(actual,sizeof(actual),"(write-only/unreadable)");
    else for(int i=0;i<got;i++)if(actual[i]=='\r'||actual[i]=='\n')actual[i]=' ';
    trace_usb("stage=%s requested=%s rc=%d errno=%d observed=%s",
              leaf,val,result,failed_errno,actual);
    return result;
}
static int init_usb_console(void) {
    const char *root="/sys/class/android_usb/android0/";
    char path[160],state[96];
    trace_usb("START native_v4 CDC_ACM_IAD_EF0201_without_adbd");
    /* Wait for gadget sysfs from Sharp OEM Linux 3.4. */
    int waited=0;
    for(; waited<45; waited++) {
        snprintf(path,sizeof(path),"%sfunctions",root);
        if(access(path,W_OK)==0)break;
        sleep(1);
    }
    trace_usb("android_usb sysfs waited=%d available=%d",waited,
              access("/sys/class/android_usb/android0/functions",W_OK)==0);
    if(waited==45)return -1;
    if(access("/sys/class/android_usb/android0/f_modem/acm_transports",W_OK)<0) {
        trace_usb("f_modem missing errno=%d",errno);
        return -1;
    }
    if(read_text("/sys/class/android_usb/android0/state",state,sizeof(state))>0)
        trace_usb("state_before=%s",state);
    /*
     * Standalone PID1 cannot enable adb until /dev/android_adb is opened by
     * adbd; android.c disables the gadget otherwise. Use ONLY 'modem'.
     * Keep the original PID 0001 to isolate enumeration behavior from
     * Windows driver cache; set stable SHL25 manufacturer/serial strings.
     */
    if(usb_write("enable","0")<0)return -1;
    if(usb_write("idVendor","18d1")<0)return -1;
    if(usb_write("idProduct","0002")<0)return -1;
    if(usb_write("iManufacturer","SHARP")<0)return -1;
    if(usb_write("iProduct","SHL25 Native Linux")<0)return -1;
    if(usb_write("iSerial","356594053328037")<0)return -1;
    if(usb_write("bDeviceClass","239")<0)return -1;
    if(usb_write("bDeviceSubClass","2")<0)return -1;
    if(usb_write("bDeviceProtocol","1")<0)return -1;
    if(usb_write("f_modem/acm_transports","tty")<0)return -1;
    if(usb_write("functions","modem")<0)return -1;
    if(usb_write("unlocked","1")<0)return -1;
    if(usb_write("enable","1")<0)return -1;
    if(read_text("/sys/class/android_usb/android0/state",state,sizeof(state))>0)
        trace_usb("state_after_enable=%s",state);
    sleep(2);
    if(read_text("/sys/class/android_usb/android0/state",state,sizeof(state))>0)
        trace_usb("state_after_2s=%s",state);
    return 0;
}

static void send_str(int fd,const char *s){
    if(fd>=0){size_t len=strlen(s);ssize_t written=write(fd,s,len);(void)written;}
}

#define SHL25_NATIVE_BUSYBOX_V5 1
/* Populate only nodes announced by /sys, not hardcoded kernel major/minors. */
static void prepare_hw_nodes(void) {
    char path[100],name[100];
    mkdir_ok("/dev/graphics");
    mkdir_ok("/dev/input");
    if(dev_node("/dev/graphics/fb0","/sys/class/graphics/fb0/dev",S_IFCHR)==0)
        trace_usb("hw_node_fb0_ready");
    for(unsigned i=0;i<12;i++){
        snprintf(path,sizeof(path),"/dev/input/event%u",i);
        snprintf(name,sizeof(name),"/sys/class/input/event%u/dev",i);
        (void)dev_node(path,name,S_IFCHR);
    }
}
static void shell_on_tty(int fd) {
    struct stat st;
    if(stat("/bin/busybox",&st)<0 || !S_ISREG(st.st_mode) ||
       !(st.st_mode & S_IXUSR)) {
        send_str(fd,"\r\nBusyBox static shell not installed\r\n");
        return;
    }
    struct termios before,canonical;
    int term_valid=(tcgetattr(fd,&before)==0);
    if(term_valid){
        canonical=before;
        canonical.c_lflag |= ICANON|ECHO|ISIG;
        canonical.c_iflag |= ICRNL;
        canonical.c_oflag |= OPOST|ONLCR;
        canonical.c_cc[VINTR]=3;
        canonical.c_cc[VEOF]=4;
        canonical.c_cc[VERASE]=127;
        (void)tcsetattr(fd,TCSANOW,&canonical);
    }
    send_str(fd,"\r\nSHL25 native BusyBox ash (type exit to return)\r\n");
    trace_usb("BUSYBOX_SHELL_START");
    pid_t pid=fork();
    if(pid==0){
        if(setsid()<0)_exit(124);
        (void)ioctl(fd,TIOCSCTTY,0);
        if(dup2(fd,STDIN_FILENO)<0 ||
           dup2(fd,STDOUT_FILENO)<0 ||
           dup2(fd,STDERR_FILENO)<0)_exit(125);
        if(fd>STDERR_FILENO)close(fd);
        (void)chdir("/");
        (void)setenv("PATH","/bin:/sbin",1);
        (void)setenv("HOME","/",1);
        (void)setenv("TERM","vt100",1);
        (void)setenv("PS1","shl25-k34# ",1);
        execl("/bin/busybox","sh","-i",(char*)NULL);
        _exit(127);
    }
    if(pid<0){
        trace_usb("BUSYBOX_FORK_FAILED errno=%d",errno);
        send_str(fd,"Unable to fork BusyBox shell\r\n");
    }else{
        /* PID1 supervises the shell; never exits, and does not read tty
         * while ash owns it. A persistent USB disconnect kills the child
         * after ten seconds, to avoid leaving a stranded tty process. */
        int status=0,disconnected=0;
        for(;;){
            pid_t result=waitpid(pid,&status,WNOHANG);
            if(result==pid || (result<0 && errno==ECHILD))break;
            if(result<0 && errno!=EINTR){
                trace_usb("BUSYBOX_WAITPID_FAILED errno=%d",errno);
                break;
            }
            char state[80];
            if(read_text("/sys/class/android_usb/android0/state",
                         state,sizeof(state))>0 &&
               strstr(state,"CONFIGURED"))disconnected=0;
            else disconnected++;
            if(disconnected>=10){
                trace_usb("BUSYBOX_SHELL_USB_DISCONNECTED");
                (void)kill(pid,SIGTERM);
                sleep(1);
                (void)kill(pid,SIGKILL);
                (void)waitpid(pid,&status,0);
                break;
            }
            sleep(1);
        }
        trace_usb("BUSYBOX_SHELL_EXIT status=%d",status);
    }
    if(term_valid)(void)tcsetattr(fd,TCSANOW,&before);
    send_str(fd,"\r\nBack to SHL25 diagnostic console\r\n");
}
static void run_lcd_test(int fd) {
    struct stat st;
    prepare_hw_nodes();
    if(stat("/sbin/fbtext",&st)<0 || !S_ISREG(st.st_mode)) {
        send_str(fd,"\r\nLCD test binary not installed\r\n");
        return;
    }
    send_str(fd,"\r\nLCD test: 5-second overlay, RAM pixels restored\r\n");
    pid_t pid=fork();
    if(pid==0){
        if(dup2(fd,1)<0 || dup2(fd,2)<0)_exit(126);
        if(fd>2)close(fd);
        execl("/sbin/fbtext","fbtext",(char*)NULL);
        _exit(127);
    }
    if(pid<0){send_str(fd,"LCD test fork failed\r\n");return;}
    int status=0;
    while(waitpid(pid,&status,0)<0 && errno==EINTR){}
    trace_usb("LCD_TEST_EXIT status=%d",status);
}

static void console_command(int fd, const char *cmd) {
    if(!strcmp(cmd,"shell")){shell_on_tty(fd);
    }else if(!strcmp(cmd,"lcd")){run_lcd_test(fd);
    }else if(!strcmp(cmd,"help")){
        send_str(fd,"\r\nCommands: help info cpu mem fb touch usb shell lcd\r\n");
    }else if(!strcmp(cmd,"info")){
        struct utsname u;
        if(uname(&u)==0){
            char b[220];
            snprintf(b,sizeof(b),"\r\nSHL25 native PID1, Linux %s, machine %s\r\n",u.release,u.machine);
            send_str(fd,b);
        }
    }else if(!strcmp(cmd,"cpu")||!strcmp(cmd,"mem")){
        const char *p=!strcmp(cmd,"cpu")?"/proc/cpuinfo":"/proc/meminfo";
        char b[1800];
        if(read_text(p,b,sizeof(b))>0)send_str(fd,b);
    }else if(!strcmp(cmd,"fb")){
        char b[64];
        if(read_text("/sys/class/graphics/fb0/modes",b,sizeof(b))>=0)send_str(fd,b);
        else send_str(fd,"No fb0 sysfs node\r\n");
    }else if(!strcmp(cmd,"touch")){
        char b[80];
        if(read_text("/sys/class/input/input3/name",b,sizeof(b))>=0)send_str(fd,b);
        else send_str(fd,"Touch device not present\r\n");
    }else if(!strcmp(cmd,"usb")){
        char b[96];
        if(read_text("/sys/class/android_usb/android0/state",b,sizeof(b))>=0)send_str(fd,b);
        else send_str(fd,"USB state unavailable\r\n");
    }else if(*cmd){send_str(fd,"\r\nUnknown command; type help\r\n");}
    send_str(fd,"\r\nshl25> ");
}
static void usb_loop(void) {
    char cmd[96];
    size_t used=0;
    unsigned missing=0,opened=0;
    trace_usb("usb_loop_enter");
    for(;;){
        if(dev_node("/dev/ttyGS0","/sys/class/tty/ttyGS0/dev",S_IFCHR)<0){
            if(missing++<4)trace_usb("ttyGS0_devnode_missing errno=%d",errno);
            sleep(2);continue;
        }
        int fd=open("/dev/ttyGS0",O_RDWR|O_NONBLOCK|O_NOCTTY|O_CLOEXEC);
        if(fd<0){
            if(missing++<4)trace_usb("ttyGS0_open_failed errno=%d",errno);
            sleep(2);continue;
        }
        if(opened++<4)trace_usb("ttyGS0_open_pass attempts=%u",opened);
        struct termios term;
        if(tcgetattr(fd,&term)==0){
            cfmakeraw(&term);
            (void)tcsetattr(fd,TCSANOW,&term);
        }
        send_str(fd,"\r\nSHL25 Native Linux 3.4 diagnostic console\r\nshl25> ");
        for(;;){
            struct pollfd pfd={.fd=fd,.events=POLLIN};
            int rc=poll(&pfd,1,2000);
            if(rc<0 && errno==EINTR)continue;
            if(rc<0 || (rc>0 && (pfd.revents&(POLLERR|POLLHUP|POLLNVAL))))break;
            if(rc==0)continue;
            char b[64];
            ssize_t n=read(fd,b,sizeof(b));
            if(n<0 && (errno==EAGAIN||errno==EINTR))continue;
            if(n<=0)break;
            for(ssize_t i=0;i<n;i++){
                unsigned char c=(unsigned char)b[i];
                if(c=='\r'||c=='\n'){
                    cmd[used]=0;
                    console_command(fd,cmd);
                    used=0;
                }else if(c>=32 && c<127 && used+1<sizeof(cmd)){
                    cmd[used++]=(char)c;
                    ssize_t echoed=write(fd,&c,1);(void)echoed;
                }
            }
        }
        close(fd);
        sleep(1);
    }
}
int main(void) {
    setup_fs();
    say("SHL25_NATIVE_PID1_START\n");
    /* Allow board eMMC probe before cache marker; no hardcoded power changes. */
    for(int i=0;i<60;i++){
        if(access("/sys/class/block/mmcblk0p32/uevent",R_OK)==0)break;
        sleep(1);
    }
    persist_marker();
    trace_usb("PID1_K34_NATIVE_V5_BUSYBOX_ALIVE");
    if(init_usb_console()<0)trace_usb("USB_ACM_SETUP_FAILED");
    else trace_usb("USB_ACM_SETUP_DONE");
    prepare_hw_nodes();
    usb_loop(); /* PID1 must never exit. */
    return 0;
}
