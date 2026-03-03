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

### 第四步：配置 SSH 密钥（重要：确保 git pull 能正常工作）

#### 方式 1：使用 RSA 密钥（推荐，最兼容）

1. **检查现有 SSH 密钥**
   ```bash
   ls -la ~/.ssh/*.pub
   ```
   - 如果已有 `id_rsa.pub`，可以跳过生成步骤

2. **生成新的 RSA SSH 密钥**（如果没有）
   ```bash
   # 清理旧密钥（如果有问题）
   rm -f ~/.ssh/id_ed25519* ~/.ssh/id_rsa*

   # 生成 RSA 4096 位密钥（兼容性最好）
   ssh-keygen -t rsa -b 4096 -C "你的邮箱" -f ~/.ssh/id_rsa -N ""
   ```

3. **启动 ssh-agent 并添加密钥**
   ```bash
   # 启动 ssh-agent
   eval "$(ssh-agent -s)"

   # 添加私钥到 ssh-agent
   ssh-add ~/.ssh/id_rsa

   # 验证密钥已添加
   ssh-add -l
   ```

4. **复制公钥到剪贴板**
   ```bash
   # macOS
   cat ~/.ssh/id_rsa.pub | pbcopy

   # Linux (需要 xclip)
   cat ~/.ssh/id_rsa.pub | xclip -selection clipboard

   # 或者手动显示并复制
   cat ~/.ssh/id_rsa.pub
   ```
   **重要：只复制一行完整内容，格式如下：**
   ```
   ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC... 你的邮箱
   ```
   **不要包含：**
   - ❌ 空格或换行（除了末尾的一个换行）
   - ❌ "-----BEGIN" 或 "-----END" 标记
   - ❌ 注释或说明文字

5. **添加公钥到 GitHub**
   - 访问：https://github.com/settings/ssh/new
   - **Title**：填写机器名称（如：`MacBook-Pro`、`Desktop-PC`）
   - **Key type**：选择 `Authentication Key`
   - **Key**：直接粘贴（Cmd+V 或 Ctrl+V）
   - 点击 **"Add SSH key"**

6. **测试 SSH 连接**
   ```bash
   ssh -T git@github.com
   ```
   **成功输出：**
   ```
   Hi Cynthia-yuan! You've successfully authenticated, but GitHub does not provide shell access.
   ```
   **如果失败：**
   - 检查密钥是否正确添加到 GitHub
   - 确认使用的是正确的 GitHub 账户
   - 尝试重新生成密钥

7. **验证远程仓库配置**
   ```bash
   # 查看当前远程仓库 URL
   git remote -v

   # 如果显示 https://...，需要切换为 SSH
   git remote set-url origin git@github.com:Cynthia-yuan/claude_submit.git

   # 验证已切换
   git remote -v
   ```
   应该显示：
   ```
   origin  git@github.com:Cynthia-yuan/claude_submit.git (fetch)
   origin  git@github.com:Cynthia-yuan/claude_submit.git (push)
   ```

8. **测试 git pull**
   ```bash
   # 首次拉取远程更改
   git pull origin main --no-edit

   # 或者设置跟踪分支后直接 pull
   git branch --set-upstream-to=origin/main main
   git pull
   ```

#### 方式 2：使用 Personal Access Token + HTTPS（备用方案）

如果 SSH 配置遇到问题，可以使用 HTTPS + Token：

1. **生成 GitHub Personal Access Token**
   - 访问：https://github.com/settings/tokens
   - 点击 "Generate new token" → "Generate new token (classic)"
   - **Note**：填写 `新机器访问`
   - **Expiration**：选择过期时间
   - **Scopes**：勾选 `repo`（全部权限）
   - 点击 "Generate token"
   - **重要：复制并保存 token**（只显示一次）

2. **使用 Token 克隆或配置**
   ```bash
   # 方式 A：使用 Token 克隆
   git clone https://<token>@github.com/Cynthia-yuan/claude_submit.git

   # 方式 B：修改现有仓库为 HTTPS + Token
   git remote set-url origin https://<token>@github.com/Cynthia-yuan/claude_submit.git

   # 方式 C：使用 Git 凭据存储（推荐）
   git remote set-url origin https://github.com/Cynthia-yuan/claude_submit.git
   git pull  # 会提示输入用户名和密码
   # 用户名：GitHub 用户名
   # 密码：粘贴 Personal Access Token（不是 GitHub 密码）
   ```

3. **配置凭据缓存**（可选，避免重复输入）
   ```bash
   # macOS
   git config --global credential.helper osxkeychain

   # Linux
   git config --global credential.helper cache
   git config --global credential.helper 'cache --timeout=3600'

   # Windows
   git config --global credential.helper manager
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

### 第七步：验证配置和测试 Pull

运行以下命令验证所有配置：

1. **验证 Git 配置**
   ```bash
   # 查看 Git 用户配置
   git config --global user.name
   git config --global user.email

   # 查看远程仓库 URL
   git remote -v
   # 应该显示：git@github.com:Cynthia-yuan/claude_submit.git

   # 查看当前分支
   git branch
   git branch -vv
   ```

2. **验证 SSH 连接**
   ```bash
   ssh -T git@github.com
   # 成功输出：Hi Cynthia-yuan! You've successfully authenticated
   ```

3. **验证 Python 环境**
   ```bash
   python3 --version
   pip --version
   pip list | grep -i flask
   ```

4. **测试 git pull（重要！）**
   ```bash
   # 方法 1：直接 pull（如果已设置跟踪分支）
   git pull

   # 方法 2：指定远程和分支
   git pull origin main

   # 方法 3：设置上游分支后 pull
   git branch --set-upstream-to=origin/main main
   git pull

   # 成功输出示例：
   # Already up to date.
   # 或
   # Updating 0d81448..79e1e4c
   # Fast-forward
   #  TEST.md | 1 +
   #  1 file changed, 1 insertion(+)
   ```

5. **测试 git push（可选）**
   ```bash
   # 创建测试文件
   echo "Test from new machine" > test-new-machine.txt

   # 添加并提交
   git add test-new-machine.txt
   git commit -m "test: setup on new machine"

   # 推送到远程
   git push origin main

   # 成功输出示例：
   # To github.com:Cynthia-yuan/claude_submit.git
   #    79e1e4c..xxxxxxx  main -> main
   ```

6. **验证项目结构**
   ```bash
   ls -la
   # 应该看到：
   # .git/          (git 仓库目录)
   # .gitignore
   # bbr-vs-cubic-test/
   # fault-pattern-knowledge-base/
   # kcsan/
   # ...
   ```

7. **完整验证脚本（一键运行）**
   ```bash
   echo "=== Git 配置验证 ===" && \
   git config --global user.name && \
   git config --global user.email && \
   echo "" && \
   echo "=== 远程仓库 URL ===" && \
   git remote -v && \
   echo "" && \
   echo "=== 当前分支 ===" && \
   git branch -vv && \
   echo "" && \
   echo "=== SSH 连接测试 ===" && \
   ssh -T git@github.com 2>&1 | head -1 && \
   echo "" && \
   echo "=== 测试 git pull ===" && \
   git pull origin main && \
   echo "" && \
   echo "=== Python 环境验证 ===" && \
   python3 --version && \
   pip --version && \
   echo "" && \
   echo "✅ 所有配置验证通过！"
   ```

**如果 pull 失败，请参考"常见问题"部分的解决方案。**

## 注意事项

- **权限问题**：某些操作可能需要 sudo 权限（Linux/macOS）
- **网络问题**：克隆仓库和安装依赖需要稳定的网络连接
- **防火墙**：确保 Git (SSH/HTTPS) 端口未被阻止
- **磁盘空间**：确保有足够的磁盘空间存储仓库和依赖
- **Windows 兼容性**：在 Windows 上使用 Git Bash 或 PowerShell，注意命令差异

## 常见问题及详细解决方案

### 1. SSH 密钥显示 "Invalid" 或 "Key is invalid"

**原因：**
- 复制时包含了多余内容（空格、换行、注释等）
- 使用了不兼容的密钥类型（ed25519 在某些系统上不兼容）
- 密钥文件损坏

**完整解决方案：**

```bash
# 步骤 1：删除所有现有密钥
rm -f ~/.ssh/id_rsa* ~/.ssh/id_ed25519* ~/.ssh/id_ecdsa*

# 步骤 2：生成新的 RSA 密钥（4096 位，最兼容）
ssh-keygen -t rsa -b 4096 -C "你的邮箱" -f ~/.ssh/id_rsa -N ""

# 步骤 3：启动 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa

# 步骤 4：验证公钥格式（应该只有一行）
cat ~/.ssh/id_rsa.pub
# 正确格式：ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC... 邮箱

# 步骤 5：复制到剪贴板
cat ~/.ssh/id_rsa.pub | pbcopy  # macOS
cat ~/.ssh/id_rsa.pub | xclip -selection clipboard  # Linux

# 步骤 6：访问 GitHub 删除旧密钥并添加新密钥
# https://github.com/settings/ssh
# 删除所有旧密钥，点击 "New SSH key" 添加新密钥

# 步骤 7：测试连接
ssh -T git@github.com
# 应该看到：Hi Cynthia-yuan! You've successfully authenticated
```

**复制技巧（避免手动复制错误）：**
```bash
# macOS：直接复制到剪贴板
cat ~/.ssh/id_rsa.pub | pbcopy

# Linux：使用 xclip
sudo apt install xclip  # Debian/Ubuntu
cat ~/.ssh/id_rsa.pub | xclip -selection clipboard

# 验证剪贴板内容（macOS）
pbpaste | head -c 100
```

### 2. Git pull 失败："Could not read from remote repository"

**完整诊断和修复：**

```bash
# 诊断步骤 1：检查远程仓库 URL
git remote -v
# 期望输出：
# origin  git@github.com:Cynthia-yuan/claude_submit.git (fetch)
# origin  git@github.com:Cynthia-yuan/claude_submit.git (push)

# 如果显示 https://...，切换到 SSH
git remote set-url origin git@github.com:Cynthia-yuan/claude_submit.git

# 诊断步骤 2：验证 SSH 密钥文件
ls -la ~/.ssh/id_rsa*
ls -la ~/.ssh/id_rsa.pub
# 确保两个文件都存在

# 诊断步骤 3：检查 ssh-agent
ps aux | grep ssh-agent
# 如果没有运行，启动它：
eval "$(ssh-agent -s)"

# 诊断步骤 4：验证密钥已添加到 ssh-agent
ssh-add -l
# 如果没有显示密钥，添加它：
ssh-add ~/.ssh/id_rsa

# 诊断步骤 5：测试 SSH 连接
ssh -T git@github.com
# 成功：Hi Cynthia-yuan! You've successfully authenticated
# 失败：Permission denied (publickey) → 密钥未添加到 GitHub

# 诊断步骤 6：验证分支
git branch -vv
# 确保显示 [origin/main] 或类似跟踪信息

# 诊断步骤 7：设置上游分支（如果需要）
git branch --set-upstream-to=origin/main main

# 最后：尝试 pull
git pull origin main
```

### 3. Git clone 失败

**诊断清单：**

```bash
# 1. 检查网络连接
ping -c 3 github.com

# 2. 检查 Git 安装
git --version

# 3. 测试 SSH 连接
ssh -T git@github.com

# 4. 验证仓库 URL（确保格式正确）
# 正确：git@github.com:Cynthia-yuan/claude_submit.git
# 错误：https://github.com/Cynthia-yuan/claude_submit.git（SSH 方式）

# 5. 尝试克隆
git clone git@github.com:Cynthia-yuan/claude_submit.git

# 6. 如果 SSH 失败，尝试 HTTPS（备用）
git clone https://github.com/Cynthia-yuan/claude_submit.git
```

### 4. 权限被拒绝（Permission denied）

**原因和解决：**

```bash
# 检查 SSH 密钥对应的 GitHub 账户
ssh -T git@github.com
# 输出会显示：Hi 账户名! You've successfully authenticated

# 如果账户名错误，说明使用了错误的 SSH 密钥
# 解决方案：
# 1. 使用正确的账户重新生成密钥
ssh-keygen -t rsa -b 4096 -C "正确的邮箱" -f ~/.ssh/id_rsa -N ""

# 2. 添加到正确的 GitHub 账户
# 访问：https://github.com/settings/ssh/new

# 3. 确认仓库访问权限
# 访问：https://github.com/Cynthia-yuan/claude_submit
# 确认你的账户已被添加为协作者（对于私有仓库）
```

### 5. pip install 失败

**解决方案：**

```bash
# 1. 更新 pip
pip install --upgrade pip

# 2. 使用国内镜像源（如果在中国）
pip install -r fault-pattern-knowledge-base/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 或配置永久镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 清理缓存重试
pip cache purge
pip install -r fault-pattern-knowledge-base/requirements.txt

# 5. 如果使用虚拟环境，确保已激活
source fault-pattern-knowledge-base/venv/bin/activate
pip install -r requirements.txt
```

### 6. Python 版本不兼容

**解决方案：**

```bash
# 1. 检查当前 Python 版本
python3 --version

# 2. 检查项目要求的版本
cat fault-pattern-knowledge-base/requirements.txt | grep python

# 3. 使用 pyenv 管理多个 Python 版本（推荐）
brew install pyenv
pyenv install 3.11.0
pyenv local 3.11.0

# 4. 或使用 conda
conda create -n vscode_claude python=3.11
conda activate vscode_claude
```

### 7. 分支跟踪问题

**错误：** "fatal: no upstream branch"

**解决：**

```bash
# 1. 查看当前分支
git branch

# 2. 查看远程分支
git branch -r

# 3. 设置跟踪分支
git branch --set-upstream-to=origin/main main

# 4. 或在 pull 时指定远程
git pull origin main

# 5. 首次推送时设置上游
git push -u origin main
```

### 8. SSL 证书问题

**错误：** "SSL certificate verification failed"

**解决方案：**

```bash
# 方案 1：更新 CA 证书（macOS）
brew install ca-certificates
brew update-ca-certificates

# 方案 2：切换到 SSH（推荐，避免 SSL 问题）
git remote set-url origin git@github.com:Cynthia-yuan/claude_submit.git

# 方案 3：配置代理（如果使用）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 方案 4：临时禁用 SSL 验证（仅用于测试！）
git config --global http.sslVerify false
# 测试后务必恢复：
git config --global http.sslVerify true
```

### 9. 防火墙或代理问题

**诊断：**

```bash
# 1. 测试网络连接
ping -c 3 github.com

# 2. 测试 SSH 端口
telnet github.com 22
# 或
nc -zv github.com 22

# 3. 检查代理设置
env | grep -i proxy

# 4. 详细 SSH 连接测试
ssh -T -v git@github.com
```

**如果使用代理，配置 Git：**

```bash
# HTTP/HTTPS 代理
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# SSH 代理配置
cat >> ~/.ssh/config << EOF
Host github.com
    ProxyCommand nc -X 5 -x 127.0.0.1:7890 %h %p
EOF

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 10. 快速故障排除命令

**一键诊断脚本：**

```bash
echo "=== Git 配置 ===" && git config --global user.name && git config --global user.email && echo "" && \
echo "=== 远程仓库 ===" && git remote -v && echo "" && \
echo "=== SSH 密钥 ===" && ls -la ~/.ssh/*.pub && echo "" && \
echo "=== SSH 连接测试 ===" && ssh -T git@github.com 2>&1 | head -1 && echo "" && \
echo "=== 分支信息 ===" && git branch -vv && echo "" && \
echo "=== 网络测试 ===" && ping -c 1 github.com
```

将此脚本复制并在新机器上运行，可以快速定位问题！

## 触发关键词

用户可能使用以下方式触发此 skill：
- `/git-setup`
- "在新机器上设置项目"
- "setup dev environment"
- "clone and setup"
- "配置开发环境"
- "部署项目"