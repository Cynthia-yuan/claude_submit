// SPDX-License-Identifier: GPL-2.0
#include <linux/netdevice.h>

/* Network device private data structure */
struct net_device_priv {
    u32 flags;  /* Access without lock protection - BUG! */
};

/**
 * net_device_priv_write - Write to device private data
 *
 * This function writes to the device flags without holding a lock.
 * Called from dev_set_promiscuity and dev_change_flags.
 */
void net_device_priv_write(struct net_device *dev)
{
    struct net_device_priv *priv = netdev_priv(dev);

    /* BUG: No lock protection for concurrent writes! */
    priv->flags |= 0x01;  /* Line 19 - Race detected here (write-write) */
    printk("Updated device flags\n");
}

/**
 * net_device_priv_read - Read device private data
 *
 * This function reads the device flags without proper synchronization.
 */
void net_device_priv_read(struct net_device *dev)
{
    struct net_device_priv *priv = netdev_priv(dev);
    u32 flags = priv->flags;  /* Line 32 - Could have race */

    printk("Device flags: %u\n", flags);
}

/* Network device operations */
int dev_set_promiscuity(struct net_device *dev, int inc)
{
    net_device_priv_write(dev);
    return 0;
}

int dev_change_flags(struct net_device *dev, unsigned int flags)
{
    net_device_priv_write(dev);
    return 0;
}