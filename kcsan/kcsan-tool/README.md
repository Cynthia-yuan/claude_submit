# KCSAN 误报率降低工具

KCSAN (Kernel Concurrency Sanitizer) 报告处理工具，通过去重、白名单和调参降低误报率。

## 功能

- **报告提取**: 从 dmesg 提取 KCSAN 报告
- **智能去重**: 精确去重和模糊去重
- **白名单管理**: 按调用栈/地址/通配符过滤
- **统计报告**: 生成人类可读和 JSON 格式报告
- **调参建议**: 自动生成 KCSAN boot 参数

## 安装

```bash
cd kcsan-tool
chmod +x kcsan-tool.sh
chmod +x lib/*.sh
```

## 使用

### 运行完整流程

```bash
./kcsan-tool.sh run -i dmesg
```

### 单独使用各模块

```bash
# 仅提取报告
./kcsan-tool.sh extract -i dmesg

# 仅去重
./kcsan-tool.sh dedup

# 生成报告
./kcsan-tool.sh report

# 调参建议
./kcsan-tool.sh tune
```

### 白名单管理

```bash
# 添加条目
./kcsan-tool.sh whitelist add "tick_periodic / clock_settime" "时间相关良性竞争"

# 列出白名单
./kcsan-tool.sh whitelist list

# 删除条目
./kcsan-tool.sh whitelist remove "tick_periodic / clock_settime"

# 初始化白名单
./kcsan-tool.sh whitelist init
```

## 输出目录

```
output/
├── raw/           # 原始报告
├── deduped/       # 去重后报告
├── filtered/      # 过滤后报告
└── final/         # 最终报告和统计
    ├── reports.txt      # 最终报告
    ├── stats.txt        # 统计信息
    ├── summary.txt      # 摘要
    ├── tuning.txt       # 调参建议
    ├── kcsan.boot.conf  # Boot 参数配置
    └── cmdline.txt      # 命令行建议
```

## 白名单格式

```
# 精确函数对
tick_periodic / clock_settime # 时间相关

# 通配符
tick_* / clock_* # 时间子系统

# 地址白名单
ADDR:0xffffffff8260a280 # 时钟设备寄存器
```

## 应用 Boot 参数

编辑 `/etc/default/grub`:

```
GRUB_CMDLINE_LINUX="... kcsan=1 kcsan.report_once_in_ms=5000 ..."
```

然后运行:

```bash
sudo update-grub
sudo reboot
```

## 工作流程

```
dmesg
  ↓ 提取
raw/reports.txt
  ↓ 精确去重
deduped/reports.txt
  ↓ 白名单过滤
filtered/reports.txt
  ↓ 最终报告
final/reports.txt
  ↓ 调参建议
kcsan.boot.conf
```
