#!/usr/bin/env python3
"""
配置管理
从config.yaml加载应用配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """应用配置类"""

    def __init__(self, config_file: str = None):
        """
        加载配置

        Args:
            config_file: 配置文件路径
        """
        if config_file is None:
            # 默认配置文件路径
            current_dir = Path(__file__).parent.parent
            config_file = current_dir / "config.yaml"

        self.config_file = Path(config_file)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        if not self.config_file.exists():
            # 返回默认配置
            return self._get_default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return self._process_env_vars(config)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
            return self._get_default_config()

    def _process_env_vars(self, config: Dict) -> Dict:
        """处理环境变量替换"""
        def process_value(value):
            if isinstance(value, str):
                # 替换 ${VAR} 格式的环境变量
                if value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    return os.getenv(env_var, value)
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            return value

        return process_value(config)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'app': {
                'name': 'Linux故障模式知识库',
                'debug': True,
                'secret_key': 'dev-secret-key-change-in-production'
            },
            'paths': {
                'base_path': '.',
                'index_file': 'INDEX.md'
            },
            'features': {
                'enable_search': True,
                'enable_cache': True
            },
            'cache': {
                'timeout': 300
            },
            'server': {
                'host': '0.0.0.0',
                'port': 5000
            }
        }

    def get(self, key: str, default=None):
        """
        获取配置值

        支持点号分隔的路径，如 'app.name'

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def app_name(self) -> str:
        """应用名称"""
        return self.get('app.name', 'Linux故障模式知识库')

    @property
    def debug(self) -> bool:
        """调试模式"""
        return self.get('app.debug', True)

    @property
    def secret_key(self) -> str:
        """密钥"""
        return self.get('app.secret_key', 'dev-secret-key')

    @property
    def base_path(self) -> str:
        """知识库根路径"""
        return self.get('paths.base_path', '.')

    @property
    def cache_enabled(self) -> bool:
        """是否启用缓存"""
        return self.get('features.enable_cache', True)

    @property
    def cache_timeout(self) -> int:
        """缓存超时时间（秒）"""
        return self.get('cache.timeout', 300)

    @property
    def search_enabled(self) -> bool:
        """是否启用搜索"""
        return self.get('features.enable_search', True)

    @property
    def server_host(self) -> str:
        """服务器主机"""
        return self.get('server.host', '0.0.0.0')

    @property
    def server_port(self) -> int:
        """服务器端口"""
        return self.get('server.port', 5000)


# 全局配置实例
config = Config()
