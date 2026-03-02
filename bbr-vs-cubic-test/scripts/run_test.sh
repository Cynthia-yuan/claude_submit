#!/bin/bash
# BBR vs CUBIC 性能对比测试脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数
TEST_DURATION="${TEST_DURATION:-60}"  # 测试时长（秒）
PARALLEL_STREAMS="${PARALLEL_STREAMS:-4}"  # 并发流数量
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"  # iperf3 服务器地址
SERVER_PORT="${SERVER_PORT:-5201}"  # iperf3 服务器端口
RESULTS_DIR="$(dirname "$0")/../results"
LOG_DIR="$(dirname "$0")/../logs"

# 创建必要的目录
mkdir -p "$RESULTS_DIR"
mkdir -p "$LOG_DIR"

echo -e "${GREEN}=== BBR vs CUBIC 性能对比测试 ===${NC}"
echo "测试时长: ${TEST_DURATION}秒"
echo "并发流数: ${PARALLEL_STREAMS}"
echo "服务器: ${SERVER_HOST}:${SERVER_PORT}"
echo ""

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}检查依赖工具...${NC}"

    # 检查 iperf3
    if ! command -v iperf3 &> /dev/null; then
        echo -e "${RED}错误: iperf3 未安装${NC}"
        echo "安装方法:"
        echo "  macOS: brew install iperf3"
        echo "  Ubuntu/Debian: sudo apt-get install iperf3"
        echo "  CentOS/RHEL: sudo yum install iperf3"
        exit 1
    fi

    # 检查 sysctl (Linux) 或 sysctl (macOS)
    if ! command -v sysctl &> /dev/null; then
        echo -e "${RED}错误: sysctl 未找到${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ 所有依赖工具已安装${NC}"
}

# 获取当前拥塞控制算法
get_current_congestion_control() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sysctl net.inet.tcp.cc.algorithm | awk '{print $2}'
    else
        # Linux
        sysctl -n net.ipv4.tcp_congestion_control
    fi
}

# 设置拥塞控制算法
set_congestion_control() {
    local algorithm=$1

    echo -e "${BLUE}设置拥塞控制算法为: $algorithm${NC}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if sysctl net.inet.tcp.cc.algorithm="$algorithm" 2>/dev/null; then
            echo -e "${GREEN}✓ 已设置为 $algorithm${NC}"
        else
            echo -e "${RED}错误: 无法设置 $algorithm (可能不支持)${NC}"
            echo "可用的算法: $(sysctl -a | grep cc.algorithm | grep -v ':' | cut -d. -f5)"
            return 1
        fi
    else
        # Linux
        if sudo sysctl -w net.ipv4.tcp_congestion_control="$algorithm" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ 已设置为 $algorithm${NC}"
        else
            echo -e "${RED}错误: 无法设置 $algorithm (可能不支持或需要 root 权限)${NC}"
            echo "可用的算法: $(cat /proc/sys/net/ipv4/tcp_available_congestion_control)"
            return 1
        fi
    fi

    # 验证设置
    sleep 1
    local current=$(get_current_congestion_control)
    echo "当前算法: $current"
}

# 运行单次测试
run_single_test() {
    local algorithm=$1
    local test_name=$2
    local output_file="${RESULTS_DIR}/${test_name}.json"
    local log_file="${LOG_DIR}/${test_name}.log"

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}运行测试: $test_name (${algorithm})${NC}"
    echo -e "${BLUE}========================================${NC}"

    # 设置算法
    if ! set_congestion_control "$algorithm"; then
        echo -e "${RED}跳过测试: $algorithm${NC}"
        return 1
    fi

    # 运行 iperf3 测试
    echo "运行 iperf3 测试..."
    iperf3 -c "$SERVER_HOST" \
        -p "$SERVER_PORT" \
        -t "$TEST_DURATION" \
        -P "$PARALLEL_STREAMS" \
        -J \
        -w 1M \
        --get-server-output \
        > "$output_file" 2>&1

    # 检查结果
    if [ $? -eq 0 ]; then
        # 提取关键指标
        local throughput=$(jq -r '.end.sum_received.bits_per_second' "$output_file" | awk '{printf "%.2f", $1/1000000000}')
        local retransmits=$(jq -r '.end.sum_sent.retransmits' "$output_file")
        local avg_rtt=$(jq -r '(.end.streams[] | select(.receiver != null) | .receiver.mean_rtt // 0) | add / (length | tonumber + 0.001)' "$output_file" | awk '{printf "%.2f", $1/1000}')

        echo -e "${GREEN}✓ 测试完成${NC}"
        echo "  吞吐量: ${throughput} Gbps"
        echo "  重传次数: $retransmits"
        echo "  平均 RTT: ${avg_rtt} ms"
        echo "  结果保存至: $output_file"
    else
        echo -e "${RED}✗ 测试失败${NC}"
        cat "$log_file"
        return 1
    fi
}

# 生成测试报告
generate_report() {
    local report_file="${RESULTS_DIR}/report.txt"

    echo ""
    echo -e "${GREEN}生成测试报告...${NC}"

    cat > "$report_file" << 'EOF'
========================================
BBR vs CUBIC 性能对比测试报告
========================================
测试时间: $(date)
测试时长: ${TEST_DURATION}秒
并发流数: ${PARALLEL_STREAMS}

EOF

    # 遍历所有结果文件
    for result_file in "${RESULTS_DIR}"/*.json; do
        if [ -f "$result_file" ]; then
            local test_name=$(basename "$result_file" .json)
            local algorithm=$(echo "$test_name" | grep -oE '(cubic|bbr)' | tr '[:lower:]' '[:upper:]')

            echo "" >> "$report_file"
            echo "--- ${test_name} ---" >> "$report_file"

            if jq empty "$result_file" 2>/dev/null; then
                local throughput=$(jq -r '.end.sum_received.bits_per_second' "$result_file" | awk '{printf "%.2f Mbps", $1/1000000}')
                local retransmits=$(jq -r '.end.sum_sent.retransmits' "$result_file")
                local avg_rtt=$(jq -r '(.end.streams[] | select(.receiver != null) | .receiver.mean_rtt // 0) | add / (length | tonumber + 0.001)' "$result_file" | awk '{printf "%.2f ms", $1/1000}')

                echo "吞吐量: $throughput" >> "$report_file"
                echo "重传次数: $retransmits" >> "$report_file"
                echo "平均 RTT: $avg_rtt" >> "$report_file"
            else
                echo "结果文件损坏或无效" >> "$report_file"
            fi
        fi
    done

    echo "" >> "$report_file"
    echo "========================================" >> "$report_file"

    echo -e "${GREEN}✓ 报告已生成: $report_file${NC}"
}

# 主测试流程
main() {
    check_dependencies

    # 显示当前拥塞控制算法
    echo -e "${BLUE}当前拥塞控制算法: $(get_current_congestion_control)${NC}"

    # 可用的算法列表
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${BLUE}macOS 检测到，支持的算法: ${GREEN}cubic, bbr${NC}"
    else
        local available=$(cat /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null || echo "cubic")
        echo -e "${BLUE}可用的拥塞控制算法: ${GREEN}$available${NC}"
    fi

    echo ""
    echo -e "${YELLOW}提示: 运行此脚本前，请先启动 iperf3 服务器:${NC}"
    echo "  iperf3 -s -p $SERVER_PORT"
    echo ""
    read -p "按 Enter 继续测试，或 Ctrl+C 取消..."

    # 运行测试
    local timestamp=$(date +%Y%m%d_%H%M%S)

    run_single_test "cubic" "cubic_test_${timestamp}"
    run_single_test "bbr" "bbr_test_${timestamp}"

    # 生成报告
    generate_report

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}所有测试完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "查看详细结果: ${BLUE}ls -la ${RESULTS_DIR}/${NC}"
    echo -e "查看测试报告: ${BLUE}cat ${RESULTS_DIR}/report.txt${NC}"
}

# 运行主流程
main "$@"
