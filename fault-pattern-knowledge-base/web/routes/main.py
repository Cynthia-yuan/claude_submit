#!/usr/bin/env python3
"""
主页面路由
首页、分类页面、搜索页面
"""

from flask import Blueprint, render_template, request, redirect, url_for

from web.config import config
from web.services.pattern_parser import get_parser

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页 - 显示分类概览和统计信息"""
    parser = get_parser(config.base_path)

    # 获取统计信息
    statistics = parser.get_statistics()

    # 获取分类列表
    categories = parser.get_categories()

    # 获取最近更新的故障模式
    recent_updates = statistics.get('recent_updates', [])

    return render_template('index.html',
                           categories=categories,
                           statistics=statistics,
                           recent_updates=recent_updates)


@main_bp.route('/category/<category_name>')
def category(category_name):
    """分类页面 - 显示该分类下的所有故障模式"""
    parser = get_parser(config.base_path)

    # 获取该分类的故障模式
    patterns = parser.get_patterns_by_category(category_name)

    # 获取所有分类（用于侧边栏）
    categories = parser.get_categories()

    # 分类显示名称
    display_names = {
        'network': '网络故障',
        'storage': '存储故障',
        'memory': '内存故障',
        'compute': '计算资源故障',
        'database': '数据库故障',
        'os': '操作系统故障',
    }
    category_display = display_names.get(category_name, category_name.upper())

    return render_template('category.html',
                           category_name=category_name,
                           category_display=category_display,
                           patterns=patterns,
                           categories=categories)


@main_bp.route('/search')
def search():
    """搜索页面"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    severity = request.args.get('severity', '')

    parser = get_parser(config.base_path)

    results = []
    if query:
        # 构建过滤条件
        filters = {}
        if category:
            filters['category'] = category
        if severity:
            filters['severity'] = severity

        # 执行搜索
        results = parser.search_patterns(query, filters)

    # 获取所有分类（用于过滤器）
    categories = parser.get_categories()

    return render_template('search.html',
                           query=query,
                           results=results,
                           categories=categories,
                           filters={'category': category, 'severity': severity})


@main_bp.route('/patterns')
def patterns_list():
    """所有故障模式列表页面"""
    parser = get_parser(config.base_path)

    # 获取所有故障模式
    patterns = parser.load_all_patterns()

    # 获取分类
    categories = parser.get_categories()

    return render_template('patterns_list.html',
                           patterns=patterns,
                           categories=categories)
