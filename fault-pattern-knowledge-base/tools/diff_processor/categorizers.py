#!/usr/bin/env python3
"""
变更分类逻辑
用于将 Excel 中的变更按类型分类
"""

from typing import Dict, List, Any
import pandas as pd
import numpy as np


# 支持的变更类型
CHANGE_TYPES = [
    "删除命令",
    "删除文件",
    "接口修改",
    "接口删除"
]


def categorize_changes(df: pd.DataFrame) -> Dict[str, List[Dict]]:
    """
    将变更按类型分类

    Args:
        df: 包含变更数据的 pandas DataFrame

    Returns:
        分类后的字典，键为变更类型，值为该类型的变更列表
    """
    categorized = {
        "删除命令": [],
        "删除文件": [],
        "接口修改": [],
        "接口删除": []
    }

    # 遍历每一行
    for idx, row in df.iterrows():
        change_type = str(row.get("变更类型", "")).strip()

        # 跳过空类型
        if not change_type or change_type == "nan":
            continue

        # 根据变更类型分类
        category = _determine_category(row, change_type)

        if category and category in categorized:
            categorized[category].append(_row_to_dict(row))

    return categorized


def _determine_category(row: pd.Series, change_type: str) -> str:
    """
    根据行数据确定变更类别

    Args:
        row: pandas Series，表示一行数据
        change_type: 变更类型字符串

    Returns:
        变更类别名称，如果不属于任何类别则返回 None
    """
    # 明确的变更类型
    if change_type in CHANGE_TYPES:
        return change_type

    # 模糊匹配：包含关键词
    if "命令" in change_type and "删除" in change_type:
        return "删除命令"

    if "文件" in change_type and "删除" in change_type:
        return "删除文件"

    # 接口相关
    if "接口" in change_type:
        # 检查变更后内容是否存在且非空
        after_content = row.get("变更后内容")
        if pd.notna(after_content) and str(after_content).strip():
            return "接口修改"
        else:
            return "接口删除"

    # 无法分类，返回 None
    return None


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    """
    将 pandas Series 转换为字典

    Args:
        row: pandas Series

    Returns:
        字典格式的行数据
    """
    result = {}

    # 常见列名映射
    column_mapping = {
        "变更类型": "变更类型",
        "命令/接口名称": "名称",
        "命令名称": "名称",
        "接口名称": "名称",
        "变更前内容": "变更前",
        "变更后内容": "变更后",
        "文件路径": "文件路径",
        "优先级": "优先级",
        "影响": "影响",
        "备注": "备注",
        "说明": "备注"
    }

    # 提取数据
    for excel_col, dict_key in column_mapping.items():
        if excel_col in row.index:
            value = row[excel_col]
            # 转换 NaN 为空字符串
            if pd.isna(value):
                value = ""
            result[dict_key] = str(value).strip()

    # 保留原始变更类型
    if "变更类型" in row.index:
        result["变更类型"] = str(row["变更类型"]).strip()

    # 如果没有找到名称列，尝试使用其他列
    if "名称" not in result or not result["名称"]:
        # 尝试从其他可能的列获取名称
        for col in row.index:
            if any(keyword in col for keyword in ["名称", "命令", "接口", "command", "name", "interface"]):
                if col != "变更类型":
                    value = row[col]
                    if pd.notna(value) and str(value).strip():
                        result["名称"] = str(value).strip()
                        break

    # 如果仍然没有名称，使用变更类型作为名称
    if "名称" not in result or not result["名称"]:
        result["名称"] = result.get("变更类型", "未知")

    return result


def validate_change_type(change_type: str) -> bool:
    """
    验证变更类型是否有效

    Args:
        change_type: 变更类型字符串

    Returns:
        是否为有效的变更类型
    """
    # 不支持新增类型
    if "新增" in change_type:
        return False

    # 检查是否在支持的类型列表中
    return change_type in CHANGE_TYPES
