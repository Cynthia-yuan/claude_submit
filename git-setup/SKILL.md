---
name: git-setup
description: 在新机器上快速设置开发环境。包括克隆 git 仓库、配置 Git 环境、安装项目依赖和配置开发工具。适用于首次部署或在多台机器上同步开发环境。
---

# Git Setup Skill

## 功能说明

在新机器上自动完成开发环境配置，包括：
1. 检查系统环境（Git、Python、Node.js 等）
2. 克隆指定的 git 仓库
3. 配置 Git 用户信息和 SSH 密钥
4. 安装项目依赖
5. 配置开发环境

## 执行步骤

### 第一步：检查系统环境

1. **检查 Git 是否安装**
   - 运行 `git --version`
   - 如果未安装，提示用户安装 Git
   - macOS: `brew install git`
   - Ubuntu/Debian: `sudo apt-get install git`
   - Windows: 下载安装包 https://git-scm.com/download/win

2. **检查 Python 是否安装**（项目需要）
   - 运行 `python3 --version`
   - 如果未安装，提示用户安装 Python
   - macOS: `brew install python3`
   - Ubuntu/Debian: `sudo apt-get install python3 python3-pip`
   - Windows: 下载安装包 https://www.python.org/downloads/

3. **检查 pip 和 venv**
   - 运行 `pip3 --version`
   - 运行 `python3 -m venv --help`

### 第二步：克隆 Git 仓库

1. **确认仓库信息**
   - 询问用户仓库 URL（默认：git@github.com:Cynthia-yuan/claude_submit.git）
   - 询问目标目录（默认：当前目录或 ~/vscode_claude）

2. **执行克隆操作**
   ```bash
   git clone <仓库-url> <目标目录>
   cd <目标目录>
   ```

3. **验证克隆成功**
   - 运行 `git status` 确认仓库状态
   - 显示分支信息和最新提交

### 第三步：配置 Git 用户信息

1. **询问用户 Git 配置**
   - GitHub 用户名（例如：Cynthia-yuan）
   - GitHub 邮箱（例如：user@example.com）

2. **配置 Git**
   ```bash
   git config --global user.name "用户名"
   git config --global user.email "邮箱"
   ```

3. **验证配置**
   - 运行 `git config --global user.name`
   - 运行 `git config --global user.email`

### 第四步：配置 SSH 密钥（可选）

1. **检查现有 SSH 密钥**
   - 运行 `ls ~/.ssh/id_*.pub`
   - 如果存在，询问是否使用现有密钥

2. **生成新的 SSH 密钥**（如果需要）
   ```bash
   ssh-keygen -t ed25519 -C "邮箱" -f ~/.ssh/id_ed25519 -N ""
   ```

3. **启动 ssh-agent 并添加密钥**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

4. **显示公钥**
   - 运行 `cat ~/.ssh/id_ed25519.pub`
   - 提供添加到 GitHub 的步骤说明

5. **测试 SSH 连接**
   - 运行 `ssh -T git@github.com`
   - 确认看到成功消息

6. **切换远程仓库为 SSH**
   ```bash
   git remote set-url origin git@github.com:用户名/仓库名.git
   ```

### 第五步：安装项目依赖

1. **安装 Python 依赖**
   - 进入 `fault-pattern-knowledge-base` 目录
   - 创建虚拟环境：
     ```bash
     python3 -m venv venv
     source venv/bin/activate  # Linux/macOS
     # 或
     venv\Scripts\activate  # Windows
     ```
   - 安装依赖：
     ```bash
     pip install -r requirements.txt
     ```

2. **检查其他依赖**
   - 查找项目中的 `package.json`（Node.js 项目）
   - 查找 `Gemfile`（Ruby 项目）
   - 查找 `go.mod`（Go 项目）
   - 根据需要安装对应依赖

3. **验证安装**
   - 运行 `pip list` 查看已安装的包
   - 尝试导入主要模块确认安装成功

### 第六步：配置开发环境

1. **配置 IDE**（可选）
   - 推荐安装 VSCode
   - 安装相关扩展（Python、GitLens 等）

2. **配置环境变量**（如果需要）
   - 检查 `.env.example` 或 `.env.local.example`
   - 复制为 `.env` 或 `.env.local`
   - 提示用户填写必要的环境变量

3. **运行项目测试**（如果可能）
   - 查找项目中的测试命令（如 `npm test`、`pytest` 等）
   - 运行测试验证环境配置正确

### 第七步：验证配置

运行以下命令验证所有配置：

1. **验证 Git**
   ```bash
   git config --global --list
   git remote -v
   git log --oneline -1
   ```

2. **验证 Python 环境**
   ```bash
   python3 --version
   pip --version
   pip list | grep -i flask
   ```

3. **验证 SSH 连接**
   ```bash
   ssh -T git@github.com
   ```

4. **验证项目结构**
   ```bash
   ls -la
   ```

## 注意事项

- **权限问题**：某些操作可能需要 sudo 权限（Linux/macOS）
- **网络问题**：克隆仓库和安装依赖需要稳定的网络连接
- **防火墙**：确保 Git (SSH/HTTPS) 端口未被阻止
- **磁盘空间**：确保有足够的磁盘空间存储仓库和依赖
- **Windows 兼容性**：在 Windows 上使用 Git Bash 或 PowerShell，注意命令差异

## 常见问题

1. **Git clone 失败**
   - 检查网络连接
   - 确认仓库 URL 正确
   - 如果使用 SSH，确保密钥已添加到 GitHub

2. **pip install 失败**
   - 更新 pip：`pip install --upgrade pip`
   - 使用国内镜像源（如果在中国）：
     ```bash
     pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
     ```

3. **SSH 连接失败**
   - 确认密钥已添加到 ssh-agent
   - 检查 GitHub SSH 设置中是否已添加公钥
   - 尝试使用 HTTPS 方式克隆

4. **Python 版本不兼容**
   - 检查项目要求的 Python 版本
   - 使用 pyenv 或 conda 管理多个 Python 版本

## 触发关键词

用户可能使用以下方式触发此 skill：
- `/git-setup`
- "在新机器上设置项目"
- "setup dev environment"
- "clone and setup"
- "配置开发环境"
- "部署项目"