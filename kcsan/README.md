# KCSAN Report Analyzer

KCSAN 报告分析工具 - 帮助快速识别内核并发竞争问题，定位代码位置，并提供修复建议。

## 功能特性

- **竞争变量提取** - 自动识别发生数据竞争的变量地址和变量名
- **代码定位** - 显示竞争发生的函数和文件位置
- **源码显示** - 自动显示相关源代码片段（需要内核源码）
- **变量定位** - 通过源码分析和 addr2line 工具定位具体变量
- **原因分析** - 分析竞争模式和可能的根本原因
- **修复建议** - 提供针对性的修复方案
- **历史统计** - 跟踪多次分析的热点问题
- **彩色输出** - 清晰易读的终端显示

## 安装

```bash
# 添加到 PATH
export PATH="$PATH:/Users/yuanlulu/vscode_claude/kcsan"

# 或创建别名（添加到 ~/.bashrc 或 ~/.zshrc）
alias kcsan-analyze='/Users/yuanlulu/vscode_claude/kcsan/kcsan-analyze'
```

## 快速开始

### 1. 分析 dmesg 输出

```bash
# 从 dmesg 实时分析
sudo dmesg | kcsan-analyze analyze

# 或直接使用 dmesg
dmesg | grep -i kcsan | kcsan-analyze analyze
```

### 2. 分析报告文件

```bash
# 分析文件中的 KCSAN 报告
kcsan-analyze analyze -f kcsan_report.txt

# 详细输出模式
kcsan-analyze analyze -f kcsan_report.txt -v

# 显示原始报告
kcsan-analyze analyze -f kcsan_report.txt -v --show-raw
```

### 3. 显示源代码

```bash
# 显示源代码（需要内核源码）
kcsan-analyze analyze -f kcsan_report.txt -v --show-source --kernel-src /path/to/kernel

# 自动检测内核源码位置
kcsan-analyze analyze -f kcsan_report.txt -v --show-source

# 自定义上下文行数（默认5行）
kcsan-analyze analyze -f kcsan_report.txt -v --show-source --context-lines 10
```

### 4. 识别竞争变量

```bash
# 识别发生竞争的变量名（需要 --show-source）
kcsan-analyze analyze -f kcsan_report.txt -v --show-source --kernel-src /path/to/kernel --resolve-vars

# 使用 vmlinux 调试符号进行更精确的定位
kcsan-analyze analyze -f kcsan_report.txt -v --show-source --resolve-vars --vmlinux /path/to/vmlinux
```

**变量识别置信度：**
- **HIGH** (🟢): 两个访问都指向同一个变量
- **MEDIUM** (🟡): 从一个访问推断出变量名
- **LOW** (🔴): 无法确定变量

### 5. 测试示例报告

```bash
# 使用提供的示例报告
cd /Users/yuanlulu/vscode_claude/kcsan
./kcsan-analyze analyze -f example_report_test.txt -v --show-source --kernel-src ./test_kernel
```

## 命令详解

### analyze - 分析 KCSAN 报告

```bash
kcsan-analyze analyze [OPTIONS]
```

**选项:**
- `-f, --file FILE` - 指定输入文件（默认从 stdin 读取）
- `-v, --verbose` - 显示详细分析，包括堆栈跟踪
- `--show-raw` - 显示原始报告文本
- `--no-history` - 不保存到历史记录
- `--show-source` - 显示源代码（需要 -v）
- `--kernel-src PATH` - 指定内核源码路径
- `--context-lines N` - 显示的上下文行数（默认: 5）
- `--resolve-vars` - 尝试识别变量名（需要 --show-source）
- `--vmlinux PATH` - 指定 vmlinux 二进制文件路径（带调试符号）

### stats - 显示统计信息

```bash
kcsan-analyze stats
```

显示:
- 总竞争数量
- 按严重程度分类
- 按竞争类型分类
- 最常出现的问题函数
- 热点内存地址（竞争最频繁的位置）

### export - 导出统计数据

```bash
kcsan-analyze export [OPTIONS]
```

**选项:**
- `--format {json,text}` - 导出格式（默认: text）
- `-o, --output FILE` - 输出文件（默认: stdout）

### clear - 清除历史

```bash
kcsan-analyze clear [OPTIONS]
```

**选项:**
- `-f, --force` - 强制清除，无需确认

## 竞争模式识别

工具可以识别以下常见竞争模式:

| 模式 | 描述 | 典型原因 |
|------|------|----------|
| `missing-lock-protection` | 缺少锁保护 | 没有使用锁或原子操作保护共享变量 |
| `mixed-atomic-non-atomic` | 混合原子/非原子访问 | 部分使用原子操作，部分使用普通访问 |
| `initialization-race` | 初始化竞争 | 变量初始化时的竞争条件 |
| `unknown-pattern` | 未知模式 | 需要手动调查 |

## 严重程度评估

- **HIGH** (🔴): Write-Write 竞争 - 可能导致内存损坏
- **MEDIUM** (🟡): Write-Read 竞争 - 可能导致读取不一致的值
- **LOW** (🟢): Read-Read 竞争 - 通常不是真正的问题

## 源码显示功能

工具可以自动定位并显示竞争发生的源代码位置。

### 内核源码位置

工具会按以下顺序查找内核源码：
1. `--kernel-src` 参数指定的路径
2. `/lib/modules/$(uname -r)/build`
3. `/usr/src/linux-headers-$(uname -r)`
4. 当前工作目录

### 源码输出示例

```
Source Code - Access 1
  File: kernel/module.c
  Line: 18
  Full Path: /path/to/kernel/kernel/module.c

  Source Code:
       13  */
       14 void example_function(void)
       15 {
       16     /* BUG: This write is not protected! */
       17     global_counter++;  /* Line 18 - Race detected here */
  >>>   18     printk(KERN_INFO "Counter: %d\n", global_counter);
       19 }
```

- `>>>` 标记表示发生竞争的代码行
- 默认显示前后各 5 行上下文
- 可通过 `--context-lines` 调整

## 变量定位功能

工具可以通过源码分析和符号表解析来识别发生竞争的变量名。

### 工作原理

1. **源码启发式分析** - 解析源码上下文，识别变量访问模式
2. **符号表解析** - 使用 addr2line/llvm-addr2line 查询地址符号信息

### 变量识别输出示例

```
Variable Identification
  Variable Name: global_counter
  Address: 0xffffffff8245a1c0
  Confidence: MEDIUM
  Method: source_analysis_access1
```

### 使用方法

```bash
# 基本变量识别（基于源码分析）
kcsan-analyze analyze -f report.txt -v \
  --show-source \
  --kernel-src /path/to/kernel \
  --resolve-vars

# 使用 vmlinux 调试符号（更精确）
kcsan-analyze analyze -f report.txt -v \
  --show-source \
  --resolve-vars \
  --vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r)
```

### vmlinux 位置

工具会按以下顺序查找 vmlinux：
1. `--vmlinux` 参数指定的路径
2. `/usr/lib/debug/boot/vmlinux-$(uname -r)`
3. `/boot/vmlinux-$(uname -r)`
4. `/lib/modules/$(uname -r)/build/vmlinux`

### 限制

- 变量识别是**启发式的**，不一定 100% 准确
- 对于栈变量或复杂表达式，可能无法识别
- 需要内核源码或带调试符号的 vmlinux

## 工作流程示例

```bash
# 1. 运行测试并收集 KCSAN 报告
sudo dmesg > kcsan_test.log

# 2. 分析报告（包含源码和变量识别）
kcsan-analyze analyze -f kcsan_test.log -v \
  --show-source \
  --kernel-src /usr/src/linux \
  --resolve-vars

# 3. 查看统计信息
kcsan-analyze stats

# 4. 导出数据用于进一步分析
kcsan-analyze export --format json -o test_stats.json
```

### 完整分析流程（带源码和变量识别）

```bash
# 假设内核源码在 /usr/src/linux
kcsan-analyze analyze \
  -f kcsan_test.log \
  -v \
  --show-source \
  --kernel-src /usr/src/linux \
  --resolve-vars \
  --vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r) \
  --context-lines 10
```

## 文件位置

- 历史记录: `~/.kcsan_history.json`
- 工具位置: `/Users/yuanlulu/vscode_claude/kcsan/`

## 帮助

```bash
# 查看帮助
kcsan-analyze --help
```