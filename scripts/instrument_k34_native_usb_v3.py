#!/usr/bin/env python3
"""Instrument SHL25 kernel 3.4 native PID1 with persisted USB bring-up evidence.

Source-to-source guarded edit to diagnostics/k34_native_init.c. Never edits
BOOT, Recovery, phone, kernel driver or official Sharp GPL archive.
"""
from pathlib import Path
import hashlib
import sys

p=Path(__file__).resolve().parent.parent/"diagnostics"/"k34_native_init.c"
original=p.read_text(encoding="utf8")
if "SHL25_NATIVE_USB_V3_TRACE" in original:
    raise SystemExit("ALREADY_INSTRUMENTED")
def replace_once(old,new):
    global original
    count=original.count(old)
    if count!=1: raise SystemExit("EXPECTED_ANCHOR_ONCE; count="+str(count)+": "+repr(old[:120]))
    original=original.replace(old,new,1)

replace_once(
    '    (void)umount("/cache");\n    say("SHL25_NATIVE cache_marker_attempted\\n");',
    '    /* Keep the verified ext4 /cache mounted for synchronous boot tracing. */\n'
    '    say("SHL25_NATIVE cache_marker_attempted; cache_mounted\\n");'
)

start=original.index("static int init_usb_console(void) {")
end=original.index("static void send_str(int fd",start)
usb= r'''
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
        (void)write(fd,"\n",1);
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
    trace_usb("START native_v3 CDC_ACM_without_adbd");
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
    if(usb_write("idProduct","0001")<0)return -1;
    if(usb_write("iManufacturer","SHARP")<0)return -1;
    if(usb_write("iProduct","SHL25 Native Linux")<0)return -1;
    if(usb_write("iSerial","356594053328037")<0)return -1;
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
'''
original=original[:start]+usb+"\n"+original[end:]
replace_once(
'''static void usb_loop(void) {
    char cmd[96];
    size_t used=0;
    for(;;){
        if(dev_node("/dev/ttyGS0","/sys/class/tty/ttyGS0/dev",S_IFCHR)<0){
            sleep(2);continue;
        }
        int fd=open("/dev/ttyGS0",O_RDWR|O_NONBLOCK|O_NOCTTY|O_CLOEXEC);
        if(fd<0){sleep(2);continue;}
''',
'''static void usb_loop(void) {
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
'''
)
replace_once(
'''    persist_marker();
    if(init_usb_console()<0)say("SHL25_NATIVE_USB_ACM_NOT_READY\\n");
    usb_loop();''',
'''    persist_marker();
    trace_usb("PID1_K34_NATIVE_V3_ALIVE cache_trace_start");
    if(init_usb_console()<0)trace_usb("USB_ACM_SETUP_FAILED");
    else trace_usb("USB_ACM_SETUP_DONE");
    usb_loop();'''
)
p.write_text(original,encoding="utf8",newline="\n")
print("INSTRUMENTED:",p,"bytes",p.stat().st_size,"sha256",hashlib.sha256(p.read_bytes()).hexdigest())
