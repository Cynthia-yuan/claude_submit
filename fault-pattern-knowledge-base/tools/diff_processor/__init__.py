#!/usr/bin/env python3
"""
差异文档处理器模块

用于处理 Excel 差异文档，识别删除命令、删除文件、接口变更等，
生成结构化的 Markdown 报告。
"""

from .processor import DiffDocumentProcessor

__version__ = "1.0.0"
__all__ = ["DiffDocumentProcessor"]
