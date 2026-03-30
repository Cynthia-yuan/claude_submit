#!/bin/bash
# KCSAN 白名单管理模块
# 支持按调用栈、地址、通配符匹配

# 默认白名单路径
WHITELIST_FILE="${WHITELIST_FILE:-config/whitelist.txt}"

# 检查报告是否在白名单中
# 返回: 0=在白名单, 1=不在
check_whitelist() {
    local report_key="$1"
    local whitelist="${2:-$WHITELIST_FILE}"

    [[ ! -f "$whitelist" ]] && return 1

    # key 格式: addr:func1:func2
    local addr=$(echo "$report_key" | cut -d: -f1)
    local func1=$(echo "$report_key" | cut -d: -f2)
    local func2=$(echo "$report_key" | cut -d: -f3)
    local func_pair="$func1 / $func2"

    # 1. 精确匹配函数对
    if grep -qF "$func_pair" "$whitelist" 2>/dev/null; then
        return 0
    fi

    # 2. 地址匹配
    if grep -q "ADDR:$addr" "$whitelist" 2>/dev/null; then
        return 0
    fi

    # 3. 通配符匹配
    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # 检查是否包含通配符
        if [[ "$line" == *"*"* ]]; then
            # 提取模式部分 (在 # 之前)
            local pattern="${line%%#*}"
            pattern=$(echo "$pattern" | xargs)  # 去除空格

            # 转换 glob 为正则
            local regex=$(echo "$pattern" | sed 's/\*/[^ ]*/g')

            if echo "$func_pair" | grep -qE "$regex"; then
                return 0
            fi
        fi
    done < "$whitelist"

    return 1
}

# 过滤白名单报告
# 输入: 报告文件
# 输出: 非白名单报告 (保存到文件)
filter_whitelist() {
    local input="$1"
    local output="${2:-${input}.filtered}"
    local whitelist="${3:-$WHITELIST_FILE}"

    [[ ! -f "$whitelist" ]] && cp "$input" "$output" && return 0

    # 使用更简单的方式过滤：逐报告处理
    local temp_key_file=$(mktemp)
    local kept_reports=$(mktemp)

    # 提取所有键
    get_all_keys "$input" > "$temp_key_file"

    local whitelisted=0
    local kept=0

    # 逐报告处理
    awk -v whitelist="$whitelist" '
    BEGIN { in_report = 0; skip = 0; count = 0 }

    /^---\[.*\]---/ {
        # 保存前一条报告
        if (in_report && !skip) {
            for (i = 0; i < report_count; i++) {
                print report_lines[i]
            }
            kept++
        }
        if (in_report && skip) {
            whitelisted++
        }

        # 新报告
        key = substr($0, 5, index($0, "]---") - 5)
        in_report = 1
        report_count = 0
        report_lines[report_count++] = $0
        skip = 0

        # 检查白名单
        split(key, parts, ":")
        addr = parts[1]
        func1 = parts[2]
        func2 = parts[3]
        func_pair = func1 " / " func2

        # 精确匹配
        cmd = "grep -qF \"" func_pair "\" \"" whitelist "\" 2>/dev/null"
        if (system(cmd) == 0) {
            skip = 1
        }
        next
    }

    in_report {
        report_lines[report_count++] = $0
    }

    END {
        # 处理最后一条报告
        if (in_report && !skip) {
            for (i = 0; i < report_count; i++) {
                print report_lines[i]
            }
            kept++
        }
        if (in_report && skip) {
            whitelisted++
        }
        print "# Whitelisted: " whitelisted ", Kept: " kept > "/dev/stderr"
    }
    ' "$input" > "$output"

    rm -f "$temp_key_file" "$kept_reports"
}

# 添加条目到白名单
add_to_whitelist() {
    local entry="$1"
    local reason="${2:-No reason}"
    local whitelist="${3:-$WHITELIST_FILE}"

    # 确保目录存在
    local dir=$(dirname "$whitelist")
    mkdir -p "$dir"

    # 检查是否已存在
    if grep -qF "$entry" "$whitelist" 2>/dev/null; then
        echo "Entry already exists in whitelist"
        return 1
    fi

    # 追加条目
    echo "$entry # $reason" >> "$whitelist"
    echo "Added to whitelist: $entry"
}

# 从白名单删除条目
remove_from_whitelist() {
    local entry="$1"
    local whitelist="${2:-$WHITELIST_FILE}"

    # 创建临时文件
    local tmp="${whitelist}.tmp"

    # 排除匹配的行
    grep -vF "$entry" "$whitelist" > "$tmp" 2>/dev/null
    mv "$tmp" "$whitelist"

    echo "Removed from whitelist: $entry"
}

# 列出白名单内容
list_whitelist() {
    local whitelist="${1:-$WHITELIST_FILE}"

    [[ ! -f "$whitelist" ]] && echo "Whitelist not found: $whitelist" && return 1

    echo "=== KCSAN Whitelist ==="
    cat -n "$whitelist" | grep -v "^ *[0-9]* *#"
}

# 初始化默认白名单
init_whitelist() {
    local whitelist="${1:-$WHITELIST_FILE}"
    local dir=$(dirname "$whitelist")
    mkdir -p "$dir"

    cat > "$whitelist" << 'EOF'
# KCSAN 白名单配置
# 格式: function1 / function2 # 原因
#
# 匹配类型:
# 1. 精确函数对: tick_periodic / clock_settime # 原因
# 2. 通配符: tick_* / clock_* # 原因
# 3. 地址: ADDR:0xffffffff8260a280 # 原因
#
# 示例:

# 时间子系统 - 已知良性竞争
# tick_periodic / clock_settime # 时间更新竞争，实际不会造成问题

# 通配符示例
# tick_* / clock_* # 时间子系统相关

# 地址白名单
# ADDR:0xffffffff8260a280 # 时钟设备寄存器
EOF

    echo "Initialized whitelist at: $whitelist"
}
