# cmd-sniper - Linux 命令行审计工具

## 概述

cmd-sniper 是一个功能强大的 Linux 命令行审计和分析工具，能够捕获系统中所有用户的命令执行记录，并提供详细的统计分析报告。

## 功能特点

- **双模式捕获**
  - auditd 审计系统：稳定成熟的系统级审计
  - eBPF 内核追踪：内核级 execve 系统调用追踪

- **全面记录**
  - 完整命令行及参数
  - 执行时间戳
  - 用户信息（UID/用户名）
  - 进程信息（PID/PPID）
  - 工作目录

- **智能分析**
  - 命令执行频率统计
  - 用户活跃度分析
  - 时间分布图表
  - 命令分类统计
  - 风险命令检测

- **多种报告格式**
  - HTML 交互式报告（含图表）
  - JSON 格式导出
  - CSV 格式导出

## 安装

```bash
# 克隆项目
cd cmd-sniper

# 运行安装脚本（需要 root 权限）
sudo ./scripts/install.sh
```

## 使用方法

### 快速开始（无需安装）

```bash
cd cmd-sniper

# 直接运行（需要 Python 3.7+）
python cmd-sniper.py init
python cmd-sniper.py status
```

### 完整安装

```bash
# 运行安装脚本
sudo ./scripts/install.sh
```

### 启动捕获

```bash
# 已安装用户
sudo cmd-sniper start --method auditd

# 未安装（直接运行）
sudo python cmd-sniper.py start --method auditd

# 使用 eBPF 方式启动
sudo cmd-sniper start --method ebpf

# 同时使用两种方式
sudo cmd-sniper start --method both

# 在后台运行
sudo cmd-sniper start --daemon
```

### 查看状态

```bash
sudo cmd-sniper status
```

### 生成报告

```bash
# 生成 HTML 报告
sudo cmd-sniper report -o report.html

# 生成 JSON 报告
sudo cmd-sniper report -f json -o report.json

# 生成最近 7 天的报告
sudo cmd-sniper report --days 7 -o weekly.html
```

### 查询命令

```bash
# 搜索包含特定模式的命令
sudo cmd-sniper query "nginx"

# 限制结果数量
sudo cmd-sniper query "docker" --limit 20

# 只查询特定用户
sudo cmd-sniper query "sudo" --user 1000
```

### 其他常用命令

```bash
# 查看最常用的命令
sudo cmd-sniper top

# 查看最活跃的用户
sudo cmd-sniper users

# 查看风险命令
sudo cmd-sniper risky

# 导出数据
sudo cmd-sniper export -f json -o commands.json

# 清理旧数据
sudo cmd-sniper cleanup --retention 90
```

## 系统要求

- Linux 内核 >= 4.15 (eBPF 支持)
- Python 3.7+
- root 权限
- auditd 服务（auditd 模式）

## 配置文件

默认配置位置：`/etc/cmd-sniper/config.yaml`

```yaml
capture:
  method: auditd          # 捕获方式: auditd, ebpf, both
  capture_env: false      # 是否捕获环境变量

storage:
  db_path: /var/lib/cmd-sniper/commands.db
  retention_days: 90      # 数据保留天数

analysis:
  exclude_commands:       # 排除的命令
    - ""
    - "ls"
    - "cd"
```

## 卸载

```bash
sudo ./scripts/uninstall.sh
```

## 架构说明

```
cmd-sniper/
├── src/
│   ├── capture/      # 捕获模块 (auditd, eBPF)
│   ├── parser/       # 日志解析
│   ├── analyzer/     # 统计分析
│   ├── reporter/     # 报告生成
│   ├── storage/      # 数据库存储
│   └── cli.py        # CLI 入口
├── ebpf/             # eBPF 程序
├── config/           # 配置文件
└── scripts/          # 安装脚本
```

## 安全注意事项

1. 此工具捕获所有命令执行，可能包含敏感信息
2. 数据库文件应设置适当的访问权限
3. 建议定期审查风险命令报告
4. 仅在获得授权的系统上使用

## 许可证

MIT License
