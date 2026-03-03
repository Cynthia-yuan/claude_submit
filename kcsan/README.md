# KCSAN Report Analyzer

KCSAN 报告分析工具 - 帮助快速识别内核并发竞争问题，定位代码位置，并提供修复建议。

## 功能特性

- **竞争变量提取** - 自动识别发生数据竞争的变量地址
- **代码定位** - 显示竞争发生的函数和文件位置
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

### 3. 测试示例报告

```bash
# 使用提供的示例报告
cd /Users/yuanlulu/vscode_claude/kcsan
./kcsan-analyze analyze -f example_report.txt -v
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

## 工作流程示例

```bash
# 1. 运行测试并收集 KCSAN 报告
sudo dmesg > kcsan_test.log

# 2. 分析报告
kcsan-analyze analyze -f kcsan_test.log -v

# 3. 查看统计信息
kcsan-analyze stats

# 4. 导出数据用于进一步分析
kcsan-analyze export --format json -o test_stats.json
```

## 文件位置

- 历史记录: `~/.kcsan_history.json`
- 工具位置: `/Users/yuanlulu/vscode_claude/kcsan/`

## 帮助

```bash
# 查看帮助
kcsan-analyze --help
```