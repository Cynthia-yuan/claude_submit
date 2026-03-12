# 快捷操作指南

## 方式一：使用 Skill 命令（推荐）

直接在对话中输入：

```
/extract-section
```

然后提供：
- 文档路径
- 章节编号

例如：
> 请提取 document.docx 的 5.1.2.1 章节

## 方式二：使用 Shell 脚本

```bash
# 基本用法
./extract.sh document.docx 5.1.2.1

# 保存到文件
./extract.sh document.docx 5.1.2.1 -o output.txt

# 详细日志
./extract.sh document.docx 5.1.2.1 -v
```

## 方式三：直接使用 Python

```bash
python3 section_extractor.py document.docx 5.1.2.1
```

## 快速开始

1. **将文档放到工作目录**
   ```bash
   cp your/path/document.docx .
   ```

2. **提取章节**
   ```bash
   ./extract.sh document.docx 5.1.2.1
   ```

3. **查看结果**
   工具会自动显示分类结果，如：
   ```
   【删除】共 2 项
   【变更】共 1 项
   总计: 删除 2 项, 变更 1 项
   ```

## 使用场景

### 场景 1: 快速查看差异
```bash
./extract.sh 差异文档.docx 5.1.2
```

### 场景 2: 保存结果供后续使用
```bash
./extract.sh 差异文档.docx 5.1.2 -o 5.1.2差异.txt
```

### 场景 3: 在 Python 脚本中使用
```python
from section_extractor import SectionExtractor

extractor = SectionExtractor()
result = extractor.extract_from_file('doc.docx', '5.1.2.1')
extractor.print_categorized(result['categorized'])
```
