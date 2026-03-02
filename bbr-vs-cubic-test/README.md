# BBR vs CUBIC 网络拥塞控制算法对比测试工具

完整的自动化测试工具，用于验证在网络拥塞场景下 BBR 算法优于 CUBIC 算法。

## 目录结构

```
bbr-vs-cubic-test/
├── scripts/
│   ├── setup_congestion.sh    # 网络拥塞场景配置工具
│   ├── run_test.sh            # 性能测试脚本
│   └── analyze_results.py     # 结果分析脚本
├── results/                   # 测试结果目录
├── logs/                      # 日志目录
├── run_all_tests.sh           # 一键运行所有测试
└── README.md                  # 本文件
```

## 系统要求

### 必需工具

- **iperf3**: 网络性能测试工具
- **jq**: JSON 处理工具
- **python3**: Python 3.x
- **tc (Linux)**: Linux 流量控制工具 (可选，用于拥塞模拟)

### 安装依赖

#### macOS
```bash
brew install iperf3 jq python3
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y iperf3 jq python3 iproute2
```

#### CentOS/RHEL
```bash
sudo yum install -y iperf3 jq python3 iproute
```

## 快速开始

### 1. 启动 iperf3 服务器

在第一个终端中：
```bash
iperf3 -s -p 5201
```

### 2. 运行完整测试

在第二个终端中：
```bash
cd bbr-vs-cubic-test
chmod +x run_all_tests.sh
./run_all_tests.sh
```

测试脚本会：
1. 检查系统依赖
2. 验证 iperf3 服务器连接
3. 让你选择测试场景
4. 自动运行 CUBIC 和 BBR 测试
5. 生成对比分析报告

## 使用说明

### 一键运行所有测试（推荐）

```bash
# 基本使用
./run_all_tests.sh

# 自定义测试参数
TEST_DURATION=60 PARALLEL_STREAMS=8 ./run_all_tests.sh

# 指定服务器
SERVER_HOST=192.168.1.100 SERVER_PORT=5201 ./run_all_tests.sh
```

### 网络拥塞场景配置

独立使用拥塞配置工具：

```bash
# 交互式菜单
sudo ./scripts/setup_congestion.sh

# 命令行模式
sudo ./scripts/setup_congestion.sh 2  # 场景2: 中度拥塞
sudo ./scripts/setup_congestion.sh clear  # 清除规则
```

**可用场景：**
- `1` - 轻度拥塞 (延迟 50ms, 丢包 0.5%)
- `2` - 中度拥塞 (延迟 100ms±20ms, 丢包 2%)
- `3` - 重度拥塞 (延迟 200ms±50ms, 丢包 5%, 抖动)
- `4` - 缓冲区膨胀 (延迟 150ms, 限速 1Mbps)
- `5` - 突发拥塞 (变化延迟和丢包)
- `6` - 长肥管道 (高延迟, 大带宽)
- `0` - 无拥塞 (正常网络)

### 运行单次性能测试

```bash
# 基本使用
./scripts/run_test.sh

# 自定义参数
TEST_DURATION=120 PARALLEL_STREAMS=4 ./scripts/run_test.sh
```

该脚本会自动：
1. 切换拥塞控制算法到 CUBIC
2. 运行 iperf3 测试
3. 切换到 BBR
4. 再次运行测试
5. 生成结果文件

### 分析测试结果

```bash
# 分析最新的测试结果
python3 scripts/analyze_results.py

# 分析指定的测试结果
python3 scripts/analyze_results.py \
    --bbr-file results/bbr_test_20241215_143000.json \
    --cubic-file results/cubic_test_20241215_142955.json

# 显示详细信息
python3 scripts/analyze_results.py -d
```

## 测试场景说明

### 场景 1: 轻度拥塞
- **配置**: 延迟 50ms, 丢包 0.5%
- **适用场景**: 模拟轻微拥塞的网络环境
- **预期结果**: BBR 和 CUBIC 差距较小

### 场景 2: 中度拥塞
- **配置**: 延迟 100ms±20ms, 丢包 2%
- **适用场景**: 模拟中等拥塞的网络
- **预期结果**: BBR 开始体现优势

### 场景 3: 重度拥塞
- **配置**: 延迟 200ms±50ms, 丢包 5%, 抖动
- **适用场景**: 模拟严重拥塞的不稳定网络
- **预期结果**: BBR 显著优于 CUBIC

### 场景 4: 缓冲区膨胀
- **配置**: 延迟 150ms, 限速 1Mbps
- **适用场景**: 模拟缓冲区膨胀问题
- **预期结果**: BBR 的 RTT 控制优势明显

### 场景 5: 突发拥塞
- **配置**: 变化延迟和丢包
- **适用场景**: 模拟动态变化的网络条件
- **预期结果**: BBR 的适应能力更强

### 场景 6: 长肥管道
- **配置**: 高延迟 (300ms), 大带宽
- **适用场景**: 跨国/跨洋传输
- **预期结果**: BBR 的带宽利用率更高

## 性能指标说明

测试脚本会测量以下关键指标：

| 指标 | 说明 | 越高/越低越好 |
|------|------|--------------|
| 吞吐量 (Mbps) | 数据传输速率 | 越高越好 |
| 平均 RTT (ms) | 往返延迟 | 越低越好 |
| 重传次数 | 重新传输的数据包数量 | 越少越好 |
| 重传率 (%) | 重传占总传输的比例 | 越低越好 |
| 抖动 (ms) | 延迟的变化程度 | 越低越好 |
| 流间标准差 | 并发流的公平性 | 越低越公平 |

## BBR vs CUBIC 理论对比

### CUBIC (传统算法)
- 基于丢包的拥塞控制
- 丢包后才降低发送速率
- 容易造成缓冲区膨胀
- 在高延迟网络中性能较差

### BBR (现代算法)
- 基于模型的拥塞控制
- 主动测量带宽和 RTT
- 避免拥塞而非反应拥塞
- 在各种网络条件下性能稳定

**BBR 优势场景：**
- 高延迟、低丢包网络
- 缓冲区膨胀环境
- 动态变化的网络
- 长肥管道网络

## 常见问题

### Q1: macOS 提示不支持 tc (traffic control)
**A:** macOS 不支持 Linux 的 tc 工具。建议：
- 使用 Linux 虚拟机 (VMware/VirtualBox)
- 使用 Docker 容器
- 在云服务器上测试
- 或者跳过拥塞配置，测试正常网络下的表现

### Q2: 提示需要 root 权限
**A:** 网络配置需要 root 权限：
```bash
sudo ./run_all_tests.sh
```

### Q3: iperf3 连接失败
**A:** 确保 iperf3 服务器正在运行：
```bash
# 在另一个终端
iperf3 -s -p 5201
```

### Q4: BBR 算法不可用
**A:** 检查内核支持：
```bash
# Linux
cat /proc/sys/net/ipv4/tcp_available_congestion_control
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr

# macOS (需要较新版本)
sysctl -a | grep cc.algorithm
```

### Q5: 测试结果差异很大
**A:** 网络测试有波动，建议：
- 增加测试时长：`TEST_DURATION=120`
- 多次测试取平均值
- 关闭其他网络应用
- 使用有线网络而非 WiFi

## 高级用法

### 自定义网络拥塞参数

编辑 `scripts/setup_congestion.sh`，修改场景配置：

```bash
scenario2_medium_congestion() {
    tc qdisc add dev $INTERFACE root netem \
        delay 100ms 20ms \   # 延迟 100ms ± 20ms
        loss 2% 25% \        # 丢包 2% ± 25%
        rate 500mbit         # 限速 500Mbps
}
```

### 并发测试多个场景

```bash
# 运行所有场景
./run_all_tests.sh
# 选择: a

# 或手动循环
for i in {1..6}; do
    ./run_all_tests.sh <<< "$i"
done
```

### 使用 Docker 隔离测试环境

```bash
# 构建测试容器
docker build -t bbr-test .

# 运行测试
docker run --rm --privileged --network host bbr-test
```

## 输出文件说明

### JSON 结果文件
保存详细的 iperf3 测试数据：
```
results/bbr_test_20241215_143000.json
results/cubic_test_20241215_142955.json
```

### 分析报告
- `results/report.txt` - 基本测试报告
- `results/summary_report.txt` - 多场景总结报告

### 日志文件
```
logs/bbr_test_20241215_143000.log
logs/cubic_test_20241215_142955.log
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 参考资料

- [BBR 论文](https://queue.acm.org/detail.cfm?id=3022184)
- [TCP CUBIC](https://www.sciencedirect.com/science/article/pii/S1389128608001158)
- [iperf3 文档](https://software.es.net/iperf/)
- [Linux Traffic Control](https://man7.org/linux/man-pages/man8/tc.8.html)
