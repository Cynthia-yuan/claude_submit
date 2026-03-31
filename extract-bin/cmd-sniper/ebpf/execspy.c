/*
 * execspy.c - eBPF program to trace execve system calls
 *
 * This eBPF program traces all execve/execveat system calls and captures
 * the command being executed along with user context (uid, pid, etc.).
 *
 * Compile with:
 *   clang -O2 -target bpf -c execspy.c -o execspy.o
 *
 * Load with:
 *   bpftool prog load execspy.o /sys/fs/bpf/execspy
 */

#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <linux/bpf.h>

#define ARG_SIZE 128
#define MAX_ARGS 5

/* Event structure sent to userspace */
struct exec_event {
    u32 pid;
    u32 uid;
    u32 ppid;
    char comm[TASK_COMM_LEN];
    char argv[ARG_SIZE];
    u64 timestamp_ns;
};

/* BPF perf map for sending events to userspace */
BPF_PERF_OUTPUT(events);

/*
 * Trace execve system call entry
 *
 * This function is called when any process calls execve().
 * We capture the PID, UID, command name, and arguments.
 */
int trace_execve(struct pt_regs *ctx,
    const char __user *const __user *__filename,
    const char __user *const __user *__const __argv,
    const char __user *const __user *__const __envp)
{
    struct exec_event event = {};
    u64 pid_tgid = bpf_get_current_pid_tgid();

    event.pid = pid_tgid >> 32;
    event.uid = bpf_get_current_uid_gid() & 0xffffffff;
    event.timestamp_ns = bpf_ktime_get_ns();

    /* Get the task comm (command name) */
    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    /* Get parent PID */
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    event.ppid = task->real_parent->tgid;

    /* Read the filename being executed */
    const char __user *arg_ptr;
    bpf_probe_read_user(&arg_ptr, sizeof(arg_ptr), &__filename[0]);

    /* Read the actual filename string */
    bpf_probe_read_user_str(&event.argv, ARG_SIZE, arg_ptr);

    /* Try to read a few arguments if space permits */
    #pragma unroll
    for (int i = 1; i < MAX_ARGS; i++) {
        bpf_probe_read_user(&arg_ptr, sizeof(arg_ptr), &__argv[i]);
        if (arg_ptr == NULL) {
            break;
        }

        /* Append space and next argument */
        int offset = 0;
        #pragma unroll
        for (int j = 0; j < ARG_SIZE - 1; j++) {
            if (event.argv[j] == '\0') {
                offset = j;
                break;
            }
        }

        if (offset > 0 && offset < ARG_SIZE - 2) {
            event.argv[offset] = ' ';
            bpf_probe_read_user_str(&event.argv[offset + 1], ARG_SIZE - offset - 1, arg_ptr);
        }
    }

    /* Send event to userspace */
    events.perf_submit(ctx, &event, sizeof(event));

    return 0;
}

/*
 * Alternative: Use tracepoint for more stable tracing
 *
 * Tracepoints are more stable than kprobes as they have stable ABIs.
 * This uses the sched_process_exec tracepoint which fires after
 * a successful exec.
 */
TRACEPOINT_PROBE(sched, sched_process_exec)
{
    struct exec_event event = {};

    event.pid = pid >> 32;
    event.uid = bpf_get_current_uid_gid() & 0xffffffff;
    event.timestamp_ns = bpf_ktime_get_ns();

    /* Get the task comm */
    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    /* Get parent PID */
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    event.ppid = task->real_parent->tgid;

    /* Get the filename being executed */
    bpf_probe_read_str(&event.argv, ARG_SIZE, args->filename);

    /* Send event to userspace */
    events.perf_submit(args, &event, sizeof(event));

    return 0;
}
