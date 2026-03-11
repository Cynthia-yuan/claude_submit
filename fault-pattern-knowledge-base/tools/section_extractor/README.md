# 章节信息提取工具

从 Word 文档中提取指定章节的内容，识别表格并按类型分类输出（删除、新增、变更）。

## 功能特性

- 从 Word 文档 (.docx) 提取指定章节
- 自动识别和解析表格
- 按类型分类：删除、新增、变更
- 简单文本输出，易于阅读

## 安装

```bash
pip install python-docx
```

或更新项目依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 提取章节并输出到终端
python3 section_extractor.py document.docx 5.1.2.1

# 保存到文本文件
python3 section_extractor.py document.docx 5.1.2.1 -o output.txt

# 显示详细日志
python3 section_extractor.py document.docx 5.1.2.1 -v
```

### 输入文档格式

Word 文档中的章节标题格式：

```
5.1.2.1 接口差异说明

本章节记录了两个版本之间的接口差异。

表格内容...
```

### 输出格式

```
================================================================================
差异分类结果
================================================================================

【删除】共 2 项
--------------------------------------------------------------------------------
 1. 接口删除 | old_api_func | void old_api_func(int) | - | 核心功能
 2. 接口删除 | legacy_helper | int helper() | - | 低

【新增】共 0 项

【变更】共 2 项
--------------------------------------------------------------------------------
 1. 接口修改 | data_processor | void process(data_t*) | void process(data_t*, int flags) | 一般
 2. 接口修改 | config_loader | int load_config(const char*) | int load_config(const char*, mode_t) | 一般

================================================================================
总计: 删除 2 项, 新增 0 项, 变更 2 项
================================================================================
```

## 分类规则

工具会自动查找表格中的"类型"或"变更类型"列，并根据关键词分类：

- **删除**: 包含"删除"、"移除"、"废弃"等关键词
- **新增**: 包含"新增"、"添加"、"引入"等关键词
- **变更**: 包含"修改"、"变更"、"更新"等关键词

## Python API 使用

```python
from section_extractor import SectionExtractor

# 创建提取器
extractor = SectionExtractor()

# 从 Word 文档提取
result = extractor.extract_from_file('document.docx', '5.1.2.1')

if result:
    print(f"章节: {result['section_id']}")
    print(f"标题: {result['title']}")

    # 打印分类结果
    extractor.print_categorized(result['categorized'])

    # 访问分类数据
    deleted = result['categorized']['删除']
    added = result['categorized']['新增']
    changed = result['categorized']['变更']
```

## 命令行参数

```
usage: section_extractor.py [-h] [-o OUTPUT] [-v] file section

从 Word 文档中提取指定章节并分类输出

positional arguments:
  file                  Word 文档路径 (.docx)
  section               章节编号，如 5.1.2.1

optional arguments:
  -h, --help            显示帮助信息
  -o OUTPUT, --output OUTPUT  输出到文本文件
  -v, --verbose         显示详细信息
```

## 使用场景

### 1. 快速查看差异摘要

```bash
python3 section_extractor.py 差异文档.docx 5.1.2
```

直接在终端查看删除、新增、变更的摘要。

### 2. 保存分类结果

```bash
python3 section_extractor.py 差异文档.docx 5.1.2 -o 差异分类.txt
```

将分类结果保存到文件，便于后续处理或分享。

### 3. 作为其他工具的输入

提取的分类数据可以作为后续验证、测试等工具的输入。

## 限制

- 仅支持 .docx 格式（Word 2007+）
- 章节标题必须以编号开头（如 "5.1.2.1 标题"）
- 表格需要有"类型"或"变更类型"列才能自动分类

## 许可证

MIT License
