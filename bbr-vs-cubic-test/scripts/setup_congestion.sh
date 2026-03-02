#!/bin/bash
# 网络拥塞场景配置脚本
# 使用 tc (traffic control) 模拟各种网络拥塞场景

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认网络接口（可以根据需要修改）
INTERFACE="${1:-lo0}"

echo -e "${GREEN}=== 网络拥塞场景配置工具 ===${NC}"
echo "网络接口: $INTERFACE"

# 检查是否有 root 权限
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}错误: 此脚本需要 root 权限运行${NC}"
   echo "请使用: sudo $0"
   exit 1
fi

# 清除现有的 qdisc 规则
clear_rules() {
    echo -e "${YELLOW}清除现有的 tc 规则...${NC}"
    tc qdisc del dev $INTERFACE root 2>/dev/null || true
    tc qdisc del dev $INTERFACE ingress 2>/dev/null || true
    echo -e "${GREEN}✓ 规则已清除${NC}"
}

# 场景1: 轻度拥塞 - 低延迟 + 低丢包
scenario1_light_congestion() {
    echo -e "${GREEN}配置场景1: 轻度拥塞 (延迟50ms, 丢包0.5%)${NC}"
    tc qdisc add dev $INTERFACE root netem \
        delay 50ms \
        loss 0.5% \
        rate 1gbit
    echo -e "${GREEN}✓ 场景1配置完成${NC}"
}

# 场景2: 中度拥塞 - 中延迟 + 中丢包
scenario2_medium_congestion() {
    echo -e "${GREEN}配置场景2: 中度拥塞 (延迟100ms±20ms, 丢包2%)${NC}"
    tc qdisc add dev $INTERFACE root netem \
        delay 100ms 20ms \
        loss 2% 25% \
        rate 500mbit
    echo -e "${GREEN}✓ 场景2配置完成${NC}"
}

# 场景3: 重度拥塞 - 高延迟 + 高丢包 + 抖动
scenario3_heavy_congestion() {
    echo -e "${GREEN}配置场景3: 重度拥塞 (延迟200ms±50ms, 丢包5%, 抖动)${NC}"
    tc qdisc add dev $INTERFACE root netem \
        delay 200ms 50ms \
        loss 5% 25% \
        duplicate 1% \
        rate 100mbit
    echo -e "${GREEN}✓ 场景3配置完成${NC}"
}

# 场景4: 缓冲区膨胀 - 高延迟带宽积
scenario4_bufferbloat() {
    echo -e "${GREEN}配置场景4: 缓冲区膨胀 (延迟150ms, 限速)${NC}"
    tc qdisc add dev $INTERFACE root handle 1: htb default 10
    tc class add dev $INTERFACE parent 1: classid 1:1 htb rate 1mbit
    tc class add dev $INTERFACE parent 1:1 classid 1:10 htb rate 1mbit ceil 1mbit
    tc qdisc add dev $INTERFACE parent 1:10 handle 10: netem delay 150ms
    echo -e "${GREEN}✓ 场景4配置完成${NC}"
}

# 场景5: 突发拥塞 - 动态变化
scenario5_burst_congestion() {
    echo -e "${GREEN}配置场景5: 突发拥塞 (变化延迟和丢包)${NC}"
    tc qdisc add dev $INTERFACE root netem \
        delay 50ms 100ms \
        loss 1% 50% \
        rate 200mbit
    echo -e "${GREEN}✓ 场景5配置完成${NC}"
}

# 场景6: 长肥管道 - 高带宽高延迟
scenario6_long_fat_network() {
    echo -e "${GREEN}配置场景6: 长肥管道 (高延迟, 大带宽)${NC}"
    tc qdisc add dev $INTERFACE root netem \
        delay 300ms 10ms \
        loss 0.1% \
        rate 10gbit
    echo -e "${GREEN}✓ 场景6配置完成${NC}"
}

# 显示当前规则
show_rules() {
    echo -e "${GREEN}=== 当前 tc 规则 ===${NC}"
    tc qdisc show dev $INTERFACE
    echo ""
    echo -e "${GREEN}=== 统计信息 ===${NC}"
    tc -s qdisc show dev $INTERFACE
}

# 交互式菜单
show_menu() {
    echo ""
    echo -e "${GREEN}请选择拥塞场景:${NC}"
    echo "0) 清除所有规则"
    echo "1) 轻度拥塞 (延迟50ms, 丢包0.5%)"
    echo "2) 中度拥塞 (延迟100ms±20ms, 丢包2%)"
    echo "3) 重度拥塞 (延迟200ms±50ms, 丢包5%, 抖动)"
    echo "4) 缓冲区膨胀 (延迟150ms, 限速1Mbps)"
    echo "5) 突发拥塞 (变化延迟和丢包)"
    echo "6) 长肥管道 (高延迟, 大带宽)"
    echo "s) 显示当前规则"
    echo "q) 退出"
    echo -n "选择: "
}

# 主循环
if [ $# -eq 0 ]; then
    # 交互模式
    while true; do
        show_menu
        read -r choice
        case $choice in
            0) clear_rules ;;
            1) clear_rules; scenario1_light_congestion ;;
            2) clear_rules; scenario2_medium_congestion ;;
            3) clear_rules; scenario3_heavy_congestion ;;
            4) clear_rules; scenario4_bufferbloat ;;
            5) clear_rules; scenario5_burst_congestion ;;
            6) clear_rules; scenario6_long_fat_network ;;
            s) show_rules ;;
            q) echo "退出"; exit 0 ;;
            *) echo -e "${RED}无效选择${NC}" ;;
        esac
    done
else
    # 命令行模式
    case $1 in
        clear) clear_rules ;;
        1) clear_rules; scenario1_light_congestion ;;
        2) clear_rules; scenario2_medium_congestion ;;
        3) clear_rules; scenario3_heavy_congestion ;;
        4) clear_rules; scenario4_bufferbloat ;;
        5) clear_rules; scenario5_burst_congestion ;;
        6) clear_rules; scenario6_long_fat_network ;;
        show) show_rules ;;
        *)
            echo "用法: $0 [clear|1|2|3|4|5|6|show]"
            echo "  或者不带参数运行进入交互模式"
            exit 1
            ;;
    esac
fi
