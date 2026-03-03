#!/bin/bash
# Test KCSAN analyzer environment
# Usage: ./test-env.sh /path/to/kernel /path/to/kcsan_report.txt

KERNEL_SRC="${1:-}"
REPORT_FILE="${2:-}"

echo "KCSAN Analyzer Environment Test"
echo "================================"
echo ""

# Check kernel source
if [ -z "$KERNEL_SRC" ]; then
    echo "⚠️  No kernel source path provided"
    echo "Usage: $0 /path/to/kernel [kcsan_report.txt]"
    echo ""
    echo "Try these locations:"
    echo "  - /lib/modules/$(uname -r)/build"
    echo "  - /usr/src/linux-$(uname -r)"
    echo "  - Your kernel source directory"
    exit 1
fi

echo "✓ Checking kernel source path: $KERNEL_SRC"
if [ ! -d "$KERNEL_SRC" ]; then
    echo "  ✗ Path does not exist"
    exit 1
fi
echo "  ✓ Path exists"

# Check for key files
echo ""
echo "Checking for kernel files:"
for file in "kernel/sched/core.c" "kernel/module.c" "init/main.c" "kernel/sched/sched.h"; do
    if [ -f "$KERNEL_SRC/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (not found - may be expected)"
    fi
done

# Check KCSAN report
echo ""
if [ -n "$REPORT_FILE" ]; then
    echo "✓ Checking KCSAN report: $REPORT_FILE"
    if [ ! -f "$REPORT_FILE" ]; then
        echo "  ✗ File does not exist"
        exit 1
    fi
    echo "  ✓ File exists"

    # Check for KCSAN markers
    echo ""
    echo "Checking KCSAN report format:"
    if grep -q "BUG: KCSAN:" "$REPORT_FILE"; then
        echo "  ✓ Found KCSAN bug markers"
    else
        echo "  ✗ No KCSAN bug markers found"
    fi

    if grep -q "\.c:[0-9]" "$REPORT_FILE"; then
        echo "  ✓ Found file:line format in stack traces"
    else
        echo "  ⚠️  No file:line format found - kernel may not have debug symbols"
    fi
fi

# Test the analyzer
echo ""
echo "Testing analyzer:"
echo "  Running: kcsan-analyze analyze --help"
if /Users/yuanlulu/vscode_claude/kcsan/kcsan-analyze analyze --help > /dev/null 2>&1; then
    echo "  ✓ Analyzer is working"
else
    echo "  ✗ Analyzer failed"
    exit 1
fi

# Test with provided report
if [ -n "$REPORT_FILE" ]; then
    echo ""
    echo "Running analysis test:"
    echo "  kcsan-analyze analyze -f $REPORT_FILE -v"
    echo ""
    /Users/yuanlulu/vscode_claude/kcsan/kcsan-analyze analyze -f "$REPORT_FILE" -v 2>&1 | head -30

    echo ""
    echo "Running with source code:"
    echo "  kcsan-analyze analyze -f $REPORT_FILE -v --show-source --kernel-src $KERNEL_SRC --diagnose"
    echo ""
    /Users/yuanlulu/vscode_claude/kcsan/kcsan-analyze analyze -f "$REPORT_FILE" -v --show-source --kernel-src "$KERNEL_SRC" --diagnose 2>&1 | head -40
fi

echo ""
echo "================================"
echo "Test complete!"
echo ""
echo "If you see 'Source code not available':"
echo "  1. Check if kernel was compiled with debug symbols (CONFIG_DEBUG_INFO=y)"
echo "  2. Run with --diagnose flag for detailed information"
echo "  3. See TROUBLESHOOTING.md for more details"