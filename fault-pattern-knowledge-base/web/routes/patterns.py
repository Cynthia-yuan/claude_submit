#!/usr/bin/env python3
"""
故障模式详情路由
显示单个故障模式的详细信息
"""

from flask import Blueprint, render_template, abort

from web.config import config
from web.services.pattern_parser import get_parser

patterns_bp = Blueprint('patterns', __name__)


@patterns_bp.route('/pattern/<fault_id>')
def pattern_detail(fault_id):
    """
    故障模式详情页

    Args:
        fault_id: 故障ID，如 FP-NETWORK-20250225-001
    """
    parser = get_parser(config.base_path)

    # 获取故障模式
    pattern = parser.get_pattern_by_id(fault_id)

    if not pattern:
        abort(404)

    # 获取所有分类（用于侧边栏）
    categories = parser.get_categories()

    # 提取相关故障模式（同分类的其他故障）
    related_patterns = [
        p for p in parser.get_patterns_by_category(pattern['category'])
        if p['fault_id'] != fault_id
    ][:5]

    return render_template('pattern_detail.html',
                           pattern=pattern,
                           categories=categories,
                           related_patterns=related_patterns)


@patterns_bp.route('/script/<fault_id>/download')
def download_script(fault_id):
    """
    下载注入脚本

    Args:
        fault_id: 故障ID
    """
    from flask import send_file, Response
    import io

    parser = get_parser(config.base_path)
    pattern = parser.get_pattern_by_id(fault_id)

    if not pattern or not pattern['injection_scripts']:
        abort(404)

    # 合并所有脚本
    all_scripts = '\n\n'.join([
        f"# {script['title']}\n{script['code']}"
        for script in pattern['injection_scripts']
    ])

    # 创建文件
    script_file = io.BytesIO()
    script_file.write(all_scripts.encode('utf-8'))
    script_file.seek(0)

    return Response(
        all_scripts,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename={fault_id}.sh'
        }
    )
