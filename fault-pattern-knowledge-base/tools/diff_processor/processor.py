#!/usr/bin/env python3
"""
差异文档处理器
用于处理 Excel 差异文档，识别删除命令、删除文件、接口变更等
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from .categorizers import categorize_changes
from .formatters import generate_markdown_report


class DiffDocumentProcessor:
    """差异文档处理器主类"""

    # 支持的变更类型（不包括新增）
    SUPPORTED_CHANGE_TYPES = [
        "删除命令",
        "删除文件",
        "接口修改",
        "接口删除"
    ]

    # Excel 表格必需列
    REQUIRED_COLUMNS = ["变更类型"]

    # 可选列
    OPTIONAL_COLUMNS = [
        "命令/接口名称",
        "命令名称",
        "接口名称",
        "变更前内容",
        "变更后内容",
        "文件路径",
        "优先级",
        "影响",
        "备注"
    ]

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化处理器

        Args:
            config: 可选的配置字典
        """
        self.config = config or {}

    def process_excel(
        self,
        file_path: str,
        categories: Optional[List[str]] = None,
        min_severity: Optional[str] = None,
        output_format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        处理 Excel 文件并生成报告

        Args:
            file_path: Excel 文件路径
            categories: 要包含的变更类型列表（None 表示包含所有）
            min_severity: 最低优先级过滤（S1, S2, S3, S4）
            output_format: 输出格式（markdown, json）

        Returns:
            包含处理结果的字典
        """
        # 读取 Excel 文件
        df = self.read_excel(file_path)

        # 过滤不支持的新增类型
        df = self._filter_unsupported_changes(df)

        # 分类变更
        categorized = categorize_changes(df)

        # 可选：过滤类别
        if categories:
            categorized = {
                k: v for k, v in categorized.items()
                if k in categories
            }

        # 可选：过滤优先级
        if min_severity:
            categorized = self._filter_by_severity(categorized, min_severity)

        # 分析影响
        analysis = self.analyze_impact(categorized)

        # 生成报告
        report = self.generate_report(
            categorized,
            analysis,
            metadata={
                "source_file": file_path,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_changes": sum(len(items) for items in categorized.values())
            },
            format=output_format
        )

        return {
            "data": categorized,
            "analysis": analysis,
            "markdown": report if output_format == "markdown" else None,
            "json": report if output_format == "json" else None
        }

    def read_excel(self, file_path: str) -> pd.DataFrame:
        """
        读取并验证 Excel 文件

        Args:
            file_path: Excel 文件路径

        Returns:
            pandas DataFrame

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式无效或缺少必需列
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel 文件不存在: {file_path}")

        # 读取 Excel 文件
        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e:
            raise ValueError(f"无法读取 Excel 文件: {e}")

        # 验证必需列
        self._validate_columns(df)

        # 清理数据：删除全空的行
        df = df.dropna(how="all")

        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        验证 DataFrame 是否包含必需列

        Args:
            df: pandas DataFrame

        Raises:
            ValueError: 缺少必需列
        """
        missing_cols = [
            col for col in self.REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing_cols:
            raise ValueError(
                f"Excel 文件缺少必需列: {', '.join(missing_cols)}\n"
                f"必需列: {', '.join(self.REQUIRED_COLUMNS)}\n"
                f"当前列: {', '.join(df.columns)}"
            )

    def _filter_unsupported_changes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤掉不支持的变更类型（新增）

        Args:
            df: 输入 DataFrame

        Returns:
            过滤后的 DataFrame
        """
        # 过滤掉包含"新增"的变更类型
        mask = ~df["变更类型"].str.contains("新增", na=False)
        return df[mask].copy()

    def _filter_by_severity(
        self,
        categorized: Dict[str, List[Dict]],
        min_severity: str
    ) -> Dict[str, List[Dict]]:
        """
        按优先级过滤变更

        Args:
            categorized: 分类后的变更字典
            min_severity: 最低优先级（S1 最高，S4 最低）

        Returns:
            过滤后的分类字典
        """
        severity_order = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
        min_level = severity_order.get(min_severity, 4)

        filtered = {}
        for category, items in categorized.items():
            filtered_items = []
            for item in items:
                priority = item.get("优先级", "S4")
                # 如果没有优先级，默认为 S4
                if not priority or priority == "nan":
                    priority = "S4"
                level = severity_order.get(str(priority).strip(), 4)
                if level <= min_level:
                    filtered_items.append(item)
            if filtered_items:
                filtered[category] = filtered_items

        return filtered

    def analyze_impact(self, categorized: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        分析变更影响

        Args:
            categorized: 分类后的变更字典

        Returns:
            影响分析字典
        """
        # 统计各类型的数量
        counts = {
            category: len(items)
            for category, items in categorized.items()
        }

        # 统计优先级分布
        severity_distribution = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
        for items in categorized.values():
            for item in items:
                priority = item.get("优先级", "S4")
                if not priority or priority == "nan":
                    priority = "S4"
                priority = str(priority).strip()
                if priority in severity_distribution:
                    severity_distribution[priority] += 1

        # 统计总变更数
        total_changes = sum(counts.values())

        # 识别高优先级变更
        high_priority_count = (
            severity_distribution.get("S1", 0) +
            severity_distribution.get("S2", 0)
        )

        return {
            "counts": counts,
            "severity_distribution": severity_distribution,
            "total_changes": total_changes,
            "high_priority_count": high_priority_count,
            "categories": list(categorized.keys())
        }

    def generate_report(
        self,
        categorized: Dict[str, List[Dict]],
        analysis: Dict[str, Any],
        metadata: Dict[str, Any],
        format: str = "markdown"
    ) -> str:
        """
        生成格式化报告

        Args:
            categorized: 分类后的变更字典
            analysis: 影响分析结果
            metadata: 元数据
            format: 报告格式（markdown, json）

        Returns:
            格式化的报告字符串
        """
        if format == "markdown":
            return generate_markdown_report(categorized, analysis, metadata)
        elif format == "json":
            import json
            return json.dumps(
                {
                    "metadata": metadata,
                    "analysis": analysis,
                    "data": categorized
                },
                ensure_ascii=False,
                indent=2
            )
        else:
            raise ValueError(f"不支持的输出格式: {format}")


def main():
    """命令行入口点"""
    import argparse

    parser = argparse.ArgumentParser(
        description="处理差异文档，生成变更分析报告"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入的 Excel 文件路径"
    )
    parser.add_argument(
        "--output", "-o",
        default="diff_report.md",
        help="输出的报告文件路径（默认：diff_report.md）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认：markdown）"
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["S1", "S2", "S3", "S4"],
        help="最低优先级过滤（S1 最高，S4 最低）"
    )
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        help="要包含的变更类型（默认：所有支持的类型）"
    )

    args = parser.parse_args()

    # 创建处理器
    processor = DiffDocumentProcessor()

    try:
        # 处理 Excel 文件
        result = processor.process_excel(
            file_path=args.input,
            categories=args.categories,
            min_severity=args.severity,
            output_format=args.format
        )

        # 保存报告
        output_content = result.get("markdown") or result.get("json")
        if output_content:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
            print(f"✓ 报告已生成: {args.output}")
            print(f"  总变更数: {result['analysis']['total_changes']}")
            for category, count in result['analysis']['counts'].items():
                print(f"  - {category}: {count} 项")
        else:
            print("错误：未能生成报告")

    except Exception as e:
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
