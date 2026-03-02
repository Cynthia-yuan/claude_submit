# 故障模式知识库

系统化的故障模式知识沉淀，帮助测试工程师理解和验证各类故障场景。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [故障分类](#故障分类)
- [使用指南](#使用指南)
- [贡献指南](#贡献指南)
- [FAQ](#faq)

## 概述

### 知识库结构

```
fault-pattern-knowledge-base/
├── templates/              # 模板和工具
│   ├── fault_pattern_template.md
│   └── fault_pattern_manager.py
├── network/                # 网络故障
│   ├── FP-NETWORK-001.md   # 网络高延迟
│   └── FP-NETWORK-002.md   # 网络丢包
├── storage/                # 存储故障
│   └── FP-STORAGE-001.md   # I/O延迟过高
├── compute/                # 计算资源故障
├── memory/                 # 内存故障
│   └── FP-MEMORY-001.md    # 内存耗尽(OOM)
├── database/               # 数据库故障
├── os/                     # 操作系统故障
├── network_security/       # 网络安全故障
├── chaos_engineering/      # 混沌工程实践
├── tools/                  # 故障注入工具集
└── README.md               # 本文件
```

### 故障模式 ID 规范

格式: `FP-{CATEGORY}-{YYYYMMDD}-{SEQ}`

示例:
- `FP-NETWORK-20250225-001` - 网络故障
- `FP-STORAGE-20250225-001` - 存储故障
- `FP-MEMORY-20250225-001` - 内存故障

### 元数据字段

每个故障模式包含以下元数据:

| 字段 | 说明 | 示例 |
|------|------|------|
| fault_id | 唯一标识 | FP-NETWORK-20250225-001 |
| name | 故障名称 | 网络高延迟故障 |
| category | 分类 | network |
| subcategory | 子类别 | latency |
| severity | 严重程度 | S1/S2/S3/S4 |
| frequency | 发生频率 | 高/中/低 |
| detectability | 检测难度 | 易/中/难 |

## 快速开始

### 方式选择

- 🌐 **Web界面**（推荐） - 可视化浏览和搜索
- 💻 **命令行** - 快速查询和执行

### Web界面使用（新功能）

#### 启动Web服务器

```bash
# 使用启动脚本
./start_server.sh

# 或手动启动
FLASK_APP=web/app.py python3 -m flask run --port=5001
```

然后访问：http://127.0.0.1:5001

#### Web功能

- 📊 **仪表板** - 查看统计信息和分类概览
- 🔍 **搜索** - 关键词搜索和过滤
- 📖 **详情页** - 完整的故障模式信息
- 📋 **脚本提取** - 一键复制或下载注入脚本
- 🎨 **响应式设计** - 支持桌面和移动设备

详细使用说明请参考 [WEB_GUIDE.md](WEB_GUIDE.md)

### 命令行使用

### 1. 查找故障模式

#### 按类别浏览
```bash
# 网络故障
ls network/

# 存储故障
ls storage/

# 内存故障
ls memory/
```

#### 搜索关键词
```bash
# 搜索包含"延迟"的故障
grep -r "延迟" */*.md

# 搜索 S1 级别故障
grep -r "severity: \"S1\"" */*.md
```

#### 使用索引
```bash
# 生成索引
python3 templates/fault_pattern_manager.py --index --base-path .

# 查看 INDEX.md
cat INDEX.md
```

### 2. 创建新故障模式

#### 方法1: 使用模板
```bash
# 复制模板
cp templates/fault_pattern_template.md network/FP-NETWORK-YYYYMMDD-XXX.md

# 编辑内容
vim network/FP-NETWORK-YYYYMMDD-XXX.md
```

#### 方法2: 使用管理工具
```bash
# 安装依赖
pip install pyyaml

# 创建故障模式
python3 templates/fault_pattern_manager.py \
  --create \
  --name "网络分区故障" \
  --category network
```

### 3. 故障注入实战

#### 网络延迟注入
```bash
# 查看详细步骤
cat network/FP-NETWORK-20250225-001.md | grep -A 20 "## 故障注入"

# 执行注入
sudo tc qdisc add dev eth0 root netem delay 300ms

# 验证
ping -c 10 target_host

# 清理
sudo tc qdisc del dev eth0 root
```

#### 内存 OOM 注入
```bash
# 查看详细步骤
cat memory/FP-MEMORY-20250225-001.md | grep -A 30 "## 故障注入"

# 执行注入
stress-ng --vm 1 --vm-bytes 4G --timeout 60s

# 监控
watch -n 1 "free -h"

# 检查 OOM
dmesg | grep -i oom
```

## 故障分类

### 按严重程度

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|---------|------|
| S1 | 致命 - 系统完全不可用，数据丢失风险 | 15分钟内 | 数据库主节点宕机 |
| S2 | 严重 - 核心功能受损，严重影响用户体验 | 30分钟内 | API服务不可用 |
| S3 | 中等 - 部分功能异常，有降级方案 | 2小时内 | 报表服务慢 |
| S4 | 轻微 - 边缘功能问题，不影响核心业务 | 1天内 | UI显示问题 |

### 按故障类别

#### 网络故障 (Network)
- [网络高延迟](network/FP-NETWORK-20250225-001.md) - RTT 异常增大
- [网络丢包](network/FP-NETWORK-20250225-002.md) - 数据包丢失
- 网络抖动 - RTT 不稳定
- 网络带宽限制 - 吞吐量受限
- DNS 解析故障
- 网络分区 - 集群分裂

#### 存储故障 (Storage)
- [I/O延迟过高](storage/FP-STORAGE-20250225-001.md) - 磁盘响应慢
- I/O 错误 - 读写失败
- 磁盘空间耗尽 - No space left
- RAID 故障 - 降级/失效
- SSD 寿命耗尽 - 变慢/只读
- 文件系统损坏

#### 内存故障 (Memory)
- [内存耗尽(OOM)](memory/FP-MEMORY-20250225-001.md) - OOM Killer 触发
- 内存泄漏 - 逐渐耗尽
- 内存碎片化 - 有内存但无法分配
- Swap 性能问题

#### 计算资源故障 (Compute)
- CPU 过载 - 100% 利用率
- CPU 过热 - 降频
- 进程崩溃 - Segment fault
- 死锁 - 资源竞争

#### 数据库故障 (Database)
- 连接池耗尽
- 慢查询
- 死锁
- 主从延迟
- 数据不一致

#### 操作系统故障 (OS)
- 内核恐慌 (Kernel Panic)
- 系统调用失败
- 文件描述符耗尽
- 端口耗尽

### 按故障注入难度

| 难度 | 工具 | 示例 | 成功率 |
|------|------|------|--------|
| 简单 | kill, tc, iptables | 进程终止, 网络延迟 | > 95% |
| 中等 | chaos-mesh, dmsetup | 磁盘I/O故障, 内存限制 | 70-90% |
| 困难 | 内核模块, 硬件模拟 | CPU硬件错误, 真实物理故障 | < 50% |

## 使用指南

### 测试流程

#### 1. 准备阶段
```
1. 选择故障模式
   ↓
2. 阅读故障描述，理解影响
   ↓
3. 检查测试环境（非生产）
   ↓
4. 准备监控和日志收集
   ↓
5. 准备回滚方案
```

#### 2. 执行阶段
```
1. 建立基线（正常状态）
   ↓
2. 执行故障注入
   ↓
3. 验证故障已注入
   ↓
4. 运行测试用例
   ↓
5. 收集监控数据
   ↓
6. 清理故障
```

#### 3. 分析阶段
```
1. 分析测试结果
   ↓
2. 对比基线数据
   ↓
3. 识别性能/功能影响
   ↓
4. 记录发现
   ↓
5. 优化系统
```

### 测试最佳实践

#### ✅ DO
- 在测试环境充分验证
- 使用自动化脚本
- 记录详细结果
- 逐步增加故障强度
- 设置自动恢复机制
- 监控系统状态

#### ❌ DON'T
- 直接在生产环境测试
- 无监控地注入故障
- 忘记清理故障
- 测试多个故障变量
- 在业务高峰测试

### 集成到 CI/CD

#### GitHub Actions 示例
```yaml
name: Chaos Testing

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点
  workflow_dispatch:

jobs:
  chaos-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install chaos-mesh
        run: |
          curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash

      - name: Inject network delay
        run: |
          kubectl apply -f .github/workflows/chaos-network-delay.yaml

      - name: Run tests
        run: |
          npm run test

      - name: Cleanup
        if: always()
        run: |
          kubectl delete -f .github/workflows/chaos-network-delay.yaml
```

#### Jenkins Pipeline 示例
```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'make build'
            }
        }

        stage('Chaos Test') {
            steps {
                sh '''
                  # 注入故障
                  sudo tc qdisc add dev eth0 root netem delay 300ms

                  # 运行测试
                  make test

                  # 清理
                  sudo tc qdisc del dev eth0 root
                '''
            }
        }
    }

    post {
        always {
            sh 'make clean-chaos'
        }
    }
}
```

## 贡献指南

### 添加新故障模式

1. **选择分类**: 确定故障属于哪个类别
2. **使用模板**: 复制 `templates/fault_pattern_template.md`
3. **编写内容**:
   - 填写元数据
   - 描述故障表现
   - 提供检测方法
   - 编写注入脚本
   - 给出预防措施
4. **测试验证**: 确保注入脚本可用
5. **提交 PR**: 包含清晰的描述

### 贡献标准

#### 内容质量
- ✅ 准确的技术描述
- ✅ 可执行的命令
- ✅ 真实的案例
- ✅ 清晰的预防措施

#### 格式规范
- ✅ 使用 Markdown
- ✅ 代码块指定语言
- ✅ 链接可点击
- ✅ 表格格式正确

#### 元数据完整
- ✅ 所有必填字段
- ✅ 唯一的 fault_id
- ✅ 正确的日期

## FAQ

### Q: 为什么需要故障模式知识库?

A:
1. **知识沉淀**: 避免重复造轮子
2. **快速查找**: 快速定位故障原因
3. **测试参考**: 标准化的测试方法
4. **团队成长**: 新人快速上手

### Q: 如何选择要测试的故障模式?

A: 优先级矩阵:

```
高影响 + 高频率 → 优先测试
高影响 + 低频率 → 次优先
低影响 + 高频率 → 定期测试
低影响 + 低频率 → 按需测试
```

### Q: 故障注入会很危险吗?

A: 如果遵循安全准则，风险可控:
1. ✅ 在测试环境验证
2. ✅ 有回滚方案
3. ✅ 设置自动恢复
4. ✅ 避免业务高峰

### Q: 如何在生产环境进行混沌测试?

A:
1. 金丝雀发布: 先小范围测试
2. 灰度发布: 逐步扩大范围
3. 熔断机制: 快速回滚
4. 实时监控: 密切观察指标

### Q: 如何维护知识库?

A:
1. **定期更新**: 添加新的故障模式
2. **版本控制**: 使用 Git 追踪变更
3. **Review 机制**: PR review
4. **使用反馈**: 收集用户反馈
5. **季度回顾**: 清理过时内容

## 统计

| 类别 | 数量 | 最后更新 |
|------|------|---------|
| Network | 2 | 2025-02-25 |
| Storage | 1 | 2025-02-25 |
| Memory | 1 | 2025-02-25 |
| Compute | 0 | - |
| Database | 0 | - |
| OS | 0 | - |
| **总计** | **4** | 2025-02-25 |

## 联系方式

- 问题反馈: [GitHub Issues](https://github.com/yourorg/fault-pattern-knowledge-base/issues)
- 贡献指南: 见上文
- 邮件: fault-patterns@example.com

## 许可证

MIT License

---

**最后更新**: 2025-02-25
**维护者**: 测试架构团队
