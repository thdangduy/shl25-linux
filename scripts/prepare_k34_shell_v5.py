#!/usr/bin/env python3
"""Add bounded BusyBox ash and LCD verification to already-proven K34 USB PID1.

Changes the one standalone PID1 implementation. Does not touch OEM driver,
BOOT, TWRP, phone, Windows drivers, or other repository branches.
"""
from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent.parent/"diagnostics"/"k34_native_init.c"
data=p.read_text(encoding="utf8")
if "SHL25_NATIVE_BUSYBOX_V5" in data:raise SystemExit("V5_ALREADY_PREPARED")
def sub(old,new):
    global data
    n=data.count(old)
    if n!=1:raise SystemExit("REFUSE_NON_UNIQUE_ANCHOR "+str(n)+" "+repr(old[:100]))
    data=data.replace(old,new,1)

sub('#include <errno.h>\n','#include <errno.h>\n#include <signal.h>\n#include <sys/wait.h>\n#include <time.h>\n')
sub('    mkdir_ok("/dev");mkdir_ok("/proc");mkdir_ok("/sys");mkdir_ok("/cache");',
    '    mkdir_ok("/dev");mkdir_ok("/proc");mkdir_ok("/sys");mkdir_ok("/cache");')
# Insert a read-only device-node preflight. No input grab, panel control or storage writes.
anchor='static void send_str(int fd,const char *s){'
helpers=r'''
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
'''
# helpers call send_str, place after its definition rather than before.
anchor='static void console_command(int fd, const char *cmd) {'
sub(anchor,helpers+"\n"+anchor)
sub('Commands: help info cpu mem fb touch usb',
    'Commands: help info cpu mem fb touch usb shell lcd')
sub('static void console_command(int fd, const char *cmd) {\n    if(!strcmp(cmd,"help")){',
    'static void console_command(int fd, const char *cmd) {\n    if(!strcmp(cmd,"shell")){shell_on_tty(fd);\n    }else if(!strcmp(cmd,"lcd")){run_lcd_test(fd);\n    }else if(!strcmp(cmd,"help")){')
sub('    trace_usb("PID1_K34_NATIVE_V3_ALIVE cache_trace_start");',
    '    trace_usb("PID1_K34_NATIVE_V5_BUSYBOX_ALIVE");')
sub('    usb_loop(); /* PID1 must never exit. */',
    '    prepare_hw_nodes();\n    usb_loop(); /* PID1 must never exit. */')
p.write_text(data,encoding="utf8",newline="\n")
print("SHL25_K34_NATIVE_SHELL_V5_SOURCE_READY SHA256="+hashlib.sha256(p.read_bytes()).hexdigest())
