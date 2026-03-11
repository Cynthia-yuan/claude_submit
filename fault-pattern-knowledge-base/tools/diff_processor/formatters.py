#!/usr/bin/env python3
"""
报告生成器
用于生成 Markdown 格式的差异报告
"""

from typing import Dict, List, Any


def generate_markdown_report(
    categorized: Dict[str, List[Dict]],
    analysis: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    生成 Markdown 格式的差异报告

    Args:
        categorized: 分类后的变更字典
        analysis: 影响分析结果
        metadata: 元数据

    Returns:
        Markdown 格式的报告字符串
    """
    lines = []

    # 标题和元数据
    lines.append("# 系统变更差异报告")
    lines.append("")
    lines.append(f"**生成时间**: {metadata.get('generated_at', 'N/A')}")
    lines.append(f"**源文件**: {metadata.get('source_file', 'N/A')}")
    lines.append("")

    # 执行摘要
    lines.append("---")
    lines.append("")
    lines.append("## 执行摘要")
    lines.append("")
    total = analysis.get('total_changes', 0)
    lines.append(f"本报告分析了系统的所有变更。共识别出 **{total} 项变更**，其中：")
    lines.append("")

    for category in ["删除命令", "删除文件", "接口修改", "接口删除"]:
        count = analysis['counts'].get(category, 0)
        if count > 0:
            lines.append(f"- **{category}**：{count} 项")

    lines.append("")

    # 关键发现
    high_priority = analysis.get('high_priority_count', 0)
    if high_priority > 0:
        lines.append("**关键发现：**")
        lines.append(f"- S1/S2 优先级变更：{high_priority} 项（需要优先处理）")

        # 统计影响核心功能的变更
        core_impact = 0
        for items in categorized.values():
            for item in items:
                impact = item.get('影响', '')
                if any(keyword in impact for keyword in ['核心', '关键', '重要']):
                    core_impact += 1

        if core_impact > 0:
            lines.append(f"- 影响核心功能：{core_impact} 项")

        lines.append("")

    # 生成各分类详情
    section_num = 1
    category_titles = {
        "删除命令": "删除命令",
        "删除文件": "删除文件",
        "接口修改": "接口修改",
        "接口删除": "接口删除"
    }

    for category in ["删除命令", "删除文件", "接口修改", "接口删除"]:
        items = categorized.get(category, [])
        if not items:
            continue

        lines.append("---")
        lines.append("")
        lines.append(f"## {section_num}. {category_titles.get(category, category)} ({len(items)}项)")
        lines.append("")

        if category == "删除命令":
            lines.extend(_format_deleted_commands(items))
        elif category == "删除文件":
            lines.extend(_format_deleted_files(items))
        elif category == "接口修改":
            lines.extend(_format_modified_interfaces(items))
        elif category == "接口删除":
            lines.extend(_format_deleted_interfaces(items))

        section_num += 1

    # 优先级分布
    lines.append("---")
    lines.append("")
    lines.append("## 优先级分布")
    lines.append("")

    severity_dist = analysis.get('severity_distribution', {})
    for priority in ["S1", "S2", "S3", "S4"]:
        count = severity_dist.get(priority, 0)
        if count > 0:
            descriptions = {
                "S1": "（关键）",
                "S2": "（重要）",
                "S3": "（一般）",
                "S4": "（低）"
            }
            lines.append(f"- **{priority}** {descriptions.get(priority, '')}: {count} 项")

    lines.append("")

    # 建议行动计划
    lines.append("---")
    lines.append("")
    lines.append("## 建议行动计划")
    lines.append("")
    lines.append("### 阶段 1：升级前准备（必须完成）")
    lines.append("")

    # 列出 S1 优先级的变更
    s1_items = []
    for items in categorized.values():
        for item in items:
            if item.get('优先级', 'S4') == 'S1':
                s1_items.append(item)

    if s1_items:
        for item in s1_items:
            name = item.get('名称', '未知')
            category = item.get('变更类型', '未知')
            note = item.get('备注', '')
            lines.append(f"- [ ] 处理 **{name}** ({category})")
            if note:
                lines.append(f"  - {note}")
        lines.append("")
    else:
        lines.append("- 无 S1 优先级变更")
        lines.append("")

    lines.append("### 阶段 2：升级并行处理")
    lines.append("")

    # 列出 S2 优先级的变更
    s2_items = []
    for items in categorized.values():
        for item in items:
            if item.get('优先级', 'S4') == 'S2':
                s2_items.append(item)

    if s2_items:
        for item in s2_items:
            name = item.get('名称', '未知')
            note = item.get('备注', '')
            lines.append(f"- [ ] 处理 **{name}**")
            if note:
                lines.append(f"  - {note}")
        lines.append("")
    else:
        lines.append("- 无 S2 优先级变更")
        lines.append("")

    lines.append("### 阶段 3：升级后验证")
    lines.append("")
    lines.append("- [ ] 运行完整测试套件")
    lines.append("- [ ] 验证所有接口调用")
    lines.append("- [ ] 检查日志和监控")
    lines.append("- [ ] 更新用户文档")
    lines.append("")

    # 附录
    lines.append("---")
    lines.append("")
    lines.append("## 附录")
    lines.append("")
    lines.append("### 变更分类说明")
    lines.append("")
    lines.append("- **删除命令**: 命令行工具被移除")
    lines.append("- **删除文件**: 配置文件、库文件等被删除")
    lines.append("- **接口修改**: 函数/方法签名变更")
    lines.append("- **接口删除**: 函数/方法被完全移除")
    lines.append("")

    lines.append("### 优先级定义")
    lines.append("")
    lines.append("- **S1**: 关键变更，必须处理，否则系统无法正常运行")
    lines.append("- **S2**: 重要变更，强烈建议处理，否则功能受限")
    lines.append("- **S3**: 一般变更，建议处理，可以后续优化")
    lines.append("- **S4**: 低优先级，仅需要文档更新")
    lines.append("")

    return "\n".join(lines)


def _format_deleted_commands(items: List[Dict]) -> List[str]:
    """格式化删除命令部分"""
    lines = []

    # 按优先级排序
    sorted_items = sorted(
        items,
        key=lambda x: _priority_to_int(x.get('优先级', 'S4'))
    )

    lines.append("| 命令名称 | 原路径 | 影响 | 优先级 | 备注 |")
    lines.append("|---------|-------|------|--------|------|")

    for item in sorted_items:
        name = item.get('名称', '')
        before = item.get('变更前', '')
        impact = item.get('影响', '-')
        priority = item.get('优先级', 'S4')
        note = item.get('备注', '')

        lines.append(f"| {name} | {before} | {impact} | {priority} | {note} |")

    lines.append("")

    # 添加说明
    notes = [item.get('备注', '') for item in items if item.get('备注')]
    if notes:
        lines.append("**说明：**")
        for note in notes[:3]:  # 只显示前3个说明
            lines.append(f"- {note}")
        lines.append("")

    return lines


def _format_deleted_files(items: List[Dict]) -> List[str]:
    """格式化删除文件部分"""
    lines = []

    # 按优先级排序
    sorted_items = sorted(
        items,
        key=lambda x: _priority_to_int(x.get('优先级', 'S4'))
    )

    lines.append("| 文件路径 | 用途 | 影响 | 优先级 | 备注 |")
    lines.append("|---------|------|------|--------|------|")

    for item in sorted_items:
        path = item.get('文件路径', item.get('名称', ''))
        before = item.get('变更前', '用途未知')
        impact = item.get('影响', '-')
        priority = item.get('优先级', 'S4')
        note = item.get('备注', '')

        lines.append(f"| {path} | {before} | {impact} | {priority} | {note} |")

    lines.append("")

    # 添加说明
    notes = [item.get('备注', '') for item in items if item.get('备注')]
    if notes:
        lines.append("**注意事项：**")
        for note in notes[:3]:
            lines.append(f"- {note}")
        lines.append("")

    return lines


def _format_modified_interfaces(items: List[Dict]) -> List[str]:
    """格式化接口修改部分"""
    lines = []

    # 按优先级排序
    sorted_items = sorted(
        items,
        key=lambda x: _priority_to_int(x.get('优先级', 'S4'))
    )

    lines.append("| 接口名称 | 变更前签名 | 变更后签名 | 影响 | 优先级 |")
    lines.append("|---------|-----------|-----------|------|--------|")

    for item in sorted_items:
        name = item.get('名称', '')
        before = item.get('变更前', '')
        after = item.get('变更后', '')
        impact = item.get('影响', '-')
        priority = item.get('优先级', 'S4')

        lines.append(f"| {name} | {before} | {after} | {impact} | {priority} |")

    lines.append("")

    # 添加迁移指南
    lines.append("**迁移指南：**")
    lines.append("")
    for item in sorted_items[:3]:
        name = item.get('名称', '')
        before = item.get('变更前', '')
        after = item.get('变更后', '')
        if before and after:
            lines.append("```python")
            lines.append(f"# 旧代码")
            lines.append(f"{before}")
            lines.append("")
            lines.append(f"# 新代码")
            lines.append(f"{after}")
            lines.append("```")
            lines.append("")
            break

    return lines


def _format_deleted_interfaces(items: List[Dict]) -> List[str]:
    """格式化接口删除部分"""
    lines = []

    # 按优先级排序
    sorted_items = sorted(
        items,
        key=lambda x: _priority_to_int(x.get('优先级', 'S4'))
    )

    lines.append("| 接口名称 | 原用途 | 删除原因 | 影响 | 优先级 | 替代方案 |")
    lines.append("|---------|-------|---------|------|--------|---------|")

    for item in sorted_items:
        name = item.get('名称', '')
        before = item.get('变更前', '未知用途')
        impact = item.get('影响', '-')
        priority = item.get('优先级', 'S4')
        note = item.get('备注', '无')

        lines.append(f"| {name} | {before} | {note} | {impact} | {priority} | - |")

    lines.append("")

    # 添加紧急处理建议
    high_priority_items = [item for item in items if item.get('优先级', 'S4') in ['S1', 'S2']]
    if high_priority_items:
        lines.append("**紧急处理：**")
        for item in high_priority_items:
            name = item.get('名称', '')
            note = item.get('备注', '')
            lines.append(f"- 所有使用 `{name}` 的代码必须在升级前重构")
            if note:
                lines.append(f"  - {note}")
        lines.append("")

    return lines


def _priority_to_int(priority: str) -> int:
    """将优先级转换为整数用于排序"""
    priority_map = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
    return priority_map.get(str(priority).strip(), 4)
