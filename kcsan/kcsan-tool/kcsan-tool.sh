#!/bin/bash
# KCSAN 误报率降低工具
# 主入口

set -e

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/extract.sh"
source "$SCRIPT_DIR/lib/dedup.sh"
source "$SCRIPT_DIR/lib/whitelist.sh"
source "$SCRIPT_DIR/lib/report.sh"
source "$SCRIPT_DIR/lib/tuner.sh"

# 默认配置
INPUT="${INPUT:-dmesg}"
WORKDIR="${WORKDIR:-output}"
WHITELIST="$SCRIPT_DIR/config/whitelist.txt"

# 显示帮助
show_help() {
    cat << EOF
KCSAN 误报率降低工具

用法: $(basename "$0") [命令] [选项]

命令:
  run        运行完整流程 (默认)
  extract    仅提取报告
  dedup      仅去重
  whitelist  管理白名单
  report     生成统计报告
  tune       生成调参建议

选项:
  -i FILE    输入文件 (默认: dmesg)
  -o DIR     输出目录 (默认: output)
  -w FILE    白名单文件
  -v         详细输出
  -h         显示帮助

白名单管理:
  $(basename "$0") whitelist add "func1 / func2" "原因"
  $(basename "$0") whitelist remove "func1 / func2"
  $(basename "$0") whitelist list
  $(basename "$0") whitelist init

示例:
  $(basename "$0") run -i dmesg
  $(basename "$0") whitelist add "tick_periodic / clock_settime" "时间相关"
  $(basename "$0") report -i output/final.txt

EOF
}

# 初始化工作目录
init_workdir() {
    mkdir -p "$WORKDIR"/{raw,deduped,filtered,final}
    mkdir -p "$SCRIPT_DIR/config"

    # 初始化白名单
    if [[ ! -f "$WHITELIST" ]]; then
        init_whitelist "$WHITELIST"
    fi
}

# 完整流程
run_full() {
    echo "=== KCSAN 误报率降低工具 ==="
    echo "Input: $INPUT"
    echo "Workdir: $WORKDIR"
    echo ""

    # 1. 提取报告
    echo "[1/6] Extracting KCSAN reports..."
    extract_reports "$INPUT" > "$WORKDIR/raw/reports.txt"
    local raw_count=$(count_reports "$WORKDIR/raw/reports.txt")
    echo "  Found $raw_count reports"
    echo ""

    # 2. 精确去重
    echo "[2/6] Exact deduplication..."
    exact_dedup "$WORKDIR/raw/reports.txt" > "$WORKDIR/deduped/reports.txt"
    local deduped_count=$(count_reports "$WORKDIR/deduped/reports.txt")
    echo "  After dedup: $deduped_count reports (removed $((raw_count - deduped_count)) duplicates)"
    echo ""

    # 3. 模糊去重统计
    echo "[3/6] Fuzzy deduplication analysis..."
    fuzzy_dedup_stats "$WORKDIR/deduped/reports.txt" > "$WORKDIR/deduped/fuzzy_stats.txt"
    echo "  Fuzzy stats saved to: $WORKDIR/deduped/fuzzy_stats.txt"
    head -5 "$WORKDIR/deduped/fuzzy_stats.txt" | sed 's/^/    /'
    echo ""

    # 4. 白名单过滤
    echo "[4/6] Applying whitelist..."
    if [[ -f "$WHITELIST" ]]; then
        filter_whitelist "$WORKDIR/deduped/reports.txt" "$WORKDIR/filtered/reports.txt" "$WHITELIST"
        local filtered_count=$(count_reports "$WORKDIR/filtered/reports.txt")
        echo "  After whitelist: $filtered_count reports (whitelisted $((deduped_count - filtered_count)))"
    else
        cp "$WORKDIR/deduped/reports.txt" "$WORKDIR/filtered/reports.txt"
        local filtered_count=$deduped_count
        echo "  No whitelist, skipping..."
    fi
    echo ""

    # 5. 生成最终报告
    echo "[5/6] Generating reports..."
    cp "$WORKDIR/filtered/reports.txt" "$WORKDIR/final/reports.txt"
    generate_stats "$WORKDIR/final/reports.txt" "$WORKDIR/final/stats.txt"
    generate_summary "$WORKDIR/final/reports.txt" "$WORKDIR/final/summary.txt"
    echo "  Reports saved to: $WORKDIR/final/"
    echo ""

    # 6. 生成调参建议
    echo "[6/6] Generating tuning suggestions..."
    analyze_and_suggest "$WORKDIR/final/reports.txt" "$WORKDIR/final/tuning.txt"
    generate_boot_params "$WORKDIR/final/kcsan.boot.conf"
    generate_cmdline "$WORKDIR/final/cmdline.txt"
    echo ""

    # 汇总
    echo "=== Summary ==="
    echo "  Raw reports:      $raw_count"
    echo "  After dedup:      $deduped_count"
    echo "  After whitelist:  $filtered_count"
    if [[ $raw_count -gt 0 ]]; then
        echo "  Reduction:        $((100 * (raw_count - filtered_count) / raw_count))%"
    else
        echo "  Reduction:        N/A"
    fi
    echo ""
    echo "Output directory: $WORKDIR/final/"
}

# 仅提取
run_extract() {
    init_workdir
    echo "Extracting KCSAN reports from: $INPUT"
    extract_reports "$INPUT" > "$WORKDIR/raw/reports.txt"
    local count=$(count_reports "$WORKDIR/raw/reports.txt")
    echo "Extracted $count reports to: $WORKDIR/raw/reports.txt"
}

# 仅去重
run_dedup() {
    local input="${1:-$WORKDIR/raw/reports.txt}"
    local output="${2:-$WORKDIR/deduped/reports.txt}"

    echo "Deduplicating: $input"
    exact_dedup "$input" > "$output"

    local before=$(count_reports "$input")
    local after=$(count_reports "$output")
    echo "Before: $before, After: $after (removed $((before - after)) duplicates)"
    echo "Output: $output"
}

# 白名单管理
run_whitelist() {
    local action="$1"
    shift || true

    case "$action" in
        add)
            local entry="$1"
            local reason="${2:-No reason}"
            add_to_whitelist "$entry" "$reason" "$WHITELIST"
            ;;
        remove)
            local entry="$1"
            remove_from_whitelist "$entry" "$WHITELIST"
            ;;
        list)
            list_whitelist "$WHITELIST"
            ;;
        init)
            init_whitelist "$WHITELIST"
            ;;
        *)
            echo "Usage: $0 whitelist {add|remove|list|init} [args]"
            exit 1
            ;;
    esac
}

# 生成报告
run_report() {
    local input="$WORKDIR/final/reports.txt"

    if [[ ! -f "$input" ]]; then
        echo "Input file not found: $input"
        echo "Run 'kcsan-tool.sh run' first to generate reports"
        exit 1
    fi

    generate_stats "$input" "$WORKDIR/final/stats.txt"
    generate_summary "$input" "$WORKDIR/final/summary.txt"
    echo "Reports generated:"
    echo "  Stats:   $WORKDIR/final/stats.txt"
    echo "  Summary: $WORKDIR/final/summary.txt"
}

# 调参建议
run_tune() {
    local input="$WORKDIR/final/reports.txt"

    if [[ ! -f "$input" ]]; then
        echo "Input file not found: $input"
        echo "Run 'kcsan-tool.sh run' first to generate reports"
        exit 1
    fi

    analyze_and_suggest "$input" "$WORKDIR/final/tuning.txt"
    generate_boot_params "$WORKDIR/final/kcsan.boot.conf"
    generate_cmdline "$WORKDIR/final/cmdline.txt"
    echo ""
    echo "Tuning files generated:"
    echo "  Suggestions: $WORKDIR/final/tuning.txt"
    echo "  Boot config:  $WORKDIR/final/kcsan.boot.conf"
    echo "  Cmdline:      $WORKDIR/final/cmdline.txt"
}

# 主函数
main() {
    local command="run"
    local cmd_input=""
    local cmd_workdir=""

    # 获取命令 (第一个非选项参数)
    while [[ $# -gt 0 ]]; do
        case "$1" in
            run|extract|dedup|whitelist|report|tune|help|--help|-h)
                command="$1"
                shift
                break
                ;;
            *)
                # 不是已知命令，跳过（可能是选项或其参数）
                shift
                ;;
        esac
    done

    # 重置 OPTIND 以便 getopts 正确处理剩余参数
    OPTIND=1

    # 解析选项
    while getopts "i:o:w:vh" opt; do
        case "$opt" in
            i) cmd_input="$OPTARG" ;;
            o) cmd_workdir="$OPTARG" ;;
            w) WHITELIST="$OPTARG" ;;
            v) set -x ;;
            h) show_help; exit 0 ;;
            *) show_help; exit 1 ;;
        esac
    done
    shift $((OPTIND-1))

    # 使用命令行参数或默认值
    INPUT="${cmd_input:-$INPUT}"
    WORKDIR="${cmd_workdir:-$WORKDIR}"

    # 执行命令
    case "$command" in
        run)
            init_workdir
            run_full
            ;;
        extract)
            init_workdir
            run_extract
            ;;
        dedup)
            init_workdir
            run_dedup "$@"
            ;;
        whitelist)
            run_whitelist "$@"
            ;;
        report)
            run_report
            ;;
        tune)
            run_tune
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
