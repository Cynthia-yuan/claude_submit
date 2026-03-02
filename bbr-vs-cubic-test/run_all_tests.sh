#!/bin/bash
# 一键运行完整的 BBR vs CUBIC 对比测试
# 自动配置网络拥塞场景并运行性能测试

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 配置
TEST_DURATION="${TEST_DURATION:-30}"  # 每次测试时长（秒）
PARALLEL_STREAMS="${PARALLEL_STREAMS:-4}"  # 并发流数量
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-5201}"
RESULTS_DIR="${SCRIPT_DIR}/results"
LOG_DIR="${SCRIPT_DIR}/logs"

echo -e "${CYAN}${BOLD}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      BBR vs CUBIC 网络拥塞控制算法对比测试工具            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# 创建必要的目录
mkdir -p "$RESULTS_DIR"
mkdir -p "$LOG_DIR"

# 打印配置信息
print_config() {
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}测试配置:${NC}"
    echo -e "  测试时长:        ${GREEN}${TEST_DURATION} 秒${NC}"
    echo -e "  并发流数:        ${GREEN}${PARALLEL_STREAMS}${NC}"
    echo -e "  服务器地址:      ${GREEN}${SERVER_HOST}:${SERVER_PORT}${NC}"
    echo -e "  结果目录:        ${GREEN}${RESULTS_DIR}${NC}"
    echo -e "  日志目录:        ${GREEN}${LOG_DIR}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}[1/4] 检查系统依赖...${NC}"

    local missing_deps=()

    # 检查必要工具
    command -v iperf3 >/dev/null 2>&1 || missing_deps+=("iperf3")
    command -v jq >/dev/null 2>&1 || missing_deps+=("jq")
    command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}✗ 缺少依赖工具: ${missing_deps[*]}${NC}"
        echo ""
        echo "安装方法:"
        echo "  macOS:   brew install ${missing_deps[*]}"
        echo "  Ubuntu:  sudo apt-get install ${missing_deps[*]}"
        echo "  CentOS:  sudo yum install ${missing_deps[*]}"
        exit 1
    fi

    echo -e "${GREEN}✓ 所有依赖工具已安装${NC}"
}

# 检查 iperf3 服务器
check_iperf3_server() {
    echo ""
    echo -e "${BLUE}[2/4] 检查 iperf3 服务器状态...${NC}"

    if iperf3 -c "$SERVER_HOST" -p "$SERVER_PORT" -t 1 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ iperf3 服务器已就绪${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ iperf3 服务器未运行${NC}"
        echo ""
        echo "请先在另一个终端启动 iperf3 服务器:"
        echo -e "${GREEN}  iperf3 -s -p $SERVER_PORT${NC}"
        echo ""
        echo "或者输入 'local' 在本地启动服务器（需要新建终端）"
        echo -n "是否继续? (y/n/local): "

        read -r response
        case "$response" in
            y|Y|yes|YES)
                echo "继续测试..."
                ;;
            local|LOCAL)
                echo -e "${YELLOW}请在另一个终端运行: iperf3 -s -p $SERVER_PORT${NC}"
                echo -n "按 Enter 确认服务器已启动..."
                read -r
                ;;
            *)
                echo "测试已取消"
                exit 0
                ;;
        esac
    fi
}

# 选择拥塞场景
select_congestion_scenario() {
    echo ""
    echo -e "${BLUE}[3/4] 选择网络拥塞场景${NC}"
    echo ""
    echo "可用的测试场景:"
    echo "  ${GREEN}1${NC} - 轻度拥塞    (延迟 50ms,   丢包 0.5%)"
    echo "  ${GREEN}2${NC} - 中度拥塞    (延迟 100ms,  丢包 2%)"
    echo "  ${GREEN}3${NC} - 重度拥塞    (延迟 200ms,  丢包 5%)"
    echo "  ${GREEN}4${NC} - 缓冲区膨胀  (延迟 150ms,  限速 1Mbps)"
    echo "  ${GREEN}5${NC} - 突发拥塞    (变化延迟和丢包)"
    echo "  ${GREEN}6${NC} - 长肥管道    (高延迟, 大带宽)"
    echo "  ${GREEN}0${NC} - 无拥塞      (正常网络)"
    echo "  ${GREEN}a${NC} - 全部场景    (运行所有测试)"
    echo ""
    echo -n "请选择 (0-6, a): "

    read -r scenario_choice

    case "$scenario_choice" in
        0|1|2|3|4|5|6)
            SELECTED_SCENARIOS=($scenario_choice)
            ;;
        a|A)
            SELECTED_SCENARIOS=(1 2 3 4 5 6)
            ;;
        *)
            echo -e "${RED}无效选择，默认使用场景 2${NC}"
            SELECTED_SCENARIOS=(2)
            ;;
    esac

    echo -e "${GREEN}✓ 已选择场景: ${SELECTED_SCENARIOS[*]}${NC}"
}

# 运行单个场景的测试
run_scenario_test() {
    local scenario=$1
    local scenario_name=""

    case "$scenario" in
        0) scenario_name="无拥塞" ;;
        1) scenario_name="轻度拥塞" ;;
        2) scenario_name="中度拥塞" ;;
        3) scenario_name="重度拥塞" ;;
        4) scenario_name="缓冲区膨胀" ;;
        5) scenario_name="突发拥塞" ;;
        6) scenario_name="长肥管道" ;;
    esac

    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  测试场景: ${scenario_name}${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local scenario_suffix="scenario${scenario}_${timestamp}"

    # 配置拥塞场景（除了场景0）
    if [ "$scenario" != "0" ]; then
        echo -e "${BLUE}配置网络拥塞场景...${NC}"

        # 检查是否是 macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${YELLOW}警告: macOS 不支持 tc (traffic control)，将跳过网络配置${NC}"
            echo "建议在 Linux 环境或虚拟机中运行完整的拥塞测试"
        else
            if [ "$EUID" -ne 0 ]; then
                echo -e "${YELLOW}警告: 需要 root 权限配置网络拥塞${NC}"
                echo "使用 sudo 重新运行..."
                sudo "$SCRIPT_DIR/scripts/setup_congestion.sh" "$scenario"
            else
                "$SCRIPT_DIR/scripts/setup_congestion.sh" "$scenario"
            fi
        fi
    fi

    # 运行 CUBIC 测试
    echo ""
    echo -e "${BLUE}运行 CUBIC 测试...${NC}"
    export TEST_DURATION="$TEST_DURATION"
    export PARALLEL_STREAMS="$PARALLEL_STREAMS"
    export SERVER_HOST="$SERVER_HOST"
    export SERVER_PORT="$SERVER_PORT"

    if ! bash "$SCRIPT_DIR/scripts/run_test.sh"; then
        echo -e "${RED}✗ CUBIC 测试失败${NC}"
        return 1
    fi

    # 重命名结果文件
    local latest_cubic=$(ls -t "$RESULTS_DIR"/cubic_test_*.json 2>/dev/null | head -1)
    if [ -n "$latest_cubic" ]; then
        mv "$latest_cubic" "$RESULTS_DIR/cubic_${scenario_suffix}.json"
        echo -e "${GREEN}✓ CUBIC 结果: cubic_${scenario_suffix}.json${NC}"
    fi

    sleep 2  # 等待网络稳定

    # 运行 BBR 测试
    echo ""
    echo -e "${BLUE}运行 BBR 测试...${NC}"
    if ! bash "$SCRIPT_DIR/scripts/run_test.sh"; then
        echo -e "${RED}✗ BBR 测试失败${NC}"
        return 1
    fi

    # 重命名结果文件
    local latest_bbr=$(ls -t "$RESULTS_DIR"/bbr_test_*.json 2>/dev/null | head -1)
    if [ -n "$latest_bbr" ]; then
        mv "$latest_bbr" "$RESULTS_DIR/bbr_${scenario_suffix}.json"
        echo -e "${GREEN}✓ BBR 结果: bbr_${scenario_suffix}.json${NC}"
    fi

    # 清除网络配置
    if [ "$scenario" != "0" ] && [[ "$OSTYPE" != "darwin"* ]]; then
        echo ""
        echo -e "${BLUE}清除网络拥塞配置...${NC}"
        if [ "$EUID" -eq 0 ]; then
            "$SCRIPT_DIR/scripts/setup_congestion.sh" clear 2>/dev/null || true
        else
            sudo "$SCRIPT_DIR/scripts/setup_congestion.sh" clear 2>/dev/null || true
        fi
    fi

    # 分析结果
    echo ""
    echo -e "${BLUE}分析测试结果...${NC}"
    python3 "$SCRIPT_DIR/scripts/analyze_results.py" \
        --bbr-file "$RESULTS_DIR/bbr_${scenario_suffix}.json" \
        --cubic-file "$RESULTS_DIR/cubic_${scenario_suffix}.json"

    echo -e "${GREEN}✓ 场景 ${scenario} 测试完成${NC}"
}

# 生成总结报告
generate_summary_report() {
    echo ""
    echo -e "${BLUE}[4/4] 生成总结报告...${NC}"

    local summary_file="$RESULTS_DIR/summary_report.txt"

    cat > "$summary_file" << EOF
═══════════════════════════════════════════════════════════
  BBR vs CUBIC 网络拥塞控制算法对比测试总结报告
═══════════════════════════════════════════════════════════

测试时间: $(date)
测试配置:
  - 测试时长: ${TEST_DURATION} 秒
  - 并发流数: ${PARALLEL_STREAMS}
  - 服务器: ${SERVER_HOST}:${SERVER_PORT}

测试场景:
  ${SELECTED_SCENARIOS[*]}

═══════════════════════════════════════════════════════════

EOF

    # 分析所有场景的结果
    for scenario in "${SELECTED_SCENARIOS[@]}"; do
        local scenario_results=$(ls -t "$RESULTS_DIR"/*_scenario${scenario}_*.json 2>/dev/null | head -2)

        if [ -n "$scenario_results" ]; then
            echo "" >> "$summary_file"
            echo "场景 ${scenario}:" >> "$summary_file"
            echo "--------" >> "$summary_file"

            # 运行分析
            local cubic_file=$(ls -t "$RESULTS_DIR"/cubic_scenario${scenario}_*.json 2>/dev/null | head -1)
            local bbr_file=$(ls -t "$RESULTS_DIR"/bbr_scenario${scenario}_*.json 2>/dev/null | head -1)

            if [ -n "$cubic_file" ] && [ -n "$bbr_file" ]; then
                python3 "$SCRIPT_DIR/scripts/analyze_results.py" \
                    --bbr-file "$bbr_file" \
                    --cubic-file "$cubic_file" \
                    >> "$summary_file" 2>&1 || true
            fi
        fi
    done

    echo "" >> "$summary_file"
    echo "═══════════════════════════════════════════════════════════" >> "$summary_file"

    echo -e "${GREEN}✓ 总结报告: $summary_file${NC}"
}

# 主流程
main() {
    print_config
    check_dependencies
    check_iperf3_server
    select_congestion_scenario

    echo ""
    echo -e "${CYAN}${BOLD}开始测试...${NC}"

    # 运行每个选定的场景
    for scenario in "${SELECTED_SCENARIOS[@]}"; do
        run_scenario_test "$scenario"
    done

    # 生成总结报告
    if [ ${#SELECTED_SCENARIOS[@]} -gt 1 ]; then
        generate_summary_report
    fi

    # 完成提示
    echo ""
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  所有测试完成！${NC}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "查看结果文件: ${BLUE}ls -la $RESULTS_DIR/${NC}"
    echo -e "查看总结报告: ${BLUE}cat $RESULTS_DIR/summary_report.txt${NC}"
    echo ""
}

# 运行主流程
main "$@"
