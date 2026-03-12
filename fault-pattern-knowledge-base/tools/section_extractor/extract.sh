#!/bin/bash
# 章节提取快捷脚本
# 使用方法: ./extract.sh document.docx 5.1.2.1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/section_extractor.py"

# 检查参数
if [ $# -lt 2 ]; then
    echo "用法: $0 <文档.docx> <章节编号> [选项]"
    echo ""
    echo "示例:"
    echo "  $0 document.docx 5.1.2.1"
    echo "  $0 document.docx 5.1.2.1 -o output.txt"
    echo "  $0 document.docx 5.1.2.1 -v"
    echo ""
    echo "选项:"
    echo "  -o FILE    保存到文件"
    echo "  -v        显示详细日志"
    exit 1
fi

DOCX_FILE="$1"
SECTION_ID="$2"

# 检查文件是否存在
if [ ! -f "$DOCX_FILE" ]; then
    echo "错误: 文件不存在 - $DOCX_FILE"
    exit 1
fi

# 检查文件格式
if [[ ! "$DOCX_FILE" =~ \.docx$ ]]; then
    echo "警告: 文件不是 .docx 格式，可能无法正常解析"
fi

# 提取章节
python3 "$PYTHON_SCRIPT" "$DOCX_FILE" "$SECTION_ID" "${@:3}"
