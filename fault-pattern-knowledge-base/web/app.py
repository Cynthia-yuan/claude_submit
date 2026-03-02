#!/usr/bin/env python3
"""
Flask应用入口
创建和配置Flask应用
"""

import os
from pathlib import Path
from flask import Flask, render_template
from flask_caching import Cache

from .config import config

# 初始化缓存
cache = Cache()


def create_app(config_file=None):
    """
    应用工厂函数

    Args:
        config_file: 配置文件路径（可选）

    Returns:
        Flask应用实例
    """
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # 加载配置
    if config_file:
        app.config.from_object(Config(config_file))
    else:
        # 使用默认配置
        app.config['SECRET_KEY'] = config.secret_key
        app.config['DEBUG'] = config.debug

    # 配置缓存
    if config.cache_enabled:
        app.config['CACHE_TYPE'] = 'SimpleCache'
        app.config['CACHE_DEFAULT_TIMEOUT'] = config.cache_timeout
        cache.init_app(app)

    # 注册蓝图
    _register_blueprints(app)

    # 注册错误处理器
    _register_error_handlers(app)

    # 注册上下文处理器
    _register_context_processors(app)

    return app


def _register_blueprints(app):
    """注册所有蓝图"""
    from web.routes.main import main_bp
    from web.routes.patterns import patterns_bp
    from web.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(patterns_bp)
    app.register_blueprint(api_bp, url_prefix='/api')


def _register_error_handlers(app):
    """注册错误处理器"""

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500


def _register_context_processors(app):
    """注册上下文处理器"""

    @app.context_processor
    def inject_config():
        """注入配置到模板"""
        return {
            'app_name': config.app_name,
            'debug': config.debug,
        }


# 开发服务器启动
def run_dev_server():
    """运行开发服务器"""
    app = create_app()

    print(f"""
    ╔════════════════════════════════════════════╗
    ║   Linux故障模式知识库 Web界面              ║
    ╠════════════════════════════════════════════╣
    ║   访问地址: http://localhost:5000           ║
    ║   工作目录: {config.base_path:20}     ║
    ╚════════════════════════════════════════════╝
    """)

    app.run(
        host=config.server_host,
        port=config.server_port,
        debug=config.debug
    )


if __name__ == '__main__':
    run_dev_server()
