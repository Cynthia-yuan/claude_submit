#!/usr/bin/env python3
"""
测试章节提取工具

演示如何使用 SectionExtractor
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from section_extractor import SectionExtractor


def test_extract_section():
    """测试提取章节"""

    print("=" * 60)
    print("测试章节提取工具")
    print("=" * 60)

    # 创建提取器
    extractor = SectionExtractor()

    # 从示例文件提取
    example_file = os.path.join(
        os.path.dirname(__file__),
        'example.md'
    )

    print(f"\n从文件提取: {example_file}")
    print("-" * 60)

    # 提取章节 5.1.2.1
    section_info = extractor.extract_from_file(example_file, '5.1.2.1')

    if section_info:
        print(f"\n✓ 找到章节!")
        print(f"  编号: {section_info.section_id}")
        print(f"  标题: {section_info.title}")
        print(f"  内容长度: {len(section_info.content)} 字符")
        print(f"  表格数量: {len(section_info.tables)}")

        # 显示表格信息
        for i, table in enumerate(section_info.tables, 1):
            print(f"\n  表格 {i}:")
            print(f"    列数: {len(table.headers)}")
            print(f"    行数: {len(table.rows)}")
            print(f"    表头: {table.headers}")

            # 显示前3行数据
            print(f"    数据预览:")
            for row in table.rows[:3]:
                print(f"      {row}")
            if len(table.rows) > 3:
                print(f"      ... (还有 {len(table.rows) - 3} 行)")

        # 输出JSON
        print("\n" + "-" * 60)
        print("JSON 输出:")
        print("-" * 60)
        json_str = extractor.to_json(section_info)
        print(json_str)

        # 保存到文件
        output_file = 'test_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"\n✓ 结果已保存到: {output_file}")

        return 0
    else:
        print(f"\n✗ 未找到章节")
        return 1


def test_multiple_sections():
    """测试提取多个章节"""

    print("\n" + "=" * 60)
    print("测试提取多个章节")
    print("=" * 60)

    extractor = SectionExtractor()
    example_file = os.path.join(
        os.path.dirname(__file__),
        'example.md'
    )

    sections_to_test = ['5.1.2.1', '5.2.1']

    for section_id in sections_to_test:
        print(f"\n提取章节: {section_id}")
        print("-" * 40)

        section_info = extractor.extract_from_file(example_file, section_id)

        if section_info:
            print(f"  标题: {section_info.title}")
            print(f"  表格数: {len(section_info.tables)}")
            if section_info.tables:
                for table in section_info.tables:
                    print(f"    - {len(table.rows)} 行 x {len(table.headers)} 列")
        else:
            print(f"  未找到")


if __name__ == '__main__':
    # 运行测试
    test_extract_section()

    # 可选：测试多个章节
    # test_multiple_sections()
