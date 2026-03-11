#!/usr/bin/env python3
"""
章节信息提取工具

从文档中提取指定章节的内容，识别表格并输出结构化数据
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """表格信息"""
    headers: List[str]
    rows: List[List[str]]
    markdown: str


@dataclass
class SectionInfo:
    """章节信息"""
    section_id: str
    title: str
    content: str
    tables: List[TableInfo]


class SectionExtractor:
    """章节提取器"""

    def __init__(self):
        """初始化提取器"""
        # 章节编号的正则表达式模式
        # 匹配如: 5.1.2.1, 5.1.2, 5.1 等
        self.section_pattern = re.compile(
            r'^(\d+(?:\.\d+)*)(?=\s+)'
        )

    def extract_from_file(
        self,
        file_path: str,
        section_id: str
    ) -> Optional[SectionInfo]:
        """
        从文件中提取指定章节

        Args:
            file_path: 文档路径
            section_id: 章节编号，如 "5.1.2.1"

        Returns:
            章节信息，如果未找到返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return self.extract_from_content(content, section_id)

        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

    def extract_from_content(
        self,
        content: str,
        section_id: str
    ) -> Optional[SectionInfo]:
        """
        从内容中提取指定章节

        Args:
            content: 文档内容
            section_id: 章节编号

        Returns:
            章节信息
        """
        lines = content.split('\n')

        # 查找章节开始位置
        start_idx = self._find_section_start(lines, section_id)
        if start_idx is None:
            logger.warning(f"未找到章节: {section_id}")
            return None

        # 查找章节结束位置（下一个同级或更高级章节）
        end_idx = self._find_section_end(lines, start_idx, section_id)

        # 提取章节内容
        section_lines = lines[start_idx:end_idx]
        title_line = section_lines[0] if section_lines else ""

        # 提取标题（去掉章节编号）
        title = self._extract_title(title_line, section_id)

        # 提取原始内容
        raw_content = '\n'.join(section_lines)

        # 识别并提取表格
        tables = self._extract_tables(section_lines)

        return SectionInfo(
            section_id=section_id,
            title=title,
            content=raw_content,
            tables=tables
        )

    def _find_section_start(
        self,
        lines: List[str],
        section_id: str
    ) -> Optional[int]:
        """查找章节开始位置"""
        for idx, line in enumerate(lines):
            # 匹配章节编号开头的行（允许行首有Markdown标题符号#）
            match = re.match(rf'^\s*#+\s*{re.escape(section_id)}\s+(.+)', line)
            if match:
                logger.info(f"找到章节 {section_id} 在第 {idx + 1} 行")
                return idx

        return None

    def _extract_title(self, line: str, section_id: str) -> str:
        """从行中提取标题（去掉Markdown符号和章节编号）"""
        # 去掉Markdown标题符号
        line = re.sub(r'^\s*#+\s*', '', line)
        # 去掉章节编号
        title = re.sub(rf'^{re.escape(section_id)}\s+', '', line)
        return title.strip()

    def _find_section_end(
        self,
        lines: List[str],
        start_idx: int,
        section_id: str
    ) -> int:
        """查找章节结束位置"""
        # 计算当前章节级别
        current_level = len(section_id.split('.'))

        # 从开始位置后查找
        for idx in range(start_idx + 1, len(lines)):
            line = lines[idx].strip()

            # 检查是否是章节标题
            match = self.section_pattern.match(line)
            if match:
                next_section_id = match.group(0)
                next_level = len(next_section_id.split('.'))

                # 如果是同级或更高级章节，则当前章节结束
                if next_level <= current_level:
                    logger.debug(
                        f"章节 {section_id} 在第 {idx} 行结束 "
                        f"(遇到章节 {next_section_id})"
                    )
                    return idx

        # 到文件末尾
        return len(lines)

    def _extract_tables(self, lines: List[str]) -> List[TableInfo]:
        """从章节内容中提取表格"""
        tables = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 检测表格开始（管道符表格）
            if '|' in line and line.strip().startswith('|'):
                table = self._parse_pipe_table(lines, i)
                if table:
                    tables.append(table)
                    i += len(table.rows) + 2  # 跳过表格行
                    continue

            # 检测Markdown表格（有分隔线）
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if '|' in line and re.match(r'^[\|\s\-:]+$', next_line):
                    table = self._parse_markdown_table(lines, i)
                    if table:
                        tables.append(table)
                        i += len(table.rows) + 2
                        continue

            i += 1

        return tables

    def _parse_pipe_table(
        self,
        lines: List[str],
        start_idx: int
    ) -> Optional[TableInfo]:
        """解析管道符表格"""
        table_lines = []

        # 收集表格行
        for i in range(start_idx, len(lines)):
            line = lines[i]
            if '|' in line:
                table_lines.append(line)
            else:
                break

        if not table_lines:
            return None

        # 解析表头
        headers = [
            cell.strip()
            for cell in table_lines[0].split('|')
            if cell.strip()
        ]

        # 解析数据行（跳过分隔行）
        rows = []
        for line in table_lines[1:]:
            cells = [
                cell.strip()
                for cell in line.split('|')
                if cell.strip()
            ]

            # 跳过分隔行（只包含-、|、空格、:的行）
            if cells and all(re.match(r'^[\-\s\:]*$', cell) for cell in cells):
                continue

            if cells:
                rows.append(cells)

        return TableInfo(
            headers=headers,
            rows=rows,
            markdown='\n'.join(table_lines)
        )

    def _parse_markdown_table(
        self,
        lines: List[str],
        start_idx: int
    ) -> Optional[TableInfo]:
        """解析Markdown表格"""
        table_lines = [lines[start_idx]]  # 表头行

        # 跳过分隔线
        if start_idx + 1 < len(lines):
            table_lines.append(lines[start_idx + 1])

        # 收集数据行
        for i in range(start_idx + 2, len(lines)):
            line = lines[i]
            if '|' in line:
                table_lines.append(line)
            else:
                break

        # 使用管道符表格的解析逻辑
        return self._parse_pipe_table(table_lines, 0)

    def to_dict(self, section_info: SectionInfo) -> Dict[str, Any]:
        """将章节信息转换为字典"""
        return {
            'section_id': section_info.section_id,
            'title': section_info.title,
            'content': section_info.content,
            'tables': [
                {
                    'headers': table.headers,
                    'rows': table.rows,
                    'row_count': len(table.rows),
                    'column_count': len(table.headers)
                }
                for table in section_info.tables
            ],
            'table_count': len(section_info.tables)
        }

    def to_json(self, section_info: SectionInfo, indent: int = 2) -> str:
        """将章节信息转换为JSON字符串"""
        data = self.to_dict(section_info)
        return json.dumps(data, ensure_ascii=False, indent=indent)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='从文档中提取指定章节的信息'
    )
    parser.add_argument(
        'file',
        help='文档文件路径'
    )
    parser.add_argument(
        'section',
        help='章节编号，如 5.1.2.1'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出JSON文件路径'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    args = parser.parse_args()

    # 配置日志
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 提取章节
    extractor = SectionExtractor()
    section_info = extractor.extract_from_file(args.file, args.section)

    if section_info:
        # 输出JSON
        json_str = extractor.to_json(section_info)
        print(json_str)

        # 保存到文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"\n结果已保存到: {args.output}", file=__import__('sys').stderr)

        return 0
    else:
        print(f"错误: 未找到章节 {args.section}", file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
