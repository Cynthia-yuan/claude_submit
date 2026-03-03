// SPDX-License-Identifier: GPL-2.0
#include <linux/module.h>
#include <linux/kernel.h>

/* Global variable with data race */
static int global_counter = 0;

/**
 * example_function - Demonstrates a data race
 *
 * This function writes to global_counter without proper synchronization.
 * Context: Process context, can be called from multiple CPUs
 */
void example_function(void)
{
    /* BUG: This write is not protected! */
    global_counter++;  /* Line 18 - Race detected here */
    printk(KERN_INFO "Counter: %d\n", global_counter);
}

/**
 * example_read_function - Reads the global counter
 *
 * This function reads global_counter without proper synchronization.
 * Context: Process context, can be called from multiple CPUs
 */
void example_read_function(void)
{
    int val;

    /* BUG: This read is not protected! */
    val = global_counter;  /* Line 36 - Race detected here */
    printk(KERN_INFO "Read counter: %d\n", val);
}

/* Module initialization */
static int __init example_init(void)
{
    printk(KERN_INFO "Example module loaded\n");
    return 0;
}

/* Module cleanup */
static void __exit example_exit(void)
{
    printk(KERN_INFO "Example module unloaded\n");
}

module_init(example_init);
module_exit(example_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("KCSAN Test");
MODULE_DESCRIPTION("Module with data race for testing");