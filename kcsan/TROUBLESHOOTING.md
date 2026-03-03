# KCSAN 分析工具 - 源码显示问题排查指南

## 问题："Source code not available"

如果你看到 "(Source code not available)" 消息，使用以下步骤进行诊断：

## 快速诊断

使用 `--diagnose` 参数查看详细信息：

```bash
kcsan-analyze analyze -f report.txt -v \
  --show-source \
  --kernel-src /path/to/kernel \
  --diagnose
```

## 常见问题及解决方案

### 1. 堆栈跟踪中没有 file:line 格式

**症状：**
```
Source Code Resolution Diagnostics
  Access 1: Stack has X frames: ['func1', 'func2', 'func3']
  Access 1:   Frame 0: 'func1' - No file:line match
  Access 1:   Frame 1: 'func2' - No file:line match
  Access 1:   Frame 2: 'func3' - No file:line match
```

**原因：** 你的内核编译时没有启用调试信息（缺少 CONFIG_DEBUG_INFO 和 CONFIG_DEBUG_INFO_DWARF4）

**解决方案：**
- 重新编译内核时启用调试选项
- 或使用 addr2line 从 vmlinux 符号表解析

```bash
# 启用内核调试选项
CONFIG_DEBUG_INFO=y
CONFIG_DEBUG_INFO_DWARF4=y
CONFIG_DEBUG_INFO_BTF=y
```

### 2. 源文件路径不匹配

**症状：**
```
Source Code Resolution Diagnostics
  Access 1: Found file:line at frame 1: kernel/module.c:123
  Access 2: Found file:line at frame 1: kernel/sched/core.c:456
  Kernel Source: /usr/src/linux

  Source Code - Access 1
  (Source code not available)
```

**原因：** 源文件在内核源码树中的路径与堆栈跟踪中的路径不匹配

**解决方案：**
- 确保使用的是完整的内核源码（包含所有文件）
- 尝试使用不同的内核版本源码
- 使用 `find` 命令检查文件是否存在：

```bash
find /path/to/kernel -name "module.c"
find /path/to/kernel -path "*/sched/core.c"
```

### 3. 权限问题

**症状：** 无错误提示，但源码不显示

**解决方案：**
```bash
# 检查源码目录权限
ls -la /path/to/kernel/kernel/

# 确保可读
chmod -R +r /path/to/kernel
```

### 4. 示例报告格式对比

**正确的格式（带 file:line）：**
```
[  123.456789] BUG: KCSAN: data-race in func1 / func2

[  123.456790] write to 0xffffffff8245a1c0 of 4 bytes by task 1234 on cpu 0:
[  123.456791]  func1+0x45/0x100
[  123.456792]  kernel/module.c:123
[  123.456793]  module_caller+0x78/0xa0
```

**不正确的格式（无 file:line）：**
```
[  123.456789] BUG: KCSAN: data-race in func1 / func2

[  123.456790] write to 0xffffffff8245a1c0 of 4 bytes by task 1234 on cpu 0:
[  123.456791]  func1+0x45/0x100
[  123.456792]  module_caller+0x78/0xa0
```

## 完整诊断流程

```bash
# 1. 测试源码路径
ls -la /path/to/kernel/kernel/sched/core.c

# 2. 测试堆栈跟踪格式
grep -n "BUG: KCSAN" kcsan_report.txt | head -5

# 3. 运行诊断
kcsan-analyze analyze -f kcsan_report.txt -v \
  --show-source \
  --kernel-src /path/to/kernel \
  --diagnose

# 4. 检查是否启用了内核调试
cat /proc/config.gz | zgrep DEBUG_INFO
```

## 其他诊断命令

```bash
# 查看堆栈跟踪内容
awk '/BUG: KCSAN/,/=====/ {print}' kcsan_report.txt

# 测试文件解析
python3 -c "
import sys
sys.path.insert(0, '/Users/yuanlulu/vscode_claude/kcsan')
from kcsan_analyzer import KCSANParser

with open('kcsan_report.txt') as f:
    parser = KCSANParser()
    races = parser.parse_dmesg_output(f.read())
    for race in races:
        print(f'Race: {race.race_type}')
        print(f'Access 1 stack: {race.access1.stack_trace}')
        print(f'Access 2 stack: {race.access2.stack_trace}')
        print('---')
"
```

## 联系支持

如果问题仍然存在，请提供：
1. KCSAN 报告样本（至少一个完整的竞争报告）
2. 使用的命令行参数
3. `--diagnose` 参数的输出
4. 内核版本和编译配置