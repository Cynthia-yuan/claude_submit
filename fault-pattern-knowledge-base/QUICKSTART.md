# 故障模式工具快速指南

## 安装

```bash
# 添加到 PATH
export PATH="$PATH:/Users/yuanlulu/vscode_claude/fault-pattern-knowledge-base/scripts"

# 或创建别名（添加到 ~/.bashrc 或 ~/.zshrc）
alias fault-query='/Users/yuanlulu/vscode_claude/fault-pattern-knowledge-base/scripts/fault-query'
```

## 使用示例

### 1. 列出所有故障模式

```bash
fault-query list
```

输出：
```
故障模式列表
==================

## NETWORK
  - [FP-NETWORK-20250225-001](../network/FP-NETWORK-20250225-001.md)
  - [FP-NETWORK-20250225-002](../network/FP-NETWORK-20250225-002.md)

## STORAGE
  - [FP-STORAGE-20250225-001](../storage/FP-STORAGE-20250225-001.md)

## MEMORY
  - [FP-MEMORY-20250225-001](../memory/FP-MEMORY-20250225-001.md)
```

### 2. 列出特定类别的故障

```bash
fault-query list network
```

### 3. 搜索故障模式

```bash
# 搜索包含"延迟"的故障
fault-query search 延迟

# 搜索包含"OOM"的故障
fault-query search OOM

# 搜索包含"I/O"的故障
fault-query search "I/O"
```

### 4. 查看故障模式详情

```bash
# 查看网络高延迟故障
fault-query show FP-NETWORK-20250225-001

# 查看内存耗尽故障
fault-query show FP-MEMORY-20250225-001
```

### 5. 执行故障注入（需要 root）

```bash
# 注入网络延迟
sudo fault-query inject FP-NETWORK-20250225-001

# 注入内存压力
sudo fault-query inject FP-MEMORY-20250225-001
```

### 6. 查看故障注入工具

```bash
# 查看所有工具类别
fault-query tools

# 查看网络故障注入工具
fault-query tools network

# 查看存储故障注入工具
fault-query tools storage
```

## 常用命令组合

### 快速测试网络延迟

```bash
# 1. 查看网络延迟故障
fault-query show FP-NETWORK-20250225-001

# 2. 注入 300ms 延迟
sudo tc qdisc add dev eth0 root netem delay 300ms

# 3. 测试
ping -c 10 target_host

# 4. 清理
sudo tc qdisc del dev eth0 root
```

### 快速测试内存 OOM

```bash
# 1. 查看内存 OOM 故障
fault-query show FP-MEMORY-20250225-001

# 2. 触发内存压力
stress-ng --vm 1 --vm-bytes 4G --timeout 60s

# 3. 监控
watch -n 1 free -h

# 4. 检查 OOM 日志
dmesg | grep -i oom
```

### 集成到测试脚本

```bash
#!/bin/bash
# test_with_chaos.sh

# 注入故障
sudo fault-query inject FP-NETWORK-20250225-001

# 运行测试
npm test

# 清理故障
sudo tc qdisc del dev eth0 root
```

## 输出说明

- 🟢 **绿色**: 正常信息
- 🔴 **红色**: 错误信息
- 🟡 **黄色**: 警告信息
- 🔵 **蓝色**: 标题和类别
- 🟦 **青色**: 文件名和链接

## 安全提示

⚠️ **故障注入可能导致系统不稳定，请务必**:

1. ✅ 在测试环境执行
2. ✅ 保存当前工作
3. ✅ 了解故障影响范围
4. ✅ 准备回滚方案
5. ✅ 避免在业务高峰测试

## 更多帮助

```bash
fault-query --help
```
