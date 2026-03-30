#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML差异文档解析器
解析HTML格式的版本差异文档，提取变更信息并导出到Excel
"""

import os
import sys
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class DiffParser:
    """HTML差异文档解析器"""

    def __init__(self, html_file, output_file=None):
        """
        初始化解析器

        Args:
            html_file: HTML文件路径
            output_file: 输出Excel文件路径
        """
        self.html_file = html_file
        self.output_file = output_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'output',
            'diff_report.xlsx'
        )
        self.changes = []

    def load_html(self):
        """加载HTML文件"""
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                return BeautifulSoup(f.read(), 'html.parser')
        except FileNotFoundError:
            print(f"错误: 文件不存在 - {self.html_file}")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 加载HTML文件失败 - {e}")
            sys.exit(1)

    def get_chapter_path(self, element):
        """
        获取元素所在章节的路径

        Args:
            element: BeautifulSoup元素

        Returns:
            章节路径字符串，如 "5.1 交付件差异 > 5.1.1 安装包变更"
        """
        path_parts = []
        current = element

        # 向上查找所有标题元素
        while current:
            if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # 提取章节编号和标题
                text = current.get_text(strip=True)
                # 移除标签
                text = text.replace('[新增]', '').replace('[删除]', '').replace('[修改]', '')
                text = text.replace('', '').replace('', '').replace('', '')
                path_parts.append(text)
            current = current.parent

        # 反转路径（从根到叶）
        path_parts.reverse()

        # 只取最后两级章节路径
        if len(path_parts) > 2:
            path_parts = path_parts[-2:]

        return ' > '.join(path_parts) if path_parts else '未知章节'

    def extract_changes(self, soup):
        """
        提取所有带data-change属性的元素

        Args:
            soup: BeautifulSoup对象
        """
        # 查找所有带data-change属性的元素
        change_elements = soup.find_all(attrs={'data-change': True})

        for elem in change_elements:
            change_type = elem.get('data-change')
            text = elem.get_text(strip=True)

            # 跳过空内容
            if not text:
                continue

            # 获取章节路径
            chapter_path = self.get_chapter_path(elem)

            # 标准化变更类型
            change_type_map = {
                'deleted': '删除',
                'added': '新增',
                'modified': '修改'
            }
            change_type_cn = change_type_map.get(change_type, change_type)

            self.changes.append({
                'chapter': chapter_path,
                'change_type': change_type_cn,
                'description': text,
                'change_type_raw': change_type,
                'verified': '待验证',
                'remark': ''
            })

        # 同时查找表格中的变更标记（使用CSS类）
        for tag_class, change_type in [
            ('tag-deleted', '删除'),
            ('tag-added', '新增'),
            ('tag-modified', '修改')
        ]:
            tags = soup.find_all(class_=tag_class)
            for tag in tags:
                # 获取所在行
                row = tag.find_parent('tr')
                if row:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        text = cells[0].get_text(strip=True)
                        description = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                        chapter_path = self.get_chapter_path(row)

                        full_desc = f"{text}"
                        if description:
                            full_desc += f" - {description}"

                        self.changes.append({
                            'chapter': chapter_path,
                            'change_type': change_type,
                            'description': full_desc,
                            'change_type_raw': change_type.lower().replace('删除', 'deleted').replace('新增', 'added').replace('修改', 'modified'),
                            'verified': '待验证',
                            'remark': ''
                        })

    def export_to_excel(self):
        """将变更信息导出到Excel"""
        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "差异报告"

        # 定义样式
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

        # 定义列头
        headers = ['章节', '变更类型', '描述', '验证状态', '备注']

        # 写入表头
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = alignment

        # 写入数据
        for row_num, change in enumerate(self.changes, 2):
            ws.cell(row=row_num, column=1, value=change['chapter'])
            ws.cell(row=row_num, column=2, value=change['change_type'])
            ws.cell(row=row_num, column=3, value=change['description'])
            ws.cell(row=row_num, column=4, value=change['verified'])
            ws.cell(row=row_num, column=5, value=change['remark'])

            # 应用边框和对齐
            for col_num in range(1, 6):
                cell = ws.cell(row=row_num, column=col_num)
                cell.border = thin_border
                cell.alignment = alignment

                # 根据变更类型设置不同的背景色
                if col_num == 2:
                    if change['change_type'] == '删除':
                        cell.fill = PatternFill(start_color='FFCDD2', end_color='FFCDD2', fill_type='solid')
                    elif change['change_type'] == '新增':
                        cell.fill = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
                    elif change['change_type'] == '修改':
                        cell.fill = PatternFill(start_color='FFE0B2', end_color='FFE0B2', fill_type='solid')

        # 调整列宽
        column_widths = [30, 12, 50, 12, 30]
        for col_num, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_num)].width = width

        # 冻结首行
        ws.freeze_panes = 'A2'

        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # 保存文件
        wb.save(self.output_file)
        print(f"Excel报告已生成: {self.output_file}")
        print(f"共提取 {len(self.changes)} 条变更记录")

    def generate_summary(self):
        """生成变更摘要"""
        summary = {
            '删除': 0,
            '新增': 0,
            '修改': 0,
            '总计': len(self.changes)
        }

        for change in self.changes:
            change_type = change['change_type']
            if change_type in summary:
                summary[change_type] += 1

        return summary

    def parse(self):
        """执行解析"""
        print(f"正在解析: {self.html_file}")
        soup = self.load_html()
        self.extract_changes(soup)

        if not self.changes:
            print("警告: 未找到任何变更标记")
            return

        # 打印摘要
        summary = self.generate_summary()
        print("\n变更摘要:")
        for change_type, count in summary.items():
            print(f"  {change_type}: {count}")

        # 导出到Excel
        self.export_to_excel()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='HTML差异文档解析器')
    parser.add_argument('html_file', help='HTML差异文档路径')
    parser.add_argument('-o', '--output', help='输出Excel文件路径')

    args = parser.parse_args()

    # 执行解析
    diff_parser = DiffParser(args.html_file, args.output)
    diff_parser.parse()


if __name__ == '__main__':
    main()
