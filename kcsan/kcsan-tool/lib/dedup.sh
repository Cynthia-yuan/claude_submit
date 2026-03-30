#!/bin/bash
# KCSAN 报告去重模块
# 支持精确去重和模糊去重

# 精确去重: 基于 addr:func1:func2 的唯一键
# 输入: extract.sh 输出的报告
# 输出: 去重后的报告
exact_dedup() {
    local input="$1"

    awk '
    BEGIN { dup_count = 0 }

    /^---\[.*\]---/ {
        # 提取 key
        key = substr($0, 5, index($0, "]---") - 5)

        if (!seen[key]++) {
            # 第一次见到这个 key，保留
            print $0
            in_report = 1
        } else {
            # 重复报告，跳过
            in_report = 0
            dup_count++
        }
        next
    }

    in_report { print }
    in_report && /^==================================================================$/ { in_report = 0 }

    END {
        if (dup_count > 0) {
            print "# Exact duplicates removed: " dup_count > "/dev/stderr"
        }
    }
    ' "$input"
}

# 模糊去重: 显示相同函数对的报告统计
# 用于识别可能是同一类 bug 的报告
fuzzy_dedup_stats() {
    local input="$1"

    # 提取 func1:func2 并统计
    grep -oE '\[[^\]]+\]---' "$input" | \
        sed 's/\[//;s/\]---//' | \
        awk -F: '{print $2 ":" $3}' | \
        sort | uniq -c | sort -rn
}

# 模糊去重: 按函数对分组
fuzzy_dedup_group() {
    local input="$1"

    # 为每个函数对创建单独的文件
    local func_pair
    local output_dir="${2:-output/fuzzy_groups}"

    mkdir -p "$output_dir"

    grep -oE '\[[^\]]+\]---' "$input" | \
        sed 's/\[//;s/\]---//' | \
        awk -F: '{print $2 ":" $3}' | \
        sort -u | \
    while read -r func_pair; do
        # 替换 / 为 __ 避免文件名问题
        local safe_name=$(echo "$func_pair" | sed 's/\//__/g')
        awk -v pair="$func_pair" '
            /^---\[.*\]---/ {
                key = substr($0, 5, index($0, "]---") - 5)
                if (index(key, pair) > 0) {
                    in_match = 1
                } else {
                    in_match = 0
                }
            }
            in_match { print }
        ' "$input" > "$output_dir/group_${safe_name}.txt"
    done

    echo "Fuzzy groups saved to: $output_dir"
}

# 合并相似的报告 (相同函数对)
# 保留每组中的第一条报告
fuzzy_dedup_merge() {
    local input="$1"

    awk '
    BEGIN { dup_count = 0 }

    /^---\[.*\]---/ {
        # 提取 key
        full_key = substr($0, 5, index($0, "]---") - 5)
        # 生成模糊键 (只包含函数对)
        split(full_key, parts, ":")
        fuzzy_key = parts[2] ":" parts[3]

        if (!seen_fuzzy[fuzzy_key]++) {
            # 该函数对第一次出现，保留
            print $0
            in_report = 1
        } else {
            in_report = 0
            dup_count++
        }
        next
    }

    in_report { print }
    in_report && /^==================================================================$/ { in_report = 0 }

    END {
        if (dup_count > 0) {
            print "# Fuzzy duplicates removed: " dup_count > "/dev/stderr"
        }
    }
    ' "$input"
}
