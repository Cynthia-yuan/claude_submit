#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH差异验证器
读取Excel中的变更记录，通过SSH连接到两个环境进行验证
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
import paramiko
from openpyxl import load_workbook
from openpyxl.styles import PatternFill


class SSHValidator:
    """SSH环境验证器"""

    def __init__(self, excel_file, config_file=None):
        """
        初始化验证器

        Args:
            excel_file: Excel文件路径
            config_file: 配置文件路径
        """
        self.excel_file = excel_file
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config.json'
        )
        self.log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'output',
            'validation.log'
        )

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.config = None
        self.changes = []
        self.validation_results = []

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.logger.info(f"配置文件加载成功: {self.config_file}")
        except FileNotFoundError:
            self.logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
            self.config = self.get_default_config()
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)

    def get_default_config(self):
        """获取默认配置"""
        return {
            "env_old": {
                "host": "old-server.example.com",
                "port": 22,
                "username": "user",
                "password": "",
                "key_file": ""
            },
            "env_new": {
                "host": "new-server.example.com",
                "port": 22,
                "username": "user",
                "password": "",
                "key_file": ""
            },
            "validation_rules": {
                "file_check_paths": ["/opt/packages", "/etc/app", "/opt/scripts"],
                "config_files": ["/etc/app/application.yml"],
                "check_commands": {
                    "jdk_version": "java -version 2>&1",
                    "mysql_version": "mysql --version"
                }
            }
        }

    def load_excel(self):
        """加载Excel文件中的变更记录"""
        try:
            wb = load_workbook(self.excel_file)
            ws = wb.active

            self.changes = []
            # 跳过表头，从第二行开始
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0]:  # 章节不为空
                    self.changes.append({
                        'chapter': row[0],
                        'change_type': row[1],
                        'description': row[2],
                        'verified': row[3] if len(row) > 3 else '待验证',
                        'remark': row[4] if len(row) > 4 else ''
                    })

            self.logger.info(f"从Excel加载了 {len(self.changes)} 条变更记录")
            return wb
        except FileNotFoundError:
            self.logger.error(f"Excel文件不存在: {self.excel_file}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"加载Excel文件失败: {e}")
            sys.exit(1)

    def create_ssh_client(self, env_config):
        """
        创建SSH客户端连接

        Args:
            env_config: 环境配置字典

        Returns:
            SSHClient对象
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if env_config.get('key_file') and os.path.exists(env_config['key_file']):
                # 使用密钥认证
                key = paramiko.RSAKey.from_private_key_file(env_config['key_file'])
                client.connect(
                    hostname=env_config['host'],
                    port=env_config.get('port', 22),
                    username=env_config['username'],
                    pkey=key,
                    timeout=10
                )
            else:
                # 使用密码认证
                client.connect(
                    hostname=env_config['host'],
                    port=env_config.get('port', 22),
                    username=env_config['username'],
                    password=env_config.get('password', ''),
                    timeout=10
                )
            self.logger.info(f"SSH连接成功: {env_config['username']}@{env_config['host']}")
            return client
        except paramiko.AuthenticationException:
            self.logger.error(f"SSH认证失败: {env_config['host']}")
            return None
        except paramiko.SSHException as e:
            self.logger.error(f"SSH连接错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            return None

    def execute_command(self, client, command):
        """
        执行SSH命令

        Args:
            client: SSHClient对象
            command: 要执行的命令

        Returns:
            (exit_code, stdout, stderr)
        """
        try:
            stdin, stdout, stderr = client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            return exit_code, stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip()
        except Exception as e:
            self.logger.error(f"执行命令失败: {command}, 错误: {e}")
            return -1, '', str(e)

    def check_file_exists(self, client, file_path):
        """
        检查文件是否存在

        Args:
            client: SSHClient对象
            file_path: 文件路径

        Returns:
            bool: 文件是否存在
        """
        exit_code, stdout, _ = self.execute_command(client, f"test -e '{file_path}' && echo 'exists'")
        return exit_code == 0 and 'exists' in stdout

    def extract_file_path(self, description):
        """
        从描述中提取文件路径

        Args:
            description: 描述文本

        Returns:
            文件路径字符串
        """
        # 尝试从描述中提取路径
        import re

        # 匹配 / 开头的路径
        path_match = re.search(r'/[/\w\-\.\_]+', description)
        if path_match:
            return path_match.group(0)

        # 检查是否是文件名
        if any(ext in description.lower() for ext in ['.tar.gz', '.jar', '.war', '.sh', '.yml', '.yaml', '.properties', '.xml', '.zip']):
            # 可能是文件名，尝试在配置的路径中查找
            return description.split()[0] if description.split() else None

        return None

    def validate_change(self, change, client_old, client_new):
        """
        验证单个变更

        Args:
            change: 变更字典
            client_old: 旧环境SSH客户端
            client_new: 新环境SSH客户端

        Returns:
            验证结果字典
        """
        change_type = change['change_type']
        description = change['description']

        result = {
            'chapter': change['chapter'],
            'change_type': change_type,
            'description': description,
            'verified': '通过',
            'remark': ''
        }

        # 根据变更类型进行验证
        if change_type == '删除':
            result = self.validate_deletion(change, client_old, client_new, result)
        elif change_type == '新增':
            result = self.validate_addition(change, client_old, client_new, result)
        elif change_type == '修改':
            result = self.validate_modification(change, client_old, client_new, result)

        return result

    def validate_deletion(self, change, client_old, client_new, result):
        """验证删除项"""
        file_path = self.extract_file_path(change['description'])

        if not file_path:
            result['verified'] = '跳过'
            result['remark'] = '无法从描述中提取文件路径'
            return result

        # 检查旧环境是否存在
        old_exists = client_old and self.check_file_exists(client_old, file_path)
        # 检查新环境是否不存在
        new_exists = client_new and self.check_file_exists(client_new, file_path)

        if old_exists and not new_exists:
            result['verified'] = '通过'
            result['remark'] = f'旧环境存在，新环境不存在 ✓'
        elif not old_exists and not new_exists:
            result['verified'] = '警告'
            result['remark'] = f'两个环境都不存在该文件'
        elif new_exists:
            result['verified'] = '失败'
            result['remark'] = f'新环境仍存在该文件，应删除'
        else:
            result['verified'] = '未知'
            result['remark'] = f'无法验证（可能是连接问题）'

        self.logger.info(f"[删除] {file_path} - {result['verified']}: {result['remark']}")
        return result

    def validate_addition(self, change, client_old, client_new, result):
        """验证新增项"""
        file_path = self.extract_file_path(change['description'])

        if not file_path:
            result['verified'] = '跳过'
            result['remark'] = '无法从描述中提取文件路径'
            return result

        # 检查旧环境是否不存在
        old_exists = client_old and self.check_file_exists(client_old, file_path)
        # 检查新环境是否存在
        new_exists = client_new and self.check_file_exists(client_new, file_path)

        if not old_exists and new_exists:
            result['verified'] = '通过'
            result['remark'] = f'新环境存在 ✓'
        elif old_exists and new_exists:
            result['verified'] = '警告'
            result['remark'] = f'两个环境都存在该文件'
        elif not new_exists:
            result['verified'] = '失败'
            result['remark'] = f'新环境不存在该文件，应新增'
        else:
            result['verified'] = '未知'
            result['remark'] = f'无法验证'

        self.logger.info(f"[新增] {file_path} - {result['verified']}: {result['remark']}")
        return result

    def validate_modification(self, change, client_old, client_new, result):
        """验证修改项"""
        file_path = self.extract_file_path(change['description'])

        if not file_path:
            result['verified'] = '跳过'
            result['remark'] = '无法从描述中提取文件路径'
            return result

        # 检查两个环境文件是否存在
        old_exists = client_old and self.check_file_exists(client_old, file_path)
        new_exists = client_new and self.check_file_exists(client_new, file_path)

        if not new_exists:
            result['verified'] = '失败'
            result['remark'] = f'新环境不存在该文件'
            return result

        # 可以添加更多的验证逻辑，比如比较文件大小、修改时间、内容等
        result['verified'] = '部分验证'
        result['remark'] = f'新环境文件存在（建议人工确认内容变更）'

        self.logger.info(f"[修改] {file_path} - {result['verified']}")
        return result

    def validate(self):
        """执行验证"""
        self.logger.info("=" * 60)
        self.logger.info("开始验证差异文档")
        self.logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        # 加载配置和Excel
        self.load_config()
        wb = self.load_excel()

        # 如果没有有效的环境配置，跳过验证
        if not self.config.get('env_old', {}).get('host') or \
           not self.config.get('env_new', {}).get('host'):
            self.logger.warning("环境配置不完整，跳过SSH验证")
            self.logger.warning("请在config.json中配置env_old和env_new的连接信息")
            return

        # 创建SSH连接
        self.logger.info("\n正在连接SSH环境...")
        client_old = self.create_ssh_client(self.config['env_old'])
        client_new = self.create_ssh_client(self.config['env_new'])

        # 如果连接失败，使用None继续
        if not client_old:
            self.logger.error("无法连接到旧环境，部分验证将无法执行")
        if not client_new:
            self.logger.error("无法连接到新环境，部分验证将无法执行")

        # 验证每个变更
        self.logger.info("\n开始验证变更记录...")
        self.validation_results = []

        for i, change in enumerate(self.changes, 1):
            self.logger.info(f"\n[{i}/{len(self.changes)}] 验证: {change['description'][:50]}")
            result = self.validate_change(change, client_old, client_new)
            self.validation_results.append(result)

        # 关闭SSH连接
        if client_old:
            client_old.close()
        if client_new:
            client_new.close()

        # 更新Excel文件
        self.update_excel(wb)

        # 生成验证摘要
        self.generate_summary()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("验证完成")
        self.logger.info(f"日志文件: {self.log_file}")
        self.logger.info("=" * 60)

    def update_excel(self, wb):
        """更新Excel文件的验证结果"""
        ws = wb.active

        # 定义样式
        fill_pass = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
        fill_fail = PatternFill(start_color='FFCDD2', end_color='FFCDD2', fill_type='solid')
        fill_warn = PatternFill(start_color='FFF9C4', end_color='FFF9C4', fill_type='solid')

        # 更新验证结果
        for row_num, result in enumerate(self.validation_results, 2):
            ws.cell(row=row_num, column=4, value=result['verified'])
            ws.cell(row=row_num, column=5, value=result['remark'])

            # 根据验证结果设置样式
            cell = ws.cell(row=row_num, column=4)
            if result['verified'] == '通过':
                cell.fill = fill_pass
            elif result['verified'] == '失败':
                cell.fill = fill_fail
            elif result['verified'] == '警告':
                cell.fill = fill_warn

        # 保存更新后的Excel
        wb.save(self.excel_file)
        self.logger.info(f"\nExcel文件已更新: {self.excel_file}")

    def generate_summary(self):
        """生成验证摘要"""
        summary = {
            '通过': 0,
            '失败': 0,
            '警告': 0,
            '跳过': 0,
            '未知': 0,
            '部分验证': 0,
            '总计': len(self.validation_results)
        }

        for result in self.validation_results:
            verified = result['verified']
            if verified in summary:
                summary[verified] += 1

        self.logger.info("\n验证摘要:")
        for status, count in summary.items():
            self.logger.info(f"  {status}: {count}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SSH差异验证器')
    parser.add_argument('excel_file', help='Excel差异报告文件路径')
    parser.add_argument('-c', '--config', help='配置文件路径')

    args = parser.parse_args()

    # 执行验证
    validator = SSHValidator(args.excel_file, args.config)
    validator.validate()


if __name__ == '__main__':
    main()
