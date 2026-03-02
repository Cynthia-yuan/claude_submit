#!/bin/bash
# Linux故障模式知识库 Web服务器启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查依赖
echo "检查Python依赖..."
python3 -c "import flask, markdown, yaml, frontmatter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "警告: 某些依赖未安装，正在安装..."
    pip3 install --user Flask markdown PyYAML python-frontmatter Flask-Caching Pygments python-dotenv gunicorn
fi

# 生成索引
echo "生成知识库索引..."
python3 templates/fault_pattern_manager.py --index --base-path .

# 启动服务器
echo ""
echo "=========================================="
echo "  Linux故障模式知识库 Web界面"
echo "=========================================="
echo ""
echo "服务器启动中..."
echo "访问地址: http://127.0.0.1:5001"
echo "按 Ctrl+C 停止服务器"
echo ""

# 使用端口5001（避免与macOS AirPlay冲突）
FLASK_APP=web/app.py python3 -m flask run --host=127.0.0.1 --port=5001
