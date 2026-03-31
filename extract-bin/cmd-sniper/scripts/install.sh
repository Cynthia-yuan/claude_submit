#!/bin/bash
#
# cmd-sniper installation script
#
# This script installs cmd-sniper on a Linux system.
# Run with sudo for full functionality.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
PREFIX="${PREFIX:-/usr}"
INSTALL_DIR="${PREFIX}/local"
CONFIG_DIR="/etc/cmd-sniper"
LIB_DIR="/var/lib/cmd-sniper"
LOG_DIR="/var/log/cmd-sniper"
RUN_DIR="/run/cmd-sniper"

# Source directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

echo "=== cmd-sniper Installation Script ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Warning: Not running as root.${NC}"
    echo "Some features (auditd, eBPF) require root privileges."
    echo ""
    read -p "Continue with limited installation? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    ROOT_INSTALL=0
else
    ROOT_INSTALL=1
fi

# Detect Python version
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        PYTHON=$cmd
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}Error: Python not found. Please install Python 3.7+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python: $PYTHON ($PYTHON_VERSION)"

# Check Python version
MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 7 ]); then
    echo -e "${RED}Error: Python 3.7+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$LIB_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$RUN_DIR"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd "$SCRIPT_DIR"

if [ -f "requirements.txt" ]; then
    if [ "$ROOT_INSTALL" -eq 1 ]; then
        $PYTHON -m pip install -r requirements.txt
    else
        $PYTHON -m pip install --user -r requirements.txt
    fi
else
    echo -e "${YELLOW}Warning: requirements.txt not found${NC}"
fi

# Install the CLI script
echo ""
echo "Installing CLI script..."

# Create wrapper script
cat > "$INSTALL_DIR/bin/cmd-sniper" << 'EOF'
#!/bin/bash
# cmd-sniper wrapper script

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
exec python3 "$SCRIPT_DIR/../lib/cmd-sniper/src/cli.py" "$@"
EOF

chmod +x "$INSTALL_DIR/bin/cmd-sniper"

# Copy source files
echo "Copying source files..."
cp -r "$SCRIPT_DIR/src" "$LIB_DIR/cmd-sniper/"
cp -r "$SCRIPT_DIR/ebpf" "$LIB_DIR/cmd-sniper/"

# Update wrapper to use correct paths
cat > "$INSTALL_DIR/bin/cmd-sniper" << EOF
#!/bin/bash
# cmd-sniper wrapper script

exec $PYTHON "$LIB_DIR/cmd-sniper/src/cli.py" "\$@"
EOF
chmod +x "$INSTALL_DIR/bin/cmd-sniper"

# Install auditd rules (if root)
if [ "$ROOT_INSTALL" -eq 1 ]; then
    echo ""
    echo "Configuring auditd..."

    # Check if auditd is installed
    if command -v auditctl &> /dev/null; then
        # Check if rules already exist
        if auditctl -l | grep -q "cmd-sniper"; then
            echo "  auditd rules already exist"
        else
            # Add rules to monitor execve
            auditctl -a exit,always -F arch=b64 -S execve -F key=cmd-sniper 2>/dev/null || true
            auditctl -a exit,always -F arch=b32 -S execve -F key=cmd-sniper 2>/dev/null || true
            echo "  auditd rules added"
        fi
    else
        echo -e "${YELLOW}  auditd not found, skipping auditd configuration${NC}"
    fi

    # Set up logrotate
    cat > /etc/logrotate.d/cmd-sniper << 'EOFEOF'
/var/log/cmd-sniper/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
EOFEOF
    echo "  logrotate configuration created"

    # Set permissions
    chown root:root "$CONFIG_DIR"
    chown root:root "$LIB_DIR"
    chown root:root "$LOG_DIR"
    chmod 755 "$CONFIG_DIR" "$LIB_DIR" "$LOG_DIR"
else
    echo ""
    echo -e "${YELLOW}Skipping system configuration (not root)${NC}"
fi

# Create default config
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cat > "$CONFIG_DIR/config.yaml" << 'EOFEOF'
# cmd-sniper configuration

capture:
  method: auditd  # 'auditd', 'ebpf', or 'both'
  auditd_log_path: /var/log/audit/audit.log
  ebpf_buffer_size: 1024
  capture_env: false

storage:
  db_path: /var/lib/cmd-sniper/commands.db
  max_size_mb: 1000
  retention_days: 90

analysis:
  min_command_length: 1
  exclude_commands:
    - ""
    - "ls"
    - "cd"
    - "pwd"
    - "history"

report:
  output_dir: /var/lib/cmd-sniper/reports
  top_n: 100
  include_time_series: true
  include_user_heatmap: true
EOFEOF
    echo "Created default configuration: $CONFIG_DIR/config.yaml"
fi

# Create systemd service (if root and systemd available)
if [ "$ROOT_INSTALL" -eq 1 ] && command -v systemctl &> /dev/null; then
    echo ""
    echo "Creating systemd service..."

    cat > /etc/systemd/system/cmd-sniper.service << 'EOFEOF'
[Unit]
Description=cmd-sniper - Linux Command Audit Tool
After=network.target auditd.service

[Service]
Type=simple
ExecStart=/usr/local/bin/cmd-sniper start --method both --daemon
ExecStop=/usr/local/bin/cmd-sniper stop
Restart=on-failure
RestartSec=10
PIDFile=/run/cmd-sniper/pid

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/cmd-sniper /var/log/cmd-sniper /run/cmd-sniper

[Install]
WantedBy=multi-user.target
EOFEOF

    systemctl daemon-reload
    echo "  systemd service created"
    echo ""
    echo "To start the service:"
    echo "  sudo systemctl start cmd-sniper"
    echo ""
    echo "To enable on boot:"
    echo "  sudo systemctl enable cmd-sniper"
fi

# Initialize database
echo ""
echo "Initializing database..."
if [ "$ROOT_INSTALL" -eq 1 ]; then
    $INSTALL_DIR/bin/cmd-sniper init
else
    $PYTHON "$SCRIPT_DIR/src/cli.py" init
fi

# Summary
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Binary installed to: $INSTALL_DIR/bin/cmd-sniper"
echo "Configuration:       $CONFIG_DIR/config.yaml"
echo "Database:            $LIB_DIR/commands.db"
echo ""
echo "Usage:"
echo "  sudo cmd-sniper start          # Start capturing"
echo "  sudo cmd-sniper status         # Show status"
echo "  sudo cmd-sniper report         # Generate report"
echo "  sudo cmd-sniper query 'pattern' # Search commands"
echo ""
echo "Run 'cmd-sniper --help' for more options."
