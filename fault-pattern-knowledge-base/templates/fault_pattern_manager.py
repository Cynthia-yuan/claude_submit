#!/usr/bin/env python3
"""
故障模式知识库管理工具
用于创建、查询、管理故障模式记录
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class FaultPattern:
    """故障模式数据类"""

    def __init__(self, metadata: Dict):
        self.metadata = metadata
        self.content = {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "metadata": self.metadata,
            "content": self.content
        }

    def generate_filename(self) -> str:
        """生成文件名"""
        fault_id = self.metadata.get("fault_id", "UNKNOWN")
        return f"{fault_id}.md"


class FaultPatternManager:
    """故障模式知识库管理器"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.index_file = self.base_path / "index.json"

    def create_fault_pattern(self, metadata: Dict) -> FaultPattern:
        """创建新的故障模式"""
        # 自动生成ID
        if "fault_id" not in metadata:
            metadata["fault_id"] = self._generate_fault_id(metadata)

        # 设置默认值
        metadata.setdefault("created", datetime.now().strftime("%Y-%m-%d"))
        metadata.setdefault("updated", datetime.now().strftime("%Y-%m-%d"))

        return FaultPattern(metadata)

    def _generate_fault_id(self, metadata: Dict) -> str:
        """生成故障ID"""
        category = metadata.get("category", "UNKNOWN")
        date = datetime.now().strftime("%Y%m%d")
        seq = self._get_next_sequence(category, date)
        return f"FP-{category}-{date}-{seq:03d}"

    def _get_next_sequence(self, category: str, date: str) -> int:
        """获取下一个序列号"""
        # 简化版：从索引文件获取
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {"sequences": {}}

        key = f"{category}_{date}"
        seq = index.get("sequences", {}).get(key, 0) + 1
        index.setdefault("sequences", {})[key] = seq

        # 保存索引
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)

        return seq

    def save_fault_pattern(self, fault_pattern: FaultPattern, category: str) -> str:
        """保存故障模式到文件"""
        category_dir = self.base_path / category
        category_dir.mkdir(parents=True, exist_ok=True)

        filename = fault_pattern.generate_filename()
        filepath = category_dir / filename

        # 生成Markdown内容
        content = self._generate_markdown(fault_pattern)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(filepath)

    def _generate_markdown(self, fault_pattern: FaultPattern) -> str:
        """生成Markdown格式内容"""
        md = f"# {fault_pattern.metadata.get('name', '未命名故障')}\n\n"

        # 元数据
        md += "## 元数据\n\n```yaml\n"
        for key, value in fault_pattern.metadata.items():
            md += f"{key}: {value}\n"
        md += "```\n\n"

        # TODO: 根据content生成更多内容

        return md

    def search_fault_patterns(self, **filters) -> List[Dict]:
        """搜索故障模式"""
        results = []

        # 遍历所有类别目录
        for category_dir in self.base_path.iterdir():
            if category_dir.is_dir() and category_dir.name not in ['templates', 'tools', 'scripts']:
                for md_file in category_dir.glob("*.md"):
                    fault_data = self._parse_fault_pattern_file(md_file)
                    if self._match_filters(fault_data, filters):
                        results.append(fault_data)

        return results

    def _parse_fault_pattern_file(self, filepath: Path) -> Optional[Dict]:
        """解析故障模式文件"""
        # 简化版：只读取基本信息
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "file": str(filepath),
                "category": filepath.parent.name,
                "name": filepath.stem
            }
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None

    def _match_filters(self, fault_data: Dict, filters: Dict) -> bool:
        """检查是否匹配过滤条件"""
        for key, value in filters.items():
            if fault_data.get(key) != value:
                return False
        return True

    def generate_index(self) -> str:
        """生成知识库索引"""
        index = {
            "generated_at": datetime.now().isoformat(),
            "categories": {},
            "total_count": 0
        }

        for category_dir in self.base_path.iterdir():
            if category_dir.is_dir() and category_dir.name not in ['templates', 'tools', 'scripts']:
                category_name = category_dir.name
                patterns = []

                for md_file in category_dir.glob("*.md"):
                    patterns.append({
                        "file": md_file.name,
                        "name": md_file.stem
                    })

                index["categories"][category_name] = {
                    "count": len(patterns),
                    "patterns": patterns
                }
                index["total_count"] += len(patterns)

        # 保存索引
        index_path = self.base_path / "INDEX.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(self._format_index(index))

        return str(index_path)

    def _format_index(self, index: Dict) -> str:
        """格式化索引为Markdown"""
        md = "# 故障模式知识库索引\n\n"
        md += f"生成时间: {index['generated_at']}\n"
        md += f"总计: {index['total_count']} 个故障模式\n\n"

        for category, data in index['categories'].items():
            md += f"## {category.upper()}\n\n"
            md += f"数量: {data['count']}\n\n"

            for pattern in data['patterns']:
                md += f"- [{pattern['name']}]({category}/{pattern['file']})\n"

            md += "\n"

        return md


def main():
    parser = argparse.ArgumentParser(description='故障模式知识库管理工具')
    parser.add_argument('--base-path', '-b', default='.',
                        help='知识库根路径')
    parser.add_argument('--create', '-c', action='store_true',
                        help='创建新故障模式')
    parser.add_argument('--search', '-s', action='store_true',
                        help='搜索故障模式')
    parser.add_argument('--index', '-i', action='store_true',
                        help='生成索引')
    parser.add_argument('--name', '-n',
                        help='故障名称')
    parser.add_argument('--category', '-cat',
                        help='故障类别')

    args = parser.parse_args()

    manager = FaultPatternManager(args.base_path)

    if args.index:
        index_path = manager.generate_index()
        print(f"索引已生成: {index_path}")

    elif args.create:
        if not args.name or not args.category:
            print("错误: 创建故障模式需要 --name 和 --category 参数")
            return

        metadata = {
            "name": args.name,
            "category": args.category
        }

        fault_pattern = manager.create_fault_pattern(metadata)
        filepath = manager.save_fault_pattern(fault_pattern, args.category)
        print(f"故障模式已创建: {filepath}")

    elif args.search:
        filters = {}
        if args.category:
            filters['category'] = args.category

        results = manager.search_fault_patterns(**filters)
        print(f"找到 {len(results)} 个故障模式:")
        for result in results:
            print(f"  - {result['category']}: {result['name']}")


if __name__ == '__main__':
    main()
