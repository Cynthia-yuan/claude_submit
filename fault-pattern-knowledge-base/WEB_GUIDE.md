# Linux故障模式知识库 - Web界面使用指南

## 快速启动

### 方式1：使用启动脚本（推荐）

```bash
./start_server.sh
```

### 方式2：手动启动

```bash
# 1. 安装依赖（首次运行）
pip3 install --user Flask markdown PyYAML python-frontmatter Flask-Caching Pygments python-dotenv gunicorn

# 2. 生成索引
python3 templates/fault_pattern_manager.py --index --base-path .

# 3. 启动服务器
FLASK_APP=web/app.py python3 -m flask run --host=127.0.0.1 --port=5001
```

### 方式3：生产环境部署

```bash
# 使用Gunicorn
gunicorn --workers 4 --bind 127.0.0.1:5001 web.app:app
```

启动后访问：**http://127.0.0.1:5001**

---

## 功能说明

### 1. 首页仪表板
- 显示故障模式总数和分类统计
- 分类卡片快速导航
- 最近更新的故障模式
- 严重程度分布图表

### 2. 分类浏览
点击侧边栏的分类或首页的分类卡片，查看该分类下的所有故障模式。

### 3. 故障详情页
每个故障模式详情页包含：
- **元数据**：故障ID、分类、严重程度、标签等
- **注入脚本**：可一键复制或下载
- **详细信息**：故障描述、症状、根因、检测方法等
- **相关故障**：同分类下的其他故障模式

### 4. 搜索功能
- 支持关键词搜索
- 按分类过滤
- 按严重程度过滤（S1-S4）

**提示**：当前版本支持英文关键词搜索效果最佳。

### 5. 注入脚本使用

#### 方式1：一键复制
1. 在故障详情页找到"故障注入脚本"区域
2. 点击"复制"按钮
3. 粘贴到终端执行

#### 方式2：下载脚本
1. 点击"下载 .sh"按钮
2. 保存到本地
3. 根据环境修改参数（如网络接口名）
4. 在测试环境执行：`bash downloaded_script.sh`

#### 方式3：使用CLI工具
```bash
sudo /path/to/fault-pattern-knowledge-base/scripts/fault-query inject FP-NETWORK-20250225-001
```

---

## API接口

Web应用同时提供RESTful API，方便集成到其他系统。

### 获取所有故障
```bash
curl http://localhost:5001/api/faults
```

### 按分类过滤
```bash
curl http://localhost:5001/api/faults?category=network
```

### 获取特定故障
```bash
curl http://localhost:5001/api/faults/FP-NETWORK-20250225-001
```

### 获取统计信息
```bash
curl http://localhost:5001/api/statistics
```

### 提取注入脚本
```bash
curl http://localhost:5001/api/scripts/FP-NETWORK-20250225-001
```

---

## 配置说明

编辑 `config.yaml` 自定义配置：

```yaml
app:
  name: "Linux故障模式知识库"  # 应用名称
  debug: true                   # 调试模式（生产环境设为false）
  secret_key: "your-secret-key" # Flask密钥

paths:
  base_path: "."                # 知识库根路径
  index_file: "INDEX.md"        # 索引文件名

features:
  enable_search: true           # 启用搜索
  enable_cache: true            # 启用缓存

cache:
  timeout: 300                  # 缓存时间（秒）

server:
  host: "0.0.0.0"               # 监听地址
  port: 5001                    # 监听端口
```

---

## 故障排查

### 端口被占用
如果提示端口5000被占用（macOS的AirPlay Receiver），使用端口5001：
```bash
FLASK_APP=web/app.py python3 -m flask run --port=5001
```

### 模板未找到
确保在项目根目录运行命令，或设置正确的 `base_path`。

### 编码问题
确保所有Markdown文件使用UTF-8编码。

---

## 项目结构

```
web/
├── app.py                    # Flask应用入口
├── config.py                 # 配置管理
├── routes/                   # 路由
│   ├── main.py              # 主页面
│   ├── patterns.py          # 故障详情
│   └── api.py               # API接口
├── services/
│   └── pattern_parser.py    # Markdown解析
├── templates/                # HTML模板
│   ├── base.html            # 基础模板
│   ├── index.html           # 首页
│   ├── pattern_detail.html  # 详情页
│   └── ...
└── static/                   # 静态资源
    └── css/style.css        # 样式表
```

---

## 开发说明

### 添加新的路由
编辑 `web/routes/` 下的对应文件。

### 修改样式
编辑 `web/static/css/style.css`。

### 添加新的模板
在 `web/templates/` 目录创建新的HTML文件。

---

## 安全提示

⚠️ **警告**：
1. 所有注入脚本仅用于测试环境
2. 生产环境执行前务必充分验证
3. 准备好回滚方案
4. 避免在业务高峰时段测试
5. 建议先在隔离的测试环境验证

---

## 技术栈

- **后端**：Flask 3.0
- **模板**：Jinja2
- **Markdown解析**：python-markdown
- **语法高亮**：Highlight.js
- **缓存**：Flask-Caching
- **样式**：原生CSS（响应式设计）

---

## 反馈与贡献

如有问题或建议，请通过以下方式反馈：
- 提交Issue到项目仓库
- 发送邮件到维护团队
- 参与贡献代码

**最后更新**：2025-02-27
