"""
章节信息提取工具

从 Word 文档中提取指定章节的内容，识别表格并按类型分类输出
"""

from .section_extractor import SectionExtractor

__all__ = ['SectionExtractor']
