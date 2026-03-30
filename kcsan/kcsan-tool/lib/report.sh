#!/bin/bash
# KCSAN 报告生成模块
# 生成统计信息和格式化报告

# 生成统计信息
generate_stats() {
    local input="$1"
    local output="${2:-${input}.stats}"

    {
        echo "=== KCSAN Report Statistics ==="
        echo ""
        echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Input file: $input"
        echo ""

        # 统计报告数量
        local count=$(grep -c "^---\[.*\]---" "$input" 2>/dev/null || echo "0")
        echo "Total reports: $count"
        echo ""

        # 按函数对统计
        echo "=== Top Function Pairs ==="
        grep -oE '\[[^\]]+\]---' "$input" 2>/dev/null | \
            sed 's/\[//;s/\]---//' | \
            awk -F: '{print $2 "/" $3}' | \
            sort | uniq -c | sort -rn | head -20
        echo ""

        # 按地址统计
        echo "=== Top Addresses ==="
        grep -oE '\[[0-9a-fA-F]+:' "$input" 2>/dev/null | \
            sed 's/\[//;s/:$//' | \
            sort | uniq -c | sort -rn | head -10
        echo ""

        # 访问类型统计
        echo "=== Access Types ==="
        grep -c "write to" "$input" 2>/dev/null || echo "0"
        echo "Write operations: $(grep -c "write to" "$input" 2>/dev/null || echo "0")"
        echo "Read operations: $(grep -c "read to" "$input" 2>/dev/null || echo "0")"
        echo ""

    } | tee "$output"
}

# 生成人类可读的摘要报告
generate_summary() {
    local input="$1"
    local output="${2:-${input}.summary}"

    {
        echo "=== KCSAN Report Summary ==="
        echo ""
        echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""

        # 提取每条报告的关键信息
        awk '
        /^---\[.*\]---/ {
            if (report != "") {
                print report
                print ""
            }
            key = substr($0, 5, index($0, "]---") - 5)
            split(key, parts, ":")
            addr = parts[1]
            func1 = parts[2]
            func2 = parts[3]

            report = "[" ++count "] " func1 " / " func2
            report = report "\n  Address: " addr
            next
        }

        /^write to/ {
            report = report "\n  Access: WRITE " $3 " (" $5 ")"
            next
        }

        /^read to/ {
            report = report "\n  Access: READ " $3 " (" $5 ")"
            next
        }

        END {
            if (report != "") {
                print report
                print ""
            }
            print "Total: " count " reports"
        }
        ' "$input"

    } | tee "$output"
}

# 生成 JSON 格式报告 (用于工具集成)
generate_json() {
    local input="$1"
    local output="${2:-${input}.json}"

    echo "{"
    echo "  \"generated_at\": \"$(date -Iseconds)\","
    echo "  \"reports\": ["

    local first=true
    local count=0

    while IFS= read -r line; do
        if [[ $line =~ ^---\[([^\]]+)\]--- ]]; then
            [[ $first == false ]] && echo ","
            first=false

            local key="${BASH_REMATCH[1]}"
            IFS=':' read -ra PARTS <<< "$key"
            local addr="${PARTS[0]}"
            local func1="${PARTS[1]}"
            local func2="${PARTS[2]}"

            printf '    {'
            printf ' "id": %d,' $((++count))
            printf ' "address": "%s",' "$addr"
            printf ' "func1": "%s",' "$func1"
            printf ' "func2": "%s",' "$func2"
            printf ' "key": "%s"' "$key"
            printf ' }'
        fi
    done < "$input"

    echo ""
    echo "  ],"
    echo "  \"total\": $count"
    echo "}" > "$output"
}

# 生成 KCSAN 抑制文件 (用于编译时排除)
generate_suppress() {
    local input="$1"
    local output="${2:-kcsan.suppress}"

    {
        echo "# KCSAN 抑制文件"
        echo "# 用于抑制特定函数的 KCSAN 检测"
        echo "# 生成时间: $(date)"
        echo ""
        echo "# 格式: kcsan_skip_watch=func_name"
        echo ""

        # 从白名单提取函数名
        grep -v "^#" "${WHITELIST_FILE:-config/whitelist.txt}" 2>/dev/null | \
            grep -v "^ADDR:" | \
            while IFS='/' read -r func1 func2_rest; do
                func1=$(echo "$func1" | xargs)
                [[ -n "$func1" ]] && echo "kcsan_skip_watch=${func1}"

                func2=$(echo "$func2_rest" | awk '{print $1}' | xargs)
                [[ -n "$func2" ]] && echo "kcsan_skip_watch=${func2}"
            done

    } > "$output"

    echo "Generated suppress file: $output"
}

# 生成 diff 报告 (比较两次运行的差异)
generate_diff() {
    local old="$1"
    local new="$2"
    local output="${3:-diff.txt}"

    {
        echo "=== KCSAN Report Diff ==="
        echo "Old: $old"
        echo "New: $new"
        echo "Date: $(date)"
        echo ""

        # 新增的报告
        echo "=== New Reports (in new, not in old) ==="
        comm -13 <(get_all_keys "$old" | sort) \
                 <(get_all_keys "$new" | sort) | \
            while read -r key; do
                echo "  + $key"
            done
        echo ""

        # 消失的报告
        echo "=== Fixed Reports (in old, not in new) ==="
        comm -23 <(get_all_keys "$old" | sort) \
                 <(get_all_keys "$new" | sort) | \
            while read -r key; do
                echo "  - $key"
            done
        echo ""

        # 统计
        local old_count=$(count_reports "$old")
        local new_count=$(count_reports "$new")
        echo "Old count: $old_count"
        echo "New count: $new_count"
        echo "Change: $((new_count - old_count))"

    } | tee "$output"
}

# 打印单条报告详情
show_report() {
    local input="$1"
    local report_id="$2"

    awk -v id="$report_id" '
    BEGIN { count = 0; in_target = 0 }
    /^---\[.*\]---/ {
        count++
        if (count == id) {
            in_target = 1
            print $0
        } else {
            in_target = 0
        }
        next
    }
    in_target { print }
    ' "$input"
}
