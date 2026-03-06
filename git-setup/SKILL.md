---
name: git-setup
description: 在新机器上快速设置开发环境。使用 HTTPS 方式克隆 git 仓库，通过 Personal Access Token 进行身份验证。包括配置 Git 环境、安装项目依赖和配置开发工具。适用于首次部署或在多台机器上同步开发环境。
---

# Git Setup Skill (HTTPS 方式)

## 功能说明

在新机器上自动完成开发环境配置，使用 HTTPS 方式访问 Git 仓库：
1. 检查系统环境（Git、Python、Node.js 等）
2. 生成 GitHub Personal Access Token
3. 克隆指定的 git 仓库（HTTPS 方式）
4. 配置 Git 凭据存储（避免重复输入密码）
5. 安装项目依赖
6. 配置开发环境

**优势：**
- ✅ 无需配置 SSH 密钥
- ✅ 更简单，更易调试
- ✅ 适合所有操作系统
- ✅ 企业防火墙友好

## 执行步骤

### 第一步：检查系统环境

1. **检查 Git 是否安装**
   ```bash
   git --version
   ```
   - 如果未安装，提示用户安装 Git
   - macOS: `brew install git`
   - Ubuntu/Debian: `sudo apt-get install git`
   - Windows: 下载安装包 https://git-scm.com/download/win

2. **检查 Python 是否安装**（项目需要）
   ```bash
   python3 --version
   ```
   - 如果未安装，提示用户安装 Python
   - macOS: `brew install python3`
   - Ubuntu/Debian: `sudo apt-get install python3 python3-pip`
   - Windows: 下载安装包 https://www.python.org/downloads/

3. **检查 pip 和 venv**
   ```bash
   pip3 --version
   python3 -m venv --help
   ```

### 第二步：生成 GitHub Personal Access Token

1. **访问 GitHub Token 设置页面**
   - 打开浏览器，访问：https://github.com/settings/tokens
   - 点击 "Generate new token" → "Generate new token (classic)"

2. **填写 Token 信息**
   - **Note**：填写机器名称，例如 `MacBook-Pro` 或 `Desktop-PC`
   - **Expiration**：选择过期时间（建议 90 天或更长）
   - **Scopes**：勾选以下权限：
     - ✅ `repo`（完整仓库控制权限）
     - ✅ `workflow`（如果需要 GitHub Actions）
   - 点击底部 "Generate token" 按钮

3. **保存 Token**
   - **重要：Token 只显示一次，必须立即复制保存！**
   - 建议保存到密码管理器或安全位置
   - Token 格式：`ghp_xxxxxxxxxxxxxxxxxxxx`

4. **验证 Token**
   - 确认 Token 以 `ghp_` 开头
   - 长度约为 40 个字符

### 第三步：克隆 Git 仓库（HTTPS 方式）

1. **确认仓库信息**
   - 询问用户仓库 URL（默认：`https://github.com/Cynthia-yuan/claude_submit.git`）
   - 询问目标目录（默认：`~/vscode_claude` 或当前目录）

2. **执行克隆操作**
   ```bash
   # 方式 A：直接使用 Token 克隆（临时方式）
   git clone https://<TOKEN>@github.com/Cynthia-yuan/claude_submit.git vscode_claude

   # 方式 B：使用标准 HTTPS 克隆（推荐）
   git clone https://github.com/Cynthia-yuan/claude_submit.git vscode_claude

   # 进入仓库目录
   cd vscode_claude
   ```

3. **验证克隆成功**
   ```bash
   git status
   git log --oneline -1
   git remote -v
   ```
   应该显示：
   ```
   origin  https://github.com/Cynthia-yuan/claude_submit.git (fetch)
   origin  https://github.com/Cynthia-yuan/claude_submit.git (push)
   ```

### 第四步：配置 Git 用户信息和凭据存储

1. **配置 Git 用户信息**
   ```bash
   # 询问用户 GitHub 用户名和邮箱
   git config --global user.name "Cynthia-yuan"
   git config --global user.email "cynthiayuanll@163.com"

   # 验证配置
   git config --global user.name
   git config --global user.email
   ```

2. **配置 Git 凭据存储**（重要：避免重复输入 Token）

   **macOS:**
   ```bash
   git config --global credential.helper osxkeychain
   ```

   **Linux:**
   ```bash
   # 方式 A：内存缓存（1小时）
   git config --global credential.helper cache
   git config --global credential.helper 'cache --timeout=3600'

   # 方式 B：永久存储（需要安装）
   sudo apt install git-credential-libsecret  # Ubuntu/Debian
   git config --global credential.helper libsecret
   ```

   **Windows:**
   ```bash
   git config --global credential.helper manager
   ```

3. **首次 Pull 并输入凭据**
   ```bash
   git pull origin main
   ```
   **会提示输入：**
   - **Username**：输入 GitHub 用户名（例如：`Cynthia-yuan`）
   - **Password**：粘贴 Personal Access Token（不是 GitHub 密码！）
     - Token 格式：`ghp_xxxxxxxxxxxxxxxxxxxx`
     - 注意：输入时不会显示任何字符，这是正常的

4. **验证凭据已保存**
   ```bash
   # 再次 pull，不应该再提示输入用户名密码
   git pull

   # 或查看凭据存储
   # macOS: 钥匙串访问中搜索 "github"
   # Linux: ~/.git-credentials
   # Windows: Windows 凭据管理器
   ```

### 第五步：验证 git pull 和 push 功能

1. **测试 git pull**
   ```bash
   # 方法 1：直接 pull（如果已设置跟踪分支）
   git pull

   # 方法 2：指定远程和分支
   git pull origin main

   # 方法 3：设置跟踪分支后 pull
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

2. **测试 git push**
   ```bash
   # 创建测试文件
   echo "Test from new machine via HTTPS" > test-https-setup.txt

   # 添加并提交
   git add test-https-setup.txt
   git commit -m "test: HTTPS setup on new machine"

   # 推送到远程
   git push origin main

   # 成功输出示例：
   # To https://github.com/Cynthia-yuan/claude_submit.git
   #    79e1e4c..xxxxxxx  main -> main
   ```

### 第六步：安装项目依赖

1. **安装 Python 依赖**
   ```bash
   # 进入项目目录
   cd fault-pattern-knowledge-base

   # 创建虚拟环境
   python3 -m venv venv

   # 激活虚拟环境
   source venv/bin/activate  # Linux/macOS
   # 或
   venv\Scripts\activate  # Windows

   # 安装依赖
   pip install --upgrade pip
   pip install -r requirements.txt

   # 验证安装
   pip list | grep -i flask
   ```

2. **检查其他依赖**
   - 查找项目中的 `package.json`（Node.js 项目）
   - 查找 `Gemfile`（Ruby 项目）
   - 查找 `go.mod`（Go 项目）
   - 根据需要安装对应依赖

### 第七步：完整验证

运行一键验证脚本：

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
echo "=== 测试 git pull ===" && \
git pull origin main && \
echo "" && \
echo "=== Python 环境验证 ===" && \
python3 --version && \
pip --version && \
echo "" && \
echo "✅ 所有配置验证通过！"
```

## 注意事项

- **Token 安全**：
  - ⚠️ Token 相当于密码，请妥善保管
  - ⚠️ 不要在代码中硬编码 Token
  - ⚠️ 不要将 Token 提交到 Git 仓库
  - ⚠️ 定期更新 Token（建议 90 天）

- **Token 泄露处理**：
  - 如果 Token 泄露，立即访问：https://github.com/settings/tokens
  - 撤销泄露的 Token（点击 "Delete"）
  - 生成新的 Token 并更新凭据

- **凭据存储**：
  - 配置凭据存储后，Token 会被安全保存
  - 不需要每次输入 Token
  - 如需更新 Token，删除存储的凭据重新输入

- **网络问题**：
  - 克隆仓库和安装依赖需要稳定的网络连接
  - 如果使用代理，需要配置 Git 代理
  - 企业环境可能需要配置防火墙

- **磁盘空间**：
  - 确保有足够的磁盘空间存储仓库和依赖

## 备用方案：SSH 方式

如果 HTTPS 方式遇到问题，可以使用 SSH 方式作为备用：

### 生成 SSH 密钥

```bash
# 1. 生成 RSA 密钥
ssh-keygen -t rsa -b 4096 -C "你的邮箱" -f ~/.ssh/id_rsa -N ""

# 2. 启动 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa

# 3. 复制公钥
cat ~/.ssh/id_rsa.pub | pbcopy  # macOS

# 4. 添加到 GitHub
# 访问：https://github.com/settings/ssh/new
# 粘贴公钥，点击 "Add SSH key"

# 5. 测试连接
ssh -T git@github.com

# 6. 切换远程仓库为 SSH
git remote set-url origin git@github.com:Cynthia-yuan/claude_submit.git

# 7. 验证
git remote -v
git pull
```

## 常见问题及解决方案

### 1. Token 验证失败

**错误：** "Authentication failed" 或 "Invalid credentials"

**原因：**
- Token 输入错误
- Token 已过期或被撤销
- 使用了 GitHub 密码而不是 Token

**解决方案：**
```bash
# 1. 生成新的 Token
# 访问：https://github.com/settings/tokens
# 撤销旧 Token，生成新 Token

# 2. 清除存储的凭据
# macOS
git credential-osxkeychain erase
host=github.com
protocol=https
# 按 Ctrl+D 结束输入

# Linux
rm -f ~/.git-credentials

# Windows
# 在凭据管理器中删除 GitHub 相关凭据

# 3. 重新 pull 并输入新 Token
git pull origin main
```

### 2. Git pull 失败："Could not read from remote repository"

**诊断和修复：**

```bash
# 诊断步骤 1：检查远程仓库 URL
git remote -v
# 应该显示：https://github.com/Cynthia-yuan/claude_submit.git

# 诊断步骤 2：测试网络连接
ping github.com

# 诊断步骤 3：查看详细错误信息
GIT_CURL_VERBOSE=1 git pull origin main

# 诊断步骤 4：检查凭据存储
git config --global credential.helper

# 解决方案 1：重新输入凭据
git pull origin main
# 输入正确的用户名和 Token

# 解决方案 2：清除凭据后重新输入
# (参考问题 1 的解决方案)

# 解决方案 3：使用临时 URL 测试
git remote set-url origin https://<TOKEN>@github.com/Cynthia-yuan/claude_submit.git
git pull origin main
# 如果成功，说明 Token 有效，问题在凭据存储
```

### 3. 每次都要输入用户名密码

**原因：** 凭据存储未配置或配置错误

**解决方案：**

```bash
# macOS
git config --global credential.helper osxkeychain

# Linux
# 安装凭据助手
sudo apt install git-credential-libsecret  # Ubuntu/Debian
git config --global credential.helper libsecret

# Windows
git config --global credential.helper manager

# 配置后重新 pull
git pull origin main
# 输入一次后会自动保存
```

### 4. Git clone 失败

**诊断清单：**

```bash
# 1. 检查网络连接
ping github.com

# 2. 检查 Git 安装
git --version

# 3. 尝试直接使用 Token 克隆
git clone https://<TOKEN>@github.com/Cynthia-yuan/claude_submit.git

# 4. 检查代理设置
env | grep -i proxy

# 5. 如果使用代理，配置 Git
git config --global http.proxy http://代理地址:端口
git config --global https.proxy http://代理地址:端口

# 6. 克隆完成后移除代理（如果需要）
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 5. SSL 证书问题

**错误：** "SSL certificate verification failed"

**解决方案：**

```bash
# 方案 1：更新 CA 证书
# macOS
brew install ca-certificates

# Ubuntu/Debian
sudo apt update && sudo apt install ca-certificates

# 方案 2：配置代理（如果使用）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 方案 3：临时禁用 SSL 验证（仅用于测试！）
git config --global http.sslVerify false
git clone https://github.com/Cynthia-yuan/claude_submit.git
# 测试后务必恢复：
git config --global http.sslVerify true
```

### 6. 权限被拒绝（Permission denied）

**错误：** "fatal: repository not found" 或 "Permission denied"

**原因：**
- 使用了错误的账户
- 账户没有仓库访问权限
- Token 权限不足

**解决方案：**

```bash
# 1. 确认使用的 GitHub 账户
# 浏览器访问：https://github.com/Cynthia-yuan/claude_submit
# 确认能正常访问

# 2. 检查 Token 权限
# 访问：https://github.com/settings/tokens
# 确认 Token 有 `repo` 权限

# 3. 如果是私有仓库，确认账户已被添加为协作者
# 仓库所有者操作：
# Settings → Collaborators → Add people

# 4. 重新生成具有正确权限的 Token
```

### 7. pip install 失败

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
```

### 8. Python 版本不兼容

**解决方案：**

```bash
# 1. 检查当前 Python 版本
python3 --version

# 2. 使用 pyenv 管理多个 Python 版本
brew install pyenv
pyenv install 3.11.0
pyenv local 3.11.0

# 3. 或使用 conda
conda create -n vscode_claude python=3.11
conda activate vscode_claude
```

### 9. 分支跟踪问题

**错误：** "fatal: no upstream branch"

**解决：**

```bash
# 1. 查看当前分支
git branch

# 2. 设置跟踪分支
git branch --set-upstream-to=origin/main main

# 3. 或在 pull 时指定远程
git pull origin main

# 4. 首次推送时设置上游
git push -u origin main
```

### 10. 快速故障排除命令

**一键诊断脚本：**

```bash
echo "=== Git 配置 ===" && \
git config --global user.name && \
git config --global user.email && \
echo "" && \
echo "=== 远程仓库 ===" && \
git remote -v && \
echo "" && \
echo "=== 凭据存储 ===" && \
git config --global credential.helper && \
echo "" && \
echo "=== 当前分支 ===" && \
git branch -vv && \
echo "" && \
echo "=== 网络测试 ===" && \
ping -c 1 github.com && \
echo "" && \
echo "=== 测试 pull ===" && \
git pull origin main
```

## Token 管理最佳实践

1. **定期更新 Token**
   - 建议每 90 天更新一次
   - 设置过期提醒

2. **为不同机器使用不同 Token**
   - 便于追踪和管理
   - 撤销时不影响其他机器

3. **Token 权限最小化**
   - 只授予必要的权限
   - 对于只读操作，可以使用只读 Token

4. **安全存储 Token**
   - 使用密码管理器
   - 不要在代码中硬编码
   - 不要在聊天工具中明文发送

5. **泄露应急处理**
   ```bash
   # 立即撤销泄露的 Token
   # 访问：https://github.com/settings/tokens
   # 点击 "Delete" 撤销 Token

   # 生成新 Token
   # 更新所有机器的凭据
   ```

## 触发关键词

用户可能使用以下方式触发此 skill：
- `/git-setup`
- "在新机器上设置项目"
- "使用 HTTPS 克隆仓库"
- "配置 Git HTTPS 访问"
- "setup dev environment"
- "clone and setup"
- "配置开发环境"