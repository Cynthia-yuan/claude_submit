# 系统版本差异文档

## 5.1 接口变更

### 5.1.1 概述

本节描述系统接口的主要变更。

### 5.1.2 核心接口

#### 5.1.2.1 接口差异说明

本章节记录了两个版本之间的核心接口差异，包括删除和修改的接口。

| 变更类型 | 接口名称 | 变更前签名 | 变更后签名 | 影响 | 备注 |
|---------|---------|-----------|-----------|------|------|
| 接口删除 | old_api_func | void old_api_func(int) | - | 核心功能 | 已废弃，使用新接口替代 |
| 接口修改 | data_processor | void process(data_t*) | void process(data_t*, int flags) | 一般 | 增加flags参数 |
| 接口修改 | config_loader | int load_config(const char*) | int load_config(const char*, mode_t) | 一般 | 增加权限参数 |
| 接口删除 | legacy_helper | int helper() | - | 低 | 移除辅助函数 |

这些变更会影响现有系统的兼容性，请参考迁移指南。

#### 5.1.2.2 兼容性说明

后续版本将保持API兼容性...

### 5.1.3 其他变更

其他接口变更内容...

## 5.2 命令变更

### 5.2.1 删除的命令

| 命令名称 | 原路径 | 替代命令 | 备注 |
|---------|-------|---------|------|
| old_cmd | /usr/bin/old_cmd | new_cmd | 已迁移 |
| legacy_tool | /usr/sbin/legacy_tool | - | 无替代 |

### 5.2.2 新增命令

...
