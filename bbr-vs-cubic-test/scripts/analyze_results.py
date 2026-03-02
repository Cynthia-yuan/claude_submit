#!/usr/bin/env python3
"""
BBR vs CUBIC 测试结果分析脚本
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

def parse_json_result(file_path):
    """解析 iperf3 JSON 结果文件"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"错误: 无法解析 {file_path}: {e}")
        return None

def extract_metrics(data):
    """提取关键性能指标"""
    if not data or 'end' not in data:
        return None

    metrics = {}

    # 接收端统计
    if 'sum_received' in data['end']:
        sum_received = data['end']['sum_received']
        metrics['throughput_bps'] = sum_received.get('bits_per_second', 0)
        metrics['throughput_mbps'] = metrics['throughput_bps'] / 1_000_000
        metrics['throughput_gbps'] = metrics['throughput_bps'] / 1_000_000_000
        metrics['bytes_received'] = sum_received.get('bytes', 0)
        metrics['duration'] = sum_received.get('seconds', 0)

    # 发送端统计
    if 'sum_sent' in data['end']:
        sum_sent = data['end']['sum_sent']
        metrics['retransmits'] = sum_sent.get('retransmits', 0)
        metrics['bytes_sent'] = sum_sent.get('bytes', 0)

    # 流级别的统计（用于计算 RTT）
    if 'streams' in data['end']:
        streams = data['end']['streams']

        # 计算 RTT 统计
        rtts = []
        for stream in streams:
            if 'receiver' in stream and 'mean_rtt' in stream['receiver']:
                rtts.append(stream['receiver']['mean_rtt'])

        if rtts:
            metrics['avg_rtt_ms'] = sum(rtts) / len(rtts) / 1000  # 转换为毫秒
            metrics['min_rtt_ms'] = min(rtts) / 1000
            metrics['max_rtt_ms'] = max(rtts) / 1000
        else:
            metrics['avg_rtt_ms'] = 0
            metrics['min_rtt_ms'] = 0
            metrics['max_rtt_ms'] = 0

        # 计算吞吐量统计（各个流）
        throughputs = []
        for stream in streams:
            if 'receiver' in stream and 'bits_per_second' in stream['receiver']:
                throughputs.append(stream['receiver']['bits_per_second'])

        if throughputs:
            metrics['stream_stddev_mbps'] = (sum((x - sum(throughputs)/len(throughputs))**2 for x in throughputs) / len(throughputs))**0.5 / 1_000_000

    # 计算重传率
    if 'retransmits' in metrics and 'bytes_sent' in metrics and metrics['bytes_sent'] > 0:
        metrics['retransmit_rate'] = (metrics['retransmits'] / metrics['bytes_sent']) * 100

    # 计算抖动
    if 'streams' in data['end']:
        jitters = []
        for stream in data['end']['streams']:
            if 'receiver' in stream and 'stddev_rtt' in stream['receiver']:
                jitters.append(stream['receiver']['stddev_rtt'])

        if jitters:
            metrics['avg_jitter_ms'] = sum(jitters) / len(jitters) / 1000
        else:
            metrics['avg_jitter_ms'] = 0

    return metrics

def format_bytes(bytes_value):
    """格式化字节数"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def format_metric(value, unit, precision=2):
    """格式化指标"""
    return f"{value:.{precision}f} {unit}"

def print_header(text, char='='):
    """打印标题"""
    print(f"\n{char * 60}")
    print(f"  {text}")
    print(f"{char * 60}\n")

def print_metrics(algorithm, metrics, detailed=False):
    """打印指标"""
    if not metrics:
        print(f"  {algorithm}: 无有效数据")
        return

    print(f"  算法: {algorithm.upper()}")
    print(f"  ┌─ 吞吐量指标:")
    print(f"  │  总吞吐量: {format_metric(metrics.get('throughput_mbps', 0), 'Mbps')}")
    print(f"  │  总吞吐量: {format_metric(metrics.get('throughput_gbps', 0), 'Gbps')}")
    print(f"  │  总传输量: {format_bytes(metrics.get('bytes_received', 0))}")
    print(f"  │  测试时长: {format_metric(metrics.get('duration', 0), '秒', 1)}")

    if 'stream_stddev_mbps' in metrics:
        print(f"  │  流间标准差: {format_metric(metrics['stream_stddev_mbps'], 'Mbps')}")

    print(f"  ├─ 延迟指标:")
    print(f"  │  平均 RTT: {format_metric(metrics.get('avg_rtt_ms', 0), 'ms', 2)}")
    print(f"  │  最小 RTT: {format_metric(metrics.get('min_rtt_ms', 0), 'ms', 2)}")
    print(f"  │  最大 RTT: {format_metric(metrics.get('max_rtt_ms', 0), 'ms', 2)}")

    if 'avg_jitter_ms' in metrics:
        print(f"  │  平均抖动: {format_metric(metrics['avg_jitter_ms'], 'ms', 2)}")

    print(f"  ├─ 可靠性指标:")
    print(f"  │  重传次数: {metrics.get('retransmits', 0)}")

    if 'retransmit_rate' in metrics:
        print(f"  │  重传率: {format_metric(metrics['retransmit_rate'], '%', 3)}")

    if detailed:
        print(f"  └─ 发送字节: {format_bytes(metrics.get('bytes_sent', 0))}")
    else:
        print(f"  └─ 发送字节: {format_bytes(metrics.get('bytes_sent', 0))}")

    print()

def compare_metrics(bbr_metrics, cubic_metrics):
    """对比 BBR 和 CUBIC 的性能"""
    if not bbr_metrics or not cubic_metrics:
        print("无法进行对比：缺少有效数据")
        return

    print_header("性能对比分析", '-')

    metrics_to_compare = [
        ('吞吐量 (Mbps)', 'throughput_mbps', 'Mbps'),
        ('平均 RTT (ms)', 'avg_rtt_ms', 'ms'),
        ('重传次数', 'retransmits', ''),
        ('平均抖动 (ms)', 'avg_jitter_ms', 'ms'),
    ]

    for label, key, unit in metrics_to_compare:
        bbr_value = bbr_metrics.get(key, 0)
        cubic_value = cubic_metrics.get(key, 0)

        print(f"\n{label}:")
        print(f"  CUBIC: {format_metric(cubic_value, unit)}")
        print(f"  BBR:   {format_metric(bbr_value, unit)}")

        if cubic_value > 0 and key == 'throughput_mbps':
            improvement = ((bbr_value - cubic_value) / cubic_value) * 100
            if improvement > 0:
                print(f"  → BBR 提升: {format_metric(improvement, '%')}")
            else:
                print(f"  → BBR 下降: {format_metric(abs(improvement), '%')}")
        elif cubic_value > 0 and key in ['avg_rtt_ms', 'retransmits', 'avg_jitter_ms']:
            reduction = ((cubic_value - bbr_value) / cubic_value) * 100
            if bbr_value < cubic_value:
                print(f"  → BBR 降低: {format_metric(reduction, '%')}")
            else:
                print(f"  → BBR 增加: {format_metric(abs(reduction), '%')}")

    print()
    print("结论:")

    # 判断哪个算法更好
    bbr_better_count = 0
    cubic_better_count = 0

    # 吞吐量越高越好
    if bbr_metrics.get('throughput_mbps', 0) > cubic_metrics.get('throughput_mbps', 0):
        bbr_better_count += 1
    else:
        cubic_better_count += 1

    # RTT 越低越好
    if bbr_metrics.get('avg_rtt_ms', 0) < cubic_metrics.get('avg_rtt_ms', 0):
        bbr_better_count += 1
    else:
        cubic_better_count += 1

    # 重传越少越好
    if bbr_metrics.get('retransmits', 0) < cubic_metrics.get('retransmits', 0):
        bbr_better_count += 1
    else:
        cubic_better_count += 1

    # 抖动越小越好
    if bbr_metrics.get('avg_jitter_ms', 0) < cubic_metrics.get('avg_jitter_ms', 0):
        bbr_better_count += 1
    else:
        cubic_better_count += 1

    if bbr_better_count > cubic_better_count:
        print("  ✓ BBR 在本次测试中表现更优")
    elif cubic_better_count > bbr_better_count:
        print("  ✓ CUBIC 在本次测试中表现更优")
    else:
        print("  = 两种算法表现相当")

def find_result_files(results_dir):
    """查找结果文件"""
    results_path = Path(results_dir)

    bbr_files = sorted(results_path.glob("bbr_test_*.json"))
    cubic_files = sorted(results_path.glob("cubic_test_*.json"))

    return bbr_files, cubic_files

def main():
    parser = argparse.ArgumentParser(description='分析 BBR vs CUBIC 测试结果')
    parser.add_argument('--results-dir', '-r', default='results',
                        help='结果文件目录 (默认: results)')
    parser.add_argument('--bbr-file', '-b',
                        help='指定 BBR 结果文件')
    parser.add_argument('--cubic-file', '-c',
                        help='指定 CUBIC 结果文件')
    parser.add_argument('--detailed', '-d', action='store_true',
                        help='显示详细信息')
    parser.add_argument('--timestamp', '-t',
                        help='指定测试时间戳 (例如: 20241215_143000)')

    args = parser.parse_args()

    results_dir = args.results_dir

    # 查找结果文件
    if args.bbr_file and args.cubic_file:
        bbr_file = Path(args.bbr_file)
        cubic_file = Path(args.cubic_file)
    elif args.timestamp:
        bbr_file = Path(results_dir) / f"bbr_test_{args.timestamp}.json"
        cubic_file = Path(results_dir) / f"cubic_test_{args.timestamp}.json"
    else:
        bbr_files, cubic_files = find_result_files(results_dir)

        if not bbr_files or not cubic_files:
            print(f"错误: 在 {results_dir} 目录中未找到测试结果文件")
            print("请确保已运行测试，或使用 --bbr-file 和 --cubic-file 参数指定文件")
            sys.exit(1)

        # 使用最新的测试结果
        bbr_file = bbr_files[-1]
        cubic_file = cubic_files[-1]

    print_header("BBR vs CUBIC 测试结果分析")

    print(f"BBR 结果文件: {bbr_file}")
    print(f"CUBIC 结果文件: {cubic_file}")

    # 解析文件
    bbr_data = parse_json_result(bbr_file)
    cubic_data = parse_json_result(cubic_file)

    if not bbr_data:
        print(f"错误: 无法解析 BBR 结果文件")
        sys.exit(1)

    if not cubic_data:
        print(f"错误: 无法解析 CUBIC 结果文件")
        sys.exit(1)

    # 提取指标
    bbr_metrics = extract_metrics(bbr_data)
    cubic_metrics = extract_metrics(cubic_data)

    # 打印结果
    print_header("CUBIC 测试结果")
    print_metrics("cubic", cubic_metrics, args.detailed)

    print_header("BBR 测试结果")
    print_metrics("bbr", bbr_metrics, args.detailed)

    # 对比
    compare_metrics(bbr_metrics, cubic_metrics)

if __name__ == '__main__':
    main()
