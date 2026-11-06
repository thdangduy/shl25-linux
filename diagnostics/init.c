/*
 * SHL25 Linux 3.4/6.16: statically linked, single-purpose diagnostic PID 1.
 * Not Android, not systemd, not a full Ubuntu init. No network, no flash.
 * Optional read/write access is restricted to the VERIFIED GPT 'cache'
 * partition; never mounts or modifies userdata, BOOT, or Recovery.
 *
 * This process MUST remain alive: exiting PID 1 triggers kernel panic.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <unistd.h>

static void emit(const char *phase, const char *detail)
{
    char line[400];
    int len = snprintf(line, sizeof(line),
                       "SHL25_DIAG phase=%s %s\n", phase, detail ? detail : "");
    if (len <= 0 || (size_t)len >= sizeof(line)) return;

    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (fd >= 0) {
        ssize_t bytes_written = write(fd, line, (size_t)len);
        (void)bytes_written;
        close(fd);
    }
    fd = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (fd >= 0) {
        ssize_t bytes_written = write(fd, line, (size_t)len);
        (void)bytes_written;
        close(fd);
    }
}

static void mkdir_safe(const char *p)
{
    if (mkdir(p, 0755) != 0 && errno != EEXIST) {
        char detail[120];
        snprintf(detail, sizeof(detail), "mkdir=%s errno=%d", p, errno);
        emit("warning", detail);
    }
}

static int is_verified_sharp_cache(void)
{
    char b[1024];
    int fd = open("/sys/class/block/mmcblk0p32/uevent", O_RDONLY | O_CLOEXEC);
    if (fd < 0) return 0;
    ssize_t n = read(fd, b, sizeof(b) - 1);
    close(fd);
    if (n <= 0) return 0;
    b[n] = '\0';
    return strstr(b, "\nPARTNAME=cache\n") != NULL ||
           (n >= 15 && strcmp(b + n - 15, "\nPARTNAME=cache\n") == 0);
}


/*
 * On legacy Sharp 3.4, devtmpfs is disabled. Construct only the
 * *verified* cache block node from its live sysfs major:minor.
 * The same fallback is useful if mainline devtmpfs isn't populated.
 */
static int ensure_cache_node(void)
{
    const char *path = "/dev/mmcblk0p32";
    struct stat st;
    if (stat(path, &st) == 0 && S_ISBLK(st.st_mode)) return 1;

    char b[64];
    int fd = open("/sys/class/block/mmcblk0p32/dev", O_RDONLY | O_CLOEXEC);
    if (fd < 0) return 0;
    ssize_t n = read(fd, b, sizeof(b) - 1);
    close(fd);
    if (n <= 0) return 0;
    b[n] = '\0';

    unsigned major_no = 0, minor_no = 0;
    if (sscanf(b, "%u:%u", &major_no, &minor_no) != 2)
        return 0;
    if (major_no == 0 || major_no > 4095 || minor_no > 1048575)
        return 0;

    if (mknod(path, S_IFBLK | 0600, makedev(major_no, minor_no)) != 0 &&
        errno != EEXIST) {
        emit("mmc", "mknod cache failed");
        return 0;
    }
    return stat(path, &st) == 0 && S_ISBLK(st.st_mode) &&
           st.st_rdev == makedev(major_no, minor_no);
}

static void ensure_early_console(void)
{
    /* These are character devices; harmless if already present. */
    if (mknod("/dev/console", S_IFCHR | 0600, makedev(5, 1)) != 0 &&
        errno != EEXIST) {
        /* /dev/console is optional for cache-marker diagnostics. */
    }
    if (mknod("/dev/kmsg", S_IFCHR | 0600, makedev(1, 11)) != 0 &&
        errno != EEXIST) {
        /* /dev/kmsg is optional for cache-marker diagnostics. */
    }
}

static void persist_once(void)
{
    if (!is_verified_sharp_cache()) {
        emit("cache", "PARTNAME=cache not found, refusing mount/write");
        return;
    }

    emit("cache", "verified GPT PARTNAME=cache on mmcblk0p32");
    if (mount("/dev/mmcblk0p32", "/cache", "ext4", MS_RDONLY | MS_NOATIME, NULL) != 0) {
        char d[96];
        snprintf(d, sizeof(d), "read-only ext4 mount failed errno=%d", errno);
        emit("cache", d);
        return;
    }
    emit("cache", "read-only ext4 mount success");

    if (mount(NULL, "/cache", NULL, MS_REMOUNT | MS_NOATIME, NULL) != 0) {
        char d[100];
        snprintf(d, sizeof(d), "rw remount failed errno=%d", errno);
        emit("cache", d);
        (void)umount2("/cache", 0);
        return;
    }

    int fd = open("/cache/shl25-616-diag.log",
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0644);
    if (fd < 0) {
        char d[100];
        snprintf(d, sizeof(d), "marker open failed errno=%d", errno);
        emit("cache", d);
        (void)umount2("/cache", 0);
        return;
    }

    struct utsname u;
    char line[300];
    if (uname(&u) == 0) {
        snprintf(line, sizeof(line), "SHL25_DIAG_PID1_OK kernel=%s arch=%s cache=verified\n",
                 u.release, u.machine);
    } else {
        snprintf(line, sizeof(line), "SHL25_DIAG_PID1_OK kernel=unknown cache=verified\n");
    }
    ssize_t n = write(fd, line, strlen(line));
    int write_ok = n == (ssize_t)strlen(line) && fsync(fd) == 0;
    close(fd);
    emit(write_ok ? "marker_ok" : "marker_error", line);
    (void)umount2("/cache", 0);
}

int main(void)
{
    mkdir_safe("/dev");
    mkdir_safe("/proc");
    mkdir_safe("/sys");
    mkdir_safe("/cache");
    ensure_early_console();

    /* Console may already be present from the initial CPIO node. */
    emit("init", "static ARMHF PID1 reached");
    if (mount("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755") == 0)
        emit("dev", "devtmpfs mounted");
    else
        emit("dev", "devtmpfs unavailable; sysfs block-node fallback enabled");

    if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) == 0)
        emit("proc", "proc mounted");
    else
        emit("proc", "proc mount failed");

    if (mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) == 0)
        emit("sysfs", "sysfs mounted");
    else
        emit("sysfs", "sysfs mount failed");

    struct utsname u;
    if (uname(&u) == 0) emit("kernel", u.release);

    /* Wait for eMMC block enumeration, without assuming USB or display. */
    for (int i = 0; i < 60; i++) {
        if (is_verified_sharp_cache() && ensure_cache_node()) {
            emit("mmc", "cache partition appeared");
            persist_once();
            break;
        }
        if (i == 59) emit("mmc", "cache partition did not appear in 60s");
        sleep(1);
    }

    emit("init", "idle; no reboot, no module load, no extra device changes");
    for (;;) sleep(60);
}
