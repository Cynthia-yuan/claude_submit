#!/usr/bin/env python3
"""
RESTful API路由
提供JSON格式的数据接口
"""

from flask import Blueprint, jsonify, request

from web.config import config
from web.services.pattern_parser import get_parser

api_bp = Blueprint('api', __name__)


@api_bp.route('/faults', methods=['GET'])
def list_faults():
    """
    列出所有故障模式

    Query Parameters:
        category: 过滤分类
        severity: 过滤严重程度
        q: 搜索关键词

    Returns:
        JSON: 故障模式列表
    """
    parser = get_parser(config.base_path)

    # 获取查询参数
    category = request.args.get('category', '')
    severity = request.args.get('severity', '')
    query = request.args.get('q', '')

    # 构建过滤条件
    filters = {}
    if category:
        filters['category'] = category
    if severity:
        filters['severity'] = severity

    # 执行查询
    if query:
        patterns = parser.search_patterns(query, filters)
    else:
        patterns = parser.load_all_patterns()
        # 应用过滤
        if filters:
            if 'category' in filters:
                patterns = [p for p in patterns if p['category'] == filters['category']]
            if 'severity' in filters:
                patterns = [p for p in patterns if p['severity'] == filters['severity']]

    # 返回简化数据
    result = [{
        'fault_id': p['fault_id'],
        'name': p['name'],
        'category': p['category'],
        'severity': p['severity'],
        'description': p['description'],
        'tags': p['tags'],
        'updated': p['updated']
    } for p in patterns]

    return jsonify({
        'success': True,
        'data': result,
        'count': len(result)
    })


@api_bp.route('/faults/<fault_id>', methods=['GET'])
def get_fault(fault_id):
    """
    获取特定故障模式

    Args:
        fault_id: 故障ID

    Returns:
        JSON: 故障模式详情
    """
    parser = get_parser(config.base_path)
    pattern = parser.get_pattern_by_id(fault_id)

    if not pattern:
        return jsonify({
            'success': False,
            'error': 'Fault pattern not found'
        }), 404

    # 返回完整数据
    return jsonify({
        'success': True,
        'data': pattern
    })


@api_bp.route('/categories', methods=['GET'])
def list_categories():
    """
    列出所有分类及统计

    Returns:
        JSON: 分类列表
    """
    parser = get_parser(config.base_path)
    categories = parser.get_categories()

    return jsonify({
        'success': True,
        'data': categories
    })


@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    获取知识库统计信息

    Returns:
        JSON: 统计信息
    """
    parser = get_parser(config.base_path)
    statistics = parser.get_statistics()

    return jsonify({
        'success': True,
        'data': statistics
    })


@api_bp.route('/scripts/<fault_id>', methods=['GET'])
def get_scripts(fault_id):
    """
    提取故障模式的注入脚本

    Args:
        fault_id: 故障ID

    Returns:
        JSON: 注入脚本列表
    """
    parser = get_parser(config.base_path)
    pattern = parser.get_pattern_by_id(fault_id)

    if not pattern:
        return jsonify({
            'success': False,
            'error': 'Fault pattern not found'
        }), 404

    return jsonify({
        'success': True,
        'data': {
            'fault_id': fault_id,
            'name': pattern['name'],
            'scripts': pattern['injection_scripts']
        }
    })
