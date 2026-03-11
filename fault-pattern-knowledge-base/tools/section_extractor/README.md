# 章节信息提取工具

从文档中提取指定章节（如"5.1.2.1"）的内容，识别表格并输出结构化JSON数据。

## 功能特性

- 提取指定章节的完整内容
- 自动识别和解析表格
- 支持Markdown格式表格
- 输出结构化JSON数据
- 可作为后续处理命令的输入

## 安装

无需额外依赖，使用Python标准库即可。

## 使用方法

### 基本用法

```bash
# 提取章节信息并输出到终端
python section_extractor.py document.md 5.1.2.1

# 保存到JSON文件
python section_extractor.py document.md 5.1.2.1 -o section_5.1.2.1.json

# 显示详细日志
python section_extractor.py document.md 5.1.2.1 -v
```

### 输入文档格式

支持的文档格式示例：

```
# 其他内容...

5.1.2.1 接口差异说明

本章节记录了两个版本之间的接口差异。

| 变更类型 | 接口名称 | 变更前签名 | 变更后签名 | 影响 |
|---------|---------|-----------|-----------|------|
| 接口删除 | old_func | void old_func() | - | 核心功能 |
| 接口修改 | new_func | void new_func(int) | void new_func(int, char*) | 一般 |

5.1.2.2 其他内容...
```

### 输出格式

输出的JSON格式：

```json
{
  "section_id": "5.1.2.1",
  "title": "接口差异说明",
  "content": "5.1.2.1 接口差异说明\n\n本章节记录了...",
  "tables": [
    {
      "headers": ["变更类型", "接口名称", "变更前签名", "变更后签名", "影响"],
      "rows": [
        ["接口删除", "old_func", "void old_func()", "-", "核心功能"],
        ["接口修改", "new_func", "void new_func(int)", "void new_func(int, char*)", "一般"]
      ],
      "row_count": 2,
      "column_count": 5
    }
  ],
  "table_count": 1
}
```

## Python API 使用

```python
from section_extractor import SectionExtractor

# 创建提取器
extractor = SectionExtractor()

# 从文件提取
section_info = extractor.extract_from_file('document.md', '5.1.2.1')

# 或从内容提取
with open('document.md') as f:
    content = f.read()
section_info = extractor.extract_from_content(content, '5.1.2.1')

# 转换为字典
data = extractor.to_dict(section_info)
print(data)

# 转换为JSON
json_str = extractor.to_json(section_info)

# 访问表格数据
for table in section_info.tables:
    print(f"表头: {table.headers}")
    for row in table.rows:
        print(f"  {row}")
```

## 支持的表格格式

1. **Markdown表格**（带分隔线）
```
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
```

2. **管道符表格**（简单格式）
```
| 列1 | 列2 | 列3 |
| 数据1 | 数据2 | 数据3 |
```

## 使用场景

### 1. 作为参数传递给后续处理命令

```bash
# 提取章节信息
json_data=$(python section_extractor.py document.md 5.1.2.1)

# 传递给其他命令
echo "$json_data" | python process_diff.py

# 或保存后使用
python section_extractor.py document.md 5.1.2.1 -o diff_data.json
python validate_diff.py diff_data.json
```

### 2. 在Python脚本中使用

```python
import json
from section_extractor import SectionExtractor

# 提取
extractor = SectionExtractor()
section = extractor.extract_from_file('doc.md', '5.1.2.1')

# 处理
for table in section.tables:
    if '变更类型' in table.headers:
        # 处理变更表格
        for row in table.rows:
            change_type = row[table.headers.index('变更类型')]
            # ...处理逻辑
```

## 限制

- 仅支持编号格式的章节标题（如 5.1.2.1）
- 表格必须使用管道符（|）分隔
- 不支持嵌套表格

## 许可证

MIT License
