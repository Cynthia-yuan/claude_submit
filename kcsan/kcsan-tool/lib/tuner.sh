#!/bin/bash
# KCSAN 调参模块
# 生成 KCSAN boot 参数和建议

# 生成 KCSAN boot 参数配置
generate_boot_params() {
    local output="${1:-output/kcsan.boot.conf}"

    cat > "$output" << 'EOF'
# KCSAN Boot 参数配置
# 使用方法: 将以下参数添加到内核命令行
# 例如: GRUB_CMDLINE_LINUX="... kcsan=1 ..."

# ===== 基础配置 =====
# 启用 KCSAN
kcsan=1

# ===== 去重配置 =====
# 报告去重时间窗口 (毫秒)
# 在此窗口内的相同访问只报告一次
# 默认值: 1000, 增大可减少重复报告
kcsan.report_once_in_ms=5000

# ===== 性能配置 =====
# KCSAN 条目概率 (0 - 10000, 其中 10000 = 100%)
# 降低此值可减少性能开销，但可能漏掉一些问题
# 默认值: 约 100-1000
kcsan.stall_wait=100

# ===== 跳过特定函数 =====
# 跳过对特定函数的监视
# 格式: kcsan.skip_watch=func1,func2,...
# 例如:
# kcsan.skip_watch=random_trusted_entropy

# ===== 禁用特定检测 =====
# 禁用对特定地址范围的检测
# 例如: kcsan.skip_access=0x1000-0x2000

# ===== 输出控制 =====
# 只报告一次 (不重复)
kcsan.report_once=1

EOF

    echo "Generated boot config: $output"
    echo ""
    echo "To apply these parameters, add them to your kernel command line."
    echo "For GRUB: edit /etc/default/grub and update GRUB_CMDLINE_LINUX"
    echo "Then run: update-grub && reboot"
}

# 分析报告并生成调参建议
analyze_and_suggest() {
    local input="$1"
    local output="${2:-output/tuning_suggestions.txt}"

    {
        echo "=== KCSAN 调参建议 ==="
        echo "Generated: $(date)"
        echo ""

        # 统计重复率
        local total_keys=$(get_all_keys "$input" | wc -l)
        local total_reports=$(grep -c "^---\[.*\]---" "$input")
        local dup_ratio=0

        if [[ $total_keys -gt 0 ]]; then
            dup_ratio=$((100 * (total_reports - total_keys) / total_reports))
        fi

        echo "=== 重复率分析 ==="
        echo "唯一问题数: $total_keys"
        echo "总报告数: $total_reports"
        echo "重复率: ${dup_ratio}%"

        if [[ $dup_ratio -gt 50 ]]; then
            echo ""
            echo "建议: 重复率较高，建议增加 report_once_in_ms"
            echo "  当前默认: 1000ms"
            echo "  建议值: 5000-10000ms"
            echo "  参数: kcsan.report_once_in_ms=10000"
        fi

        echo ""

        # 热点地址分析
        echo "=== 热点地址分析 ==="
        local hot_addr=$(grep -oE '\[[0-9a-fA-F]+:' "$input" 2>/dev/null | \
            sed 's/\[//;s/:$//' | \
            sort | uniq -c | sort -rn | head -5)

        if [[ -n "$hot_addr" ]]; then
            echo "最频繁的地址:"
            echo "$hot_addr"
            echo ""
            echo "如果某些地址持续误报，考虑添加地址白名单或使用 skip_access"
        fi

        echo ""

        # 热点函数分析
        echo "=== 热点函数分析 ==="
        awk -F: '
        /^\---\[.*\]---/ {
            key = substr($0, 5, index($0, "]---") - 5)
            split(key, parts, ":")
            if (length(parts) >= 3) {
                func3 = parts[3]
                funcs[func3]++
            }
        }
        END {
            for (f in funcs) {
                print funcs[f] " " f
            }
        }
        ' "$input" | sort -rn | head -10 | \
            awk '{print "  " $2 ": " $1 " 次"}'

        echo ""
        echo "如果某些函数持续误报，考虑:"
        echo "  1. 添加到白名单 (whitelist.txt)"
        echo "  2. 使用 kcsan.skip_watch 跳过"

        echo ""
        echo "=== 性能开销评估 ==="
        echo "如果 KCSAN 导致系统性能下降超过 20%，考虑:"
        echo "  1. 降低 stall_wait 值"
        echo "  2. 减少扫描频率"
        echo "  3. 使用 skip_watch 排除安全函数"

    } | tee "$output"
}

# 从白名单生成 skip_watch 参数
generate_skip_watch() {
    local whitelist="${1:-config/whitelist.txt}"

    [[ ! -f "$whitelist" ]] && echo "Whitelist not found: $whitelist" && return 1

    echo "# 从白名单生成的 skip_watch 参数"
    echo "# kcsan.skip_watch="

    local funcs=()
    while IFS='/' read -r func1 func2_rest; do
        [[ "$func1" =~ ^# ]] && continue
        [[ "$func1" =~ ^ADDR: ]] && continue
        [[ -z "$func1" ]] && continue

        func1=$(echo "$func1" | xargs)
        func1=${func1//\*/}  # 移除通配符

        [[ -n "$func1" ]] && funcs+=("$func1")

        func2=$(echo "$func2_rest" | awk '{print $1}' | xargs)
        func2=${func2//\*/}
        func2=${func2%%#*}  # 移除注释

        [[ -n "$func2" ]] && funcs+=("$func2")
    done < "$whitelist"

    # 去重并输出
    printf '%s\n' "${funcs[@]}" | sort -u | \
        awk 'NR==1 {printf "kcsan.skip_watch=%s", $0} NR>1 {printf ",%s", $0} END {print ""}'
}

# 生成完整的内核命令行建议
generate_cmdline() {
    local output="${1:-output/kernel_cmdline.txt}"

    {
        echo "# 建议的内核命令行参数"
        echo "# 添加到 GRUB_CMDLINE_LINUX 或直接在启动时指定"
        echo ""

        generate_skip_watch 2>/dev/null

        echo ""
        echo "kcsan=1"
        echo "kcsan.report_once_in_ms=5000"
        echo "kcsan.report_once=1"

    } | tee "$output"

    echo "Generated cmdline suggestions: $output"
}
