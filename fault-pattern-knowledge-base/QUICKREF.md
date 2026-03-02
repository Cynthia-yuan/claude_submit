# 快速参考卡 - Linux故障模式知识库

## 🚀 一键启动

```bash
./start_server.sh
# 访问 http://127.0.0.1:5001
```

## 📁 核心文件

| 文件 | 说明 |
|------|------|
| `start_server.sh` | 启动脚本 |
| `WEB_GUIDE.md` | Web界面详细使用指南 |
| `web/app.py` | Flask应用入口 |
| `web/services/pattern_parser.py` | Markdown解析服务 |
| `config.yaml` | 应用配置 |

## 🔗 主要URL

| 路径 | 说明 |
|------|------|
| `/` | 首页仪表板 |
| `/category/<name>` | 分类页面 |
| `/pattern/<id>` | 故障详情 |
| `/search?q=<keyword>` | 搜索 |
| `/api/faults` | API - 故障列表 |
| `/api/statistics` | API - 统计信息 |

## 💡 常用命令

```bash
# 启动Web服务器
./start_server.sh

# 生成索引
python3 templates/fault_pattern_manager.py --index --base-path .

# 使用CLI查询
./scripts/fault-query list network
./scripts/fault-query search latency
./scripts/fault-query show FP-NETWORK-20250225-001

# 使用CLI注入故障
sudo ./scripts/fault-query inject FP-NETWORK-20250225-001
```

## 🎨 功能特性

✅ Web界面浏览故障模式
✅ 关键词搜索和过滤
✅ 注入脚本一键复制/下载
✅ RESTful API接口
✅ 响应式设计
✅ 代码语法高亮
✅ 命令行工具支持

## 📊 当前统计

- 故障模式总数：4
- 分类数：3（网络、存储、内存）
- 网络故障：2
- 存储故障：1
- 内存故障：1

## ⚙️ 配置

编辑 `config.yaml` 修改：
- 监听端口（默认5001）
- 调试模式
- 缓存设置
- 路径配置

## 📝 添加新故障模式

```bash
# 1. 复制模板
cp templates/fault_pattern_template.md network/FP-NETWORK-YYYYMMDD-XXX.md

# 2. 编辑内容
vim network/FP-NETWORK-YYYYMMDD-XXX.md

# 3. 重新生成索引
python3 templates/fault_pattern_manager.py --index --base-path .

# 4. 重启Web服务器（如已运行）
```

## 🔧 故障排查

**端口被占用？**
```bash
# 使用其他端口
FLASK_APP=web/app.py python3 -m flask run --port=5002
```

**依赖缺失？**
```bash
pip3 install --user Flask markdown PyYAML python-frontmatter Flask-Caching Pygments
```

**页面显示异常？**
- 检查 `config.yaml` 中的 `base_path` 设置
- 确保 `INDEX.md` 存在
- 查看服务器日志输出

## ⚠️ 安全提醒

- 仅在测试环境使用注入脚本
- 执行前充分验证
- 准备回滚方案
- 避免业务高峰测试

---

**最后更新**：2025-02-27
**版本**：1.0.0
