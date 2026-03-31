#!/bin/bash
#
# cmd-sniper uninstallation script
#
# This script removes cmd-sniper from a Linux system.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Installation paths
PREFIX="${PREFIX:-/usr/local}"
CONFIG_DIR="/etc/cmd-sniper"
LIB_DIR="/var/lib/cmd-sniper"
LOG_DIR="/var/log/cmd-sniper"
BIN_PATH="$PREFIX/bin/cmd-sniper"

echo "=== cmd-sniper Uninstallation Script ==="
echo ""

# Check if running as root for system-wide cleanup
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Warning: Not running as root.${NC}"
    echo "Will only remove user-accessible components."
    echo ""
    ROOT_UNINSTALL=0
else
    ROOT_UNINSTALL=1
fi

# Stop any running instances
echo "Stopping cmd-sniper..."
if [ -f "/run/cmd-sniper/pid" ]; then
    if command -v cmd-sniper &> /dev/null; then
        cmd-sniper stop 2>/dev/null || true
    else
        PID=$(cat /run/cmd-sniper/pid)
        kill $PID 2>/dev/null || true
        rm -f /run/cmd-sniper/pid
    fi
fi

# Stop systemd service if running
if [ "$ROOT_UNINSTALL" -eq 1 ] && command -v systemctl &> /dev/null; then
    if systemctl is-active --quiet cmd-sniper 2>/dev/null; then
        echo "Stopping systemd service..."
        systemctl stop cmd-sniper
    fi

    if systemctl is-enabled --quiet cmd-sniper 2>/dev/null; then
        echo "Disabling systemd service..."
        systemctl disable cmd-sniper
    fi

    # Remove systemd service file
    if [ -f "/etc/systemd/system/cmd-sniper.service" ]; then
        echo "Removing systemd service file..."
        rm -f /etc/systemd/system/cmd-sniper.service
        systemctl daemon-reload
    fi
fi

# Remove auditd rules
if [ "$ROOT_UNINSTALL" -eq 1 ] && command -v auditctl &> /dev/null; then
    echo "Removing auditd rules..."
    auditctl -d exit,always -F key=cmd-sniper 2>/dev/null || true
fi

# Remove logrotate config
if [ "$ROOT_UNINSTALL" -eq 1 ] && [ -f "/etc/logrotate.d/cmd-sniper" ]; then
    echo "Removing logrotate configuration..."
    rm -f /etc/logrotate.d/cmd-sniper
fi

# Remove binary
if [ -f "$BIN_PATH" ]; then
    echo "Removing binary: $BIN_PATH"
    rm -f "$BIN_PATH"
fi

# Ask about data removal
echo ""
echo -e "${YELLOW}Data removal options:${NC}"
echo "  1) Keep all data (database, logs, config)"
echo "  2) Remove logs only"
echo "  3) Remove everything (including database)"
echo ""
read -p "Select option (1-3) [1]: " REMOVE_OPTION
REMOVE_OPTION=${REMOVE_OPTION:-1}

case $REMOVE_OPTION in
    2)
        if [ "$ROOT_UNINSTALL" -eq 1 ]; then
            echo "Removing logs..."
            rm -rf "$LOG_DIR"/*
            rmdir "$LOG_DIR" 2>/dev/null || true
        fi
        ;;
    3)
        if [ "$ROOT_UNINSTALL" -eq 1 ]; then
            echo "Removing all data..."
            rm -rf "$LIB_DIR"
            rm -rf "$LOG_DIR"
            rm -rf "$CONFIG_DIR"
            rm -rf "/run/cmd-sniper"
        else
            echo "Removing user data..."
            rm -rf "$LIB_DIR"
            rm -rf "$LOG_DIR"
            rm -rf "$CONFIG_DIR"
        fi
        ;;
    *)
        echo "Keeping all data"
        ;;
esac

# Note about remaining files
if [ "$REMOVE_OPTION" -ne 3 ]; then
    echo ""
    echo -e "${YELLOW}The following directories were preserved:${NC}"
    echo "  $CONFIG_DIR  (configuration)"
    echo "  $LIB_DIR     (database)"
    echo "  $LOG_DIR     (logs)"
    echo ""
    echo "To completely remove cmd-sniper, run:"
    echo "  sudo rm -rf $CONFIG_DIR $LIB_DIR $LOG_DIR /run/cmd-sniper"
fi

echo ""
echo -e "${GREEN}=== Uninstallation Complete ===${NC}"
