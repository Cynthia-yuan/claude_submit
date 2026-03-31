#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH差异验证器
读取Excel中的变更记录，通过SSH连接到两个环境进行验证
"""

import os
import sys
import json
import re
import argparse
import logging
from datetime import datetime
import paramiko
from openpyxl import load_workbook
from openpyxl.styles import PatternFill


class SSHValidator:
    """SSH环境验证器"""

    def __init__(self, excel_file, env_old=None, env_new=None, config_file=None):
        """
        初始化验证器

        Args:
            excel_file: Excel文件路径
            env_old: 旧环境配置字典 {'host': '', 'username': '', 'password': '', 'port': 22}
            env_new: 新环境配置字典 {'host': '', 'username': '', 'password': '', 'port': 22}
            config_file: 配置文件路径（可选）
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
        self.env_old = env_old
        self.env_new = env_new
        self.changes = []
        self.validation_results = []

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.logger.info(f"配置文件加载成功: {self.config_file}")
        except FileNotFoundError:
            self.logger.warning(f"配置文件不存在: {self.config_file}")
            self.config = self.get_default_config()
        except json.JSONDecodeError as e:
            self.logger.warning(f"配置文件格式错误: {e}")
            self.config = self.get_default_config()

    def get_default_config(self):
        """获取默认配置"""
        return {
            "env_old": {
                "host": "",
                "port": 22,
                "username": "",
                "password": "",
                "key_file": ""
            },
            "env_new": {
                "host": "",
                "port": 22,
                "username": "",
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

    def get_env_config(self, env_name):
        """
        获取环境配置，优先使用命令行参数，其次使用配置文件

        Args:
            env_name: 环境名称 'env_old' 或 'env_new'

        Returns:
            环境配置字典
        """
        # 命令行参数优先
        if env_name == 'env_old' and self.env_old:
            return self.env_old
        if env_name == 'env_new' and self.env_new:
            return self.env_new

        # 使用配置文件
        if self.config:
            return self.config.get(env_name, {})

        return {}

    def load_excel(self):
        """加载Excel文件中的变更记录"""
        try:
            wb = load_workbook(self.excel_file)

            # 获取所有sheet页
            all_changes = []
            sheet_names = wb.sheetnames

            for sheet_name in sheet_names:
                ws = wb[sheet_name]
                self.logger.info(f"正在读取Sheet页: {sheet_name}")

                # 检查是否有数据（检查第一行是否是表头）
                first_row = [cell.value for cell in ws[1]]
                if not first_row or first_row[0] is None:
                    continue

                # 跳过表头，从第二行开始
                for row in ws.iter_rows(min_row=2, values_only=True):
                    # 跳过空行
                    if not row or row[0] is None:
                        continue

                    # 判断变更类型（根据sheet名称或第二列）
                    if sheet_name in ['删除', '新增', '修改']:
                        change_type = sheet_name
                    elif len(row) > 1 and row[1]:
                        change_type = row[1]
                    else:
                        continue

                    all_changes.append({
                        'sheet': sheet_name,
                        'chapter': row[0] if row[0] else '',
                        'change_type': change_type,
                        'item_name': row[1] if len(row) > 1 and sheet_name not in ['删除', '新增', '修改'] else '',
                        'description': row[2] if len(row) > 2 else '',
                        'verified': row[3] if len(row) > 3 else '待验证',
                        'remark': row[4] if len(row) > 4 else ''
                    })

            self.changes = all_changes
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
        if not env_config or not env_config.get('host'):
            self.logger.warning("环境配置不完整，跳过连接")
            return None

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            key_file = env_config.get('key_file')
            password = env_config.get('password', '')

            # 优先使用密钥认证
            if key_file and os.path.exists(key_file):
                key = paramiko.RSAKey.from_private_key_file(key_file)
                client.connect(
                    hostname=env_config['host'],
                    port=env_config.get('port', 22),
                    username=env_config['username'],
                    pkey=key,
                    timeout=10
                )
            # 其次使用密码认证
            elif password:
                client.connect(
                    hostname=env_config['host'],
                    port=env_config.get('port', 22),
                    username=env_config['username'],
                    password=password,
                    timeout=10
                )
            else:
                self.logger.warning(f"未配置密钥或密码: {env_config['host']}")
                return None

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
        if not client:
            return False
        exit_code, stdout, _ = self.execute_command(client, f"test -e '{file_path}' && echo 'exists'")
        return exit_code == 0 and 'exists' in stdout

    def extract_file_path(self, description, item_name=''):
        """
        从描述中提取文件路径

        Args:
            description: 描述文本
            item_name: 变更项名称

        Returns:
            文件路径字符串
        """
        # 首先检查item_name
        if item_name:
            # 检查是否是路径
            if item_name.startswith('/') or re.match(r'^[\w\-/]+\.[\w]+$', item_name):
                return item_name

        # 从描述中提取路径
        # 匹配 / 开头的路径
        path_match = re.search(r'/[/\w\-\.\_]+', description)
        if path_match:
            path = path_match.group(0)
            # 扩展路径匹配（匹配更长的路径）
            extended_match = re.search(r'(/[/\w\-\.\_]+)', description)
            if extended_match:
                return extended_match.group(1)
            return path

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
        item_name = change.get('item_name', '')
        description = change['description']

        result = {
            'sheet': change.get('sheet', ''),
            'chapter': change['chapter'],
            'change_type': change_type,
            'item_name': item_name,
            'description': description,
            'verified': '通过',
            'remark': ''
        }

        # 提取文件路径
        file_path = self.extract_file_path(description, item_name)

        if not file_path:
            result['verified'] = '跳过'
            result['remark'] = '无法从描述中提取文件路径'
            return result

        # 根据变更类型进行验证
        if change_type == '删除':
            result = self.validate_deletion(file_path, client_old, client_new, result)
        elif change_type == '新增':
            result = self.validate_addition(file_path, client_old, client_new, result)
        elif change_type == '修改':
            result = self.validate_modification(file_path, client_old, client_new, result)
        else:
            result['verified'] = '跳过'
            result['remark'] = f'未知变更类型: {change_type}'

        return result

    def validate_deletion(self, file_path, client_old, client_new, result):
        """验证删除项"""
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

        self.logger.info(f"[删除] {file_path} - {result['verified']}")
        return result

    def validate_addition(self, file_path, client_old, client_new, result):
        """验证新增项"""
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

        self.logger.info(f"[新增] {file_path} - {result['verified']}")
        return result

    def validate_modification(self, file_path, client_old, client_new, result):
        """验证修改项"""
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

        # 加载配置
        self.load_config()

        # 获取环境配置
        env_old_config = self.get_env_config('env_old')
        env_new_config = self.get_env_config('env_new')

        # 打印环境信息
        self.logger.info(f"\n旧环境: {env_old_config.get('host', '未配置')} ({env_old_config.get('username', 'N/A')})")
        self.logger.info(f"新环境: {env_new_config.get('host', '未配置')} ({env_new_config.get('username', 'N/A')})")

        # 加载Excel
        wb = self.load_excel()

        # 如果没有有效的环境配置，跳过验证
        if not env_old_config.get('host') and not env_new_config.get('host'):
            self.logger.warning("\n环境配置不完整，跳过SSH验证")
            self.logger.warning("请使用以下方式配置环境:")
            self.logger.warning("  1. 命令行参数: --old-host / --new-host")
            self.logger.warning("  2. 配置文件: config.json")
            return

        # 创建SSH连接
        self.logger.info("\n正在连接SSH环境...")
        client_old = self.create_ssh_client(env_old_config)
        client_new = self.create_ssh_client(env_new_config)

        # 如果连接失败，使用None继续
        if not client_old:
            self.logger.warning("无法连接到旧环境，部分验证将无法执行")
        if not client_new:
            self.logger.warning("无法连接到新环境，部分验证将无法执行")

        # 验证每个变更
        self.logger.info("\n开始验证变更记录...")
        self.validation_results = []

        for i, change in enumerate(self.changes, 1):
            desc = change['description'][:50] if change['description'] else change['item_name']
            self.logger.info(f"\n[{i}/{len(self.changes)}] 验证: {desc}")
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
        # 定义样式
        fill_pass = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
        fill_fail = PatternFill(start_color='FFCDD2', end_color='FFCDD2', fill_type='solid')
        fill_warn = PatternFill(start_color='FFF9C4', end_color='FFF9C4', fill_type='solid')

        # 按sheet分组更新
        results_by_sheet = {}
        for result in self.validation_results:
            sheet_name = result.get('sheet', '')
            if sheet_name not in results_by_sheet:
                results_by_sheet[sheet_name] = []
            results_by_sheet[sheet_name].append(result)

        # 更新每个sheet
        for sheet_name, results in results_by_sheet.items():
            if sheet_name not in wb.sheetnames:
                continue

            ws = wb[sheet_name]
            row_num = 2  # 从第二行开始（跳过表头）

            for result in results:
                # 找到对应的行并更新
                for row in ws.iter_rows(min_row=row_num, values_only=False):
                    if row[0].value == result['chapter'] and row[2].value == result['description']:
                        row[3].value = result['verified']
                        row[4].value = result['remark']

                        # 根据验证结果设置样式
                        if result['verified'] == '通过':
                            row[3].fill = fill_pass
                        elif result['verified'] == '失败':
                            row[3].fill = fill_fail
                        elif result['verified'] == '警告':
                            row[3].fill = fill_warn
                        break
                row_num += 1

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


def parse_env_config(args, prefix):
    """
    解析环境配置

    Args:
        args: 命令行参数
        prefix: 'old' 或 'new'

    Returns:
        环境配置字典
    """
    config = {
        'host': getattr(args, f'{prefix}_host', None) or '',
        'port': getattr(args, f'{prefix}_port', 22),
        'username': getattr(args, f'{prefix}_user', None) or '',
        'password': getattr(args, f'{prefix}_pass', None) or '',
        'key_file': getattr(args, f'{prefix}_key', None) or ''
    }

    # 如果没有配置host，返回None
    if not config['host']:
        return None

    return config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SSH差异验证器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用配置文件
  python diff_validator.py diff_report.xlsx

  # 使用命令行指定环境
  python diff_validator.py diff_report.xlsx \\
    --old-host 192.168.1.10 --old-user root --old-pass password \\
    --new-host 192.168.1.20 --new-user root --new-pass password

  # 只验证新环境
  python diff_validator.py diff_report.xlsx \\
    --new-host 192.168.1.20 --new-user root --new-pass password
        """
    )

    parser.add_argument('excel_file', help='Excel差异报告文件路径')
    parser.add_argument('-c', '--config', help='配置文件路径')

    # 旧环境参数
    parser.add_argument('--old-host', help='旧环境主机地址')
    parser.add_argument('--old-port', type=int, default=22, help='旧环境SSH端口 (默认: 22)')
    parser.add_argument('--old-user', help='旧环境用户名')
    parser.add_argument('--old-pass', help='旧环境密码')
    parser.add_argument('--old-key', help='旧环境SSH密钥文件路径')

    # 新环境参数
    parser.add_argument('--new-host', help='新环境主机地址')
    parser.add_argument('--new-port', type=int, default=22, help='新环境SSH端口 (默认: 22)')
    parser.add_argument('--new-user', help='新环境用户名')
    parser.add_argument('--new-pass', help='新环境密码')
    parser.add_argument('--new-key', help='新环境SSH密钥文件路径')

    args = parser.parse_args()

    # 解析环境配置
    env_old = parse_env_config(args, 'old')
    env_new = parse_env_config(args, 'new')

    # 执行验证
    validator = SSHValidator(args.excel_file, env_old, env_new, args.config)
    validator.validate()


if __name__ == '__main__':
    main()
