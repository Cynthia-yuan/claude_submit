#!/bin/bash
# Linux故障模式知识库 Web服务器启动脚本

# 项目目录
PROJECT_DIR="/Users/yuanlulu/vscode_claude/fault-pattern-knowledge-base"

echo "=========================================="
echo "  Linux故障模式知识库 Web界面"
echo "=========================================="
echo ""

# 切换到项目目录
cd "$PROJECT_DIR" || exit 1

# 检查Python依赖
echo "检查依赖..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Flask未安装，正在安装..."
    pip3 install --user Flask markdown PyYAML python-frontmatter Flask-Caching Pygments
fi

# 生成索引
echo "生成知识库索引..."
python3 templates/fault_pattern_manager.py --index --base-path . 2>/dev/null

echo ""
echo "✓ 服务器启动中..."
echo "✓ 访问地址: http://127.0.0.1:5001"
echo "✓ 按 Ctrl+C 停止服务器"
echo ""
echo "=========================================="
echo ""

# 使用Python直接启动（避免路径问题）
python3 -c "
import sys
import os
os.chdir('$PROJECT_DIR')
sys.path.insert(0, '$PROJECT_DIR')

from web.app import create_app
app = create_app()
app.run(host='127.0.0.1', port=5001, debug=False)
"
