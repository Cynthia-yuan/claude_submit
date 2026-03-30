#!/bin/bash
# KCSAN 报告提取模块
# 从 dmesg 输出中提取 KCSAN 报告

# 提取单条 KCSAN 报告的关键信息
# 输出格式: 每条报告以 ---[key]--- 开头，key 用于去重
# key 格式: addr:func1:func2
extract_reports() {
    local input="$1"

    awk '
    BEGIN { in_report = 0; report_content = "" }

    # 检测报告开始
    /^==================================================================$/ {
        if (in_report && report_content != "") {
            # 保存前一条报告
            print report_content
            report_content = ""
        }
        in_report = 1
        next
    }

    # 解析 BUG 行，提取函数名
    in_report && /^BUG: KCSAN:/ {
        # 提取 "in func1 / func2" 格式
        for (i = 1; i <= NF; i++) {
            if ($i == "in") {
                func1 = $(i+1)
                # func2 在 "/" 后面
                for (j = i+2; j <= NF; j++) {
                    if ($(j) == "/") {
                        func2 = $(j+1)
                        break
                    }
                }
                break
            }
        }
        report_content = report_content $0 "\n"
        next
    }

    # 解析地址行
    in_report && /^write to 0x/ {
        addr = $3
        access_type = "write"
        size = $5
        report_content = report_content $0 "\n"
        next
    }

    in_report && /^read to 0x/ {
        addr = $3
        access_type = "read"
        size = $5
        report_content = report_content $0 "\n"
        next
    }

    # 调用栈行
    in_report && /^(write|read) to 0x/ {
        report_content = report_content $0 "\n"
        next
    }

    in_report && /^[ \t]/ {
        # 调用栈内容行（以空格/制表符开头）
        report_content = report_content $0 "\n"
        next
    }

    # 检测报告结束
    in_report && /^Report [0-9]+ generated at:/ {
        timestamp = $0
        # 生成去重键: addr:func1:func2
        key = addr ":" func1 ":" func2

        # 输出报告头标记
        print "---[" key "]---"
        print report_content $0
        print "=================================================================="

        in_report = 0
        report_content = ""
        next
    }

    # 报告内容
    in_report {
        report_content = report_content $0 "\n"
        next
    }
    ' "$input"
}

# 统计报告数量
count_reports() {
    local input="$1"
    grep -c "^---\[.*\]---" "$input" 2>/dev/null || echo "0"
}

# 从提取的报告中获取所有去重键
get_all_keys() {
    local input="$1"
    grep -oE '\[[^\]]+\]---' "$input" | sed 's/\[//;s/\]---//'
}
