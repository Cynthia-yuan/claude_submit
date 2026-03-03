// SPDX-License-Identifier: GPL-2.0
#include <linux/sched.h>
#include <linux/atomic.h>

/* Counter with mixed atomic/non-atomic access */
static atomic_t atomic_counter = ATOMIC_INIT(1);

/**
 * atomic_read_counter - Correctly uses atomic_read
 *
 * This is the correct way to access an atomic_t variable.
 */
void atomic_read_counter(void)
{
    int val = atomic_read(&atomic_counter);  /* Line 15 - Race detected here */
    printk("Atomic counter: %d\n", val);
}

/**
 * normal_write_counter - BUG: Non-atomic write to atomic variable
 *
 * This function incorrectly accesses atomic_t without using atomic ops.
 * This is a common bug when developers forget to use atomic_* functions.
 */
void normal_write_counter(void)
{
    /* BUG: Should use atomic_set() or atomic_inc() instead! */
    atomic_counter.counter++;  /* Line 30 - Race detected here */
    printk("Wrote counter (BUGGY!)\n");
}

/* Scheduler functions */
void scheduler_tick(void)
{
    /* Timer tick handler */
    atomic_read_counter();  /* Called here */
}

void sched_fork(void)
{
    /* Fork handling */
    normal_write_counter();  /* Called here */
}