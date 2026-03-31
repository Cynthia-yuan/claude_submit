"""
eBPF-based command capture module.
"""
import os
import signal
import time
from datetime import datetime
from typing import Optional, List, Callable
import pwd

from .base import CaptureBase, CaptureError, CaptureNotAvailableError


class EbpfCapture(CaptureBase):
    """
    Capture commands using eBPF tracing of execve system calls.

    This method uses eBPF to trace execve/execveat at the kernel level.
    It provides the most comprehensive capture but requires a newer kernel.
    """

    def __init__(self, db, config=None):
        super().__init__(db, config)
        self.bpf: Optional[object] = None
        self._bpf_module: Optional[object] = None

    def get_method_name(self) -> str:
        return "ebpf"

    def is_available(self) -> bool:
        """Check if eBPF is available."""
        try:
            # Check if BCC is available
            from bcc import BPF
            # Check kernel version (eBPF requires 4.4+)
            with open("/proc/version", "r") as f:
                version = f.read()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def check_permissions(self) -> bool:
        """Check if running with required privileges."""
        return os.geteuid() == 0

    # BPF program for tracing execve
    BPF_PROGRAM = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

#define ARG_ARRAY_SIZE 100
#define MAX_ARGS 20

struct data_t {
    u32 pid;
    u32 uid;
    u32 ppid;
    char comm[TASK_COMM_LEN];
    char argv[ARG_ARRAY_SIZE];
    u64 timestamp_ns;
};

BPF_PERF_OUTPUT(events);

// Trace execve system call
int trace_execve(struct pt_regs *ctx,
    const char __user *const __user *__filename,
    const char __user *const __user *__const __argv,
    const char __user *const __user *__const __envp)
{
    struct data_t data = {};
    u64 pid_tgid = bpf_get_current_pid_tgid();
    data.pid = pid_tgid >> 32;
    data.uid = bpf_get_current_uid_gid();
    data.timestamp_ns = bpf_ktime_get_ns();

    // Get command name
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    // Read argv (simplified - read first few arguments)
    const char __user *arg_ptr;
    char arg[64];
    int offset = 0;

    // Read filename (argv[0])
    bpf_probe_read_user(&arg_ptr, sizeof(arg_ptr), &__filename[0]);
    bpf_probe_read_user_str(&data.argv[offset], 64, arg_ptr);
    offset += 64;

    // Read up to MAX_ARGS additional arguments
    #pragma unroll
    for (int i = 1; i < MAX_ARGS; i++) {
        bpf_probe_read_user(&arg_ptr, sizeof(arg_ptr), &__argv[i]);
        if (arg_ptr == NULL) break;
        bpf_probe_read_user_str(&arg, sizeof(arg), arg_ptr);

        // Add space separator and argument
        if (offset + 1 < ARG_ARRAY_SIZE) {
            data.argv[offset] = ' ';
            offset++;
        }
        if (offset < ARG_ARRAY_SIZE) {
            bpf_probe_read_str(&data.argv[offset], ARG_ARRAY_SIZE - offset, arg);
            // Move offset past this argument
            #pragma unroll
            for (int j = 0; j < 63 && offset < ARG_ARRAY_SIZE; j++) {
                if (data.argv[offset + j] == '\\0') {
                    offset = offset + j + 1;
                    break;
                }
            }
        }
    }

    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}
"""

    # Alternative simpler BPF program using tracepoint
    BPF_TRACEPOINT_PROGRAM = """
#include <linux/sched.h>

struct data_t {
    u32 pid;
    u32 uid;
    u32 ppid;
    char comm[TASK_COMM_LEN];
    char filename[256];
};

BPF_PERF_OUTPUT(events);

// Trace sched_process_exec tracepoint
TRACEPOINT_PROBE(sched, sched_process_exec) {
    struct data_t data = {};
    data.pid = pid >> 32;
    data.uid = bpf_get_current_uid_gid();

    // Get parent PID from task_struct
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    data.ppid = task->real_parent->tgid;

    // Get command name
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    // Get filename
    bpf_probe_read_str(&data.filename, sizeof(data.filename), args->filename);

    events.perf_submit(args, &data, sizeof(data));
    return 0;
}
"""

    def start(self):
        """Start capturing commands using eBPF."""
        if not self.is_available():
            raise CaptureNotAvailableError("eBPF is not available")

        if not self.check_permissions():
            raise CaptureError("Root privileges required for eBPF capture")

        from bcc import BPF

        try:
            # Try tracepoint first (more stable)
            self.bpf = BPF(text=self.BPF_TRACEPOINT_PROGRAM, cflags=["-Wno-macro-redefined"])
        except Exception:
            # Fall back to kprobe
            self.bpf = BPF(text=self.BPF_PROGRAM)
            self.bpf.attach_kprobe(event="do_execve", fn_name="trace_execve")

        # Create session
        self._create_session()
        self.running = True

    def stop(self):
        """Stop capturing."""
        self.running = False

        if self.bpf:
            try:
                self.bpf.cleanup()
            except Exception:
                pass
            self.bpf = None

        self._close_session("stopped")

    def _event_to_record(self, event: Dict) -> Optional:
        """Convert eBPF event to CommandRecord."""
        from ..storage import CommandRecord

        # Parse command and arguments
        argv_str = event.get("argv") or event.get("filename", "")
        parts = argv_str.split(" ", 1)
        command = parts[0] if parts else ""

        try:
            username = pwd.getpwuid(event["uid"]).pw_name
        except KeyError:
            username = f"uid_{event['uid']}"

        # Convert nanoseconds to datetime
        timestamp = datetime.fromtimestamp(event.get("timestamp_ns", 0) / 1_000_000_000)

        return CommandRecord(
            timestamp=timestamp,
            uid=event["uid"],
            username=username,
            pid=event.get("pid", 0),
            ppid=event.get("ppid", 0),
            cwd="",
            command=command,
            full_command=argv_str,
            argv=argv_str.split(" ") if argv_str else [],
            capture_method="ebpf",
        )

    def capture_once(self, timeout_ms: int = 100) -> int:
        """
        Capture pending events from the perf buffer.

        Returns the number of commands captured.
        """
        if not self.running or not self.bpf:
            return 0

        count = 0

        def handle_event(_, data, __):
            nonlocal count
            event = self.bpf["events"].event(data)
            record = self._event_to_record(event)
            if record:
                self.db.insert_command(record)
                count += 1

        def handle_lost_events():
            pass

        # Try to read from perf buffer
        try:
            self.bpf["events"].open_perf_buffer(handle_event, handle_lost_events)
            self.bpf.perf_buffer_poll(timeout=timeout_ms)
        except Exception:
            pass

        return count

    def capture_forever(self, callback: Optional[Callable] = None):
        """
        Continuously capture commands.

        Args:
            callback: Optional function to call for each captured command
        """
        self.setup_signal_handlers()
        total_captured = 0

        def handle_event(_, data, __):
            nonlocal total_captured
            event = self.bpf["events"].event(data)
            record = self._event_to_record(event)
            if record:
                self.db.insert_command(record)
                total_captured += 1
                if callback:
                    callback(record)

        def handle_lost_events():
            pass

        self.bpf["events"].open_perf_buffer(handle_event, handle_lost_events)

        try:
            while self.running:
                self.bpf.perf_buffer_poll()
        except KeyboardInterrupt:
            self.stop()

        return total_captured


class BpftraceCapture(CaptureBase):
    """
    Alternative eBPF capture using bpftrace.

    This is a simpler alternative that uses bpftrace scripts
    instead of Python + BCC.
    """

    BPFTRACE_SCRIPT = """
#!/usr/bin/env bpftrace

tracepoint:syscalls:sys_enter_execve
{
    printf("%d %d %s %s\\n", pid, uid, comm, str(args->filename));
}
"""

    def get_method_name(self) -> str:
        return "bpftrace"

    def is_available(self) -> bool:
        """Check if bpftrace is available."""
        try:
            result = os.system("which bpftrace > /dev/null 2>&1")
            return result == 0
        except Exception:
            return False

    def start(self):
        """Start capturing using bpftrace."""
        if not self.is_available():
            raise CaptureNotAvailableError("bpftrace is not available")

        raise CaptureError("bpftrace capture not yet implemented")

    def stop(self):
        """Stop capturing."""
        pass
