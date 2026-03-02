#!/usr/bin/env python3
"""
故障模式解析服务
解析Markdown文件，提取元数据、注入脚本，转换为HTML
"""

import re
import yaml
import markdown
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class FaultPatternParser:
    """故障模式解析器"""

    # 定义有效的分类目录
    VALID_CATEGORIES = {'network', 'storage', 'memory', 'compute', 'database', 'os'}

    def __init__(self, base_path: str = "."):
        """
        初始化解析器

        Args:
            base_path: 知识库根路径
        """
        self.base_path = Path(base_path).resolve()

    def parse_fault_pattern_file(self, filepath: Path) -> Optional[Dict]:
        """
        解析故障模式Markdown文件

        Args:
            filepath: Markdown文件路径

        Returns:
            包含元数据、内容、HTML、脚本的字典，解析失败返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            return None

        # 提取YAML frontmatter
        metadata = self._extract_yaml_frontmatter(content)

        # 提取注入脚本
        injection_scripts = self._extract_injection_scripts(content)

        # 转换为HTML
        html_content = self._markdown_to_html(content)

        # 提取基本信息
        category = filepath.parent.name
        fault_id = metadata.get('fault_id', filepath.stem)
        name = metadata.get('name', filepath.stem)

        # 提取摘要（故障描述的第一段）
        description = self._extract_description(content)

        return {
            'metadata': metadata,
            'content': content,
            'html': html_content,
            'injection_scripts': injection_scripts,
            'file_path': str(filepath),
            'relative_path': str(filepath.relative_to(self.base_path)),
            'category': category,
            'fault_id': fault_id,
            'name': name,
            'description': description,
            'severity': metadata.get('severity', 'S4'),
            'frequency': metadata.get('frequency', '低'),
            'tags': metadata.get('tags', []),
            'created': metadata.get('created', ''),
            'updated': metadata.get('updated', ''),
        }

    def _extract_yaml_frontmatter(self, content: str) -> Dict:
        """
        提取YAML frontmatter

        Args:
            content: Markdown文件内容

        Returns:
            元数据字典
        """
        # 匹配 ```yaml ... ``` 代码块
        yaml_match = re.search(r'```yaml\n(.*?)\n```', content, re.DOTALL)
        if yaml_match:
            try:
                return yaml.safe_load(yaml_match.group(1)) or {}
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                return {}

        return {}

    def _extract_injection_scripts(self, content: str) -> List[Dict]:
        """
        从"## 故障注入"章节提取bash脚本

        Args:
            content: Markdown文件内容

        Returns:
            脚本列表，每个脚本包含标题、代码、语言
        """
        scripts = []

        # 查找"## 故障注入"章节
        injection_section = re.search(r'## 故障注入\s*\n(.*?)(?=##\s|\Z)', content, re.DOTALL)
        if not injection_section:
            return scripts

        section = injection_section.group(1)

        # 提取所有bash代码块
        bash_blocks = re.findall(r'```bash\n(.*?)\n```', section, re.DOTALL)

        for i, script in enumerate(bash_blocks):
            # 提取脚本标题（如果有）
            title = f'注入脚本 {i+1}'

            # 检查是否有注释标题
            first_line = script.strip().split('\n')[0]
            if first_line.strip().startswith('#'):
                title = first_line.strip().lstrip('#').strip()

            scripts.append({
                'title': title,
                'code': script.strip(),
                'language': 'bash',
                'index': i
            })

        return scripts

    def _markdown_to_html(self, content: str) -> str:
        """
        将Markdown转换为HTML

        Args:
            content: Markdown内容

        Returns:
            HTML字符串
        """
        md = markdown.Markdown(
            extensions=[
                'fenced_code',  # 围栏代码块
                'tables',       # 表格支持
                'toc',          # 目录生成
                'nl2br',        # 换行转<br>
                'sane_lists',   # 更智能的列表
            ]
        )
        return md.convert(content)

    def _extract_description(self, content: str) -> str:
        """
        提取故障描述（从"### 定义"后的第一段文本）

        Args:
            content: Markdown内容

        Returns:
            描述文本
        """
        # 查找"### 定义"部分
        definition_match = re.search(r'### 定义\s*\n(.*?)(?=\n#{1,3}\s|\Z)', content, re.DOTALL)
        if definition_match:
            desc = definition_match.group(1).strip()
            # 移除多余的换行，保留为单行
            desc = re.sub(r'\s+', ' ', desc)
            return desc[:200] + '...' if len(desc) > 200 else desc

        return "暂无描述"

    def load_all_patterns(self) -> List[Dict]:
        """
        加载所有故障模式

        Returns:
            故障模式列表
        """
        patterns = []

        # 遍历所有分类目录
        for category_dir in self.base_path.iterdir():
            if not category_dir.is_dir():
                continue

            # 跳过非分类目录
            if category_dir.name in ['templates', 'tools', 'scripts', 'web', '__pycache__', 'venv']:
                continue

            # 查找所有.md文件
            for md_file in category_dir.glob("*.md"):
                # 跳过特殊文件
                if md_file.name.startswith('_'):
                    continue

                pattern = self.parse_fault_pattern_file(md_file)
                if pattern:
                    patterns.append(pattern)

        # 按fault_id排序
        patterns.sort(key=lambda x: x['fault_id'])
        return patterns

    def get_pattern_by_id(self, fault_id: str) -> Optional[Dict]:
        """
        根据fault_id获取故障模式

        Args:
            fault_id: 故障ID（如 FP-NETWORK-20250225-001）

        Returns:
            故障模式字典，未找到返回None
        """
        patterns = self.load_all_patterns()
        for pattern in patterns:
            if pattern['fault_id'] == fault_id:
                return pattern
        return None

    def get_patterns_by_category(self, category: str) -> List[Dict]:
        """
        根据分类获取故障模式

        Args:
            category: 分类名称

        Returns:
            该分类下的故障模式列表
        """
        patterns = self.load_all_patterns()
        return [p for p in patterns if p['category'] == category]

    def search_patterns(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        搜索故障模式

        Args:
            query: 搜索关键词
            filters: 过滤条件（category, severity, frequency等）

        Returns:
            匹配的故障模式列表
        """
        patterns = self.load_all_patterns()
        results = []

        query_lower = query.lower()

        for pattern in patterns:
            # 全文搜索
            searchable_text = ' '.join([
                pattern['name'],
                pattern['description'],
                ' '.join(pattern['tags']),
                pattern['content']
            ]).lower()

            if query and query_lower not in searchable_text:
                continue

            # 应用过滤条件
            if filters:
                if 'category' in filters and pattern['category'] != filters['category']:
                    continue
                if 'severity' in filters and pattern['severity'] != filters['severity']:
                    continue
                if 'frequency' in filters and pattern['frequency'] != filters['frequency']:
                    continue

            results.append(pattern)

        return results

    def get_categories(self) -> List[Dict]:
        """
        获取所有分类及其统计信息

        Returns:
            分类列表，每个分类包含name, count, display_name
        """
        categories = []

        # 定义分类显示名称
        display_names = {
            'network': '网络故障',
            'storage': '存储故障',
            'memory': '内存故障',
            'compute': '计算资源故障',
            'database': '数据库故障',
            'os': '操作系统故障',
        }

        patterns = self.load_all_patterns()

        # 统计每个分类的数量
        category_counts = {}
        for pattern in patterns:
            cat = pattern['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # 构建分类列表
        for cat_name, count in category_counts.items():
            categories.append({
                'name': cat_name,
                'count': count,
                'display_name': display_names.get(cat_name, cat_name.upper())
            })

        # 按count降序排序
        categories.sort(key=lambda x: x['count'], reverse=True)

        return categories

    def get_statistics(self) -> Dict:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        patterns = self.load_all_patterns()

        # 统计严重程度分布
        severity_distribution = {}
        for pattern in patterns:
            sev = pattern['severity']
            severity_distribution[sev] = severity_distribution.get(sev, 0) + 1

        # 获取最近更新
        recent_updates = sorted(
            patterns,
            key=lambda x: x['updated'],
            reverse=True
        )[:5]

        return {
            'total_patterns': len(patterns),
            'total_categories': len(self.get_categories()),
            'severity_distribution': severity_distribution,
            'recent_updates': recent_updates,
            'last_updated': max([p['updated'] for p in patterns]) if patterns else ''
        }


# 便捷函数
def get_parser(base_path: str = ".") -> FaultPatternParser:
    """获取解析器实例"""
    return FaultPatternParser(base_path)
