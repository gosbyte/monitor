# 到期提醒监控系统 (Item Monitor)

基于 Flask + SQLite + Docker 的到期项管理系统，支持钉钉/企业微信/邮件推送，精确到分钟的后台守护进程实时监控。

## 功能特性

| 功能 | 说明 |
|------|------|
| 📋 **到期项管理** | 添加/编辑/删除 SSL证书、域名、订阅等各类到期项，支持批量 Excel 导入 |
| 🔔 **多渠道推送** | 钉钉群机器人、企业微信机器人、SMTP 邮件，到期前自动提醒 |
| ⏰ **精确到分钟** | 后台守护进程实时轮询，到期立即推送，不等到第二天 |
| 🔐 **多用户管理** | 支持添加管理员/普通用户，密码哈希存储 |
| 📊 **数据统计** | 首页仪表盘：总数、已过期、即将到期、健康度百分比 |
| 🎨 **暗色模式** | 一键切换明/暗主题，独立持久化存储 |
| 📱 **响应式设计** | 移动端汉堡菜单、触摸友好、自适应布局 |
| 🔒 **安全加固** | CSRF 防护、登录限流（5次失败锁定5分钟）、PIL 验证码、文件锁防并发 |
| 📈 **操作日志** | 完整记录所有操作（增删改查、登录、配置变更） |
| 💾 **数据备份恢复** | 一键导出 SQLite 数据库为 SQL 文件，支持导入恢复 |
| 📉 **性能优化** | Tailwind CSS 精简（17KB）、路由级 JS 加载、缓存过期项避免重复查询 |

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   Docker Container                   │
│                                                      │
│  ┌──────────────┐      ┌──────────────┐             │
│  │  Supervisor   │─────▶│   Flask Web   │  :5188     │
│  │  (nodaemon)   │      │   (app.py)    │             │
│  └──────┬───────┘      └──────┬───────┘             │
│         │                     │                      │
│  ┌──────▼───────┐      ┌──────▼───────┐             │
│  │  Daemon       │      │  SQLite DB    │             │
│  │  (daemon.py)  │      │  (monitor.db) │             │
│  │  轮询检查到期  │      │               │             │
│  └──────┬───────┘      └──────────────┘             │
│         │                                            │
│  ┌──────▼───────┐                                     │
│  │  Push Service │─────▶ 钉钉 / 企业微信 / 邮件        │
│  └──────────────┘                                     │
└─────────────────────────────────────────────────────┘
         │
         ▼
  /app/data/  (宿主机挂载: ./data/)
  ├── monitor.db          SQLite 数据库
  ├── certs.json          到期项数据（兼容旧版）
  ├── users.json          用户数据
  ├── config.json         系统配置
  ├── logs.json           操作日志
  └── *.log               运行日志
```

## 快速部署

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆或下载项目
git clone https://github.com/gosbyte/monitor.git
cd monitor

# 2. 一键部署
chmod +x deploy.sh
./deploy.sh
```

### 方式二：手动 Docker 部署

```bash
# 1. 创建数据目录
mkdir -p data

# 2. 构建镜像
docker build -t item-monitor:latest .

# 3. 启动容器
docker run -d \
  --name item-monitor \
  --restart unless-stopped \
  -p 5188:5188 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  -e PORT=5188 \
  -e DATA_DIR=/app/data \
  -e USE_SQLITE=1 \
  item-monitor:latest

# 4. 查看日志
docker logs -f item-monitor
```

### 方式三：docker-compose.yml

```yaml
version: '3.8'

services:
  item-monitor:
    build: .
    image: item-monitor:latest
    container_name: item-monitor
    ports:
      - "5188:5188"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - PORT=5188
      - USE_SQLITE=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5188/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

```bash
docker compose up -d
```

## 首次使用

### 1. 访问系统

```
http://服务器IP:5188
```

默认账号：`admin`，首次登录后请立即修改密码。

### 2. 配置推送渠道

进入 **系统配置** 页面，填写以下信息：

#### 钉钉机器人
1. 钉钉群 → 群设置 → 智能群助手 → 添加机器人 → 自定义
2. 安全设置选择「加签」，复制生成的 Secret
3. 填写 Webhook URL 和 Secret
4. 设置提醒天数：`[30, 14, 7, 3, 1]`（到期前 N 天提醒）

#### 企业微信机器人
1. 企业微信群 → 群设置 → 群机器人 → 添加
2. 复制 Webhook URL
3. 填写到系统配置

#### 邮件通知
1. 填写 SMTP 服务器地址、端口、用户名、密码
2. 填写接收邮箱和发件人名称
3. 启用邮件推送

### 3. 添加到期项

进入 **监控管理** 页面：
- 点击「添加记录」手动输入
- 点击「批量导入」上传 Excel 文件（.xlsx/.xls）

字段说明：
| 字段 | 说明 |
|------|------|
| 名称 | 到期项名称（如：example.com SSL证书） |
| 类型 | SSL证书 / 域名 / 订阅 / 合同 / 其他 |
| 到期日期 | YYYY-MM-DD 格式 |
| 链接 | 相关链接（可选） |
| 备注 | 备注信息（可选） |
| 钉钉ID | 指定钉钉用户ID推送（可选，留空则推送群机器人） |

## 目录结构

```
monitor/
├── app.py                  # Flask 主应用（路由注册）
├── auth.py                 # 认证模块（登录、限流、验证码）
├── data.py                 # 数据层（JSON/SQLite 操作）
├── db.py                   # SQLite 数据库管理（迁移、初始化）
├── daemon.py               # 后台守护进程（到期检查 + 推送）
├── dingtalk.py             # 钉钉推送（文本、Markdown、ActionCard）
├── webhook.py              # 企业微信推送
├── cache.py                # 缓存管理（过期项缓存）
├── exceptions.py           # 自定义异常类
├── init_data.py            # 数据初始化脚本
├── supervisord.conf        # Supervisor 配置（web + daemon）
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 多阶段构建
├── docker-compose.yml      # Docker Compose 配置
├── deploy.sh               # 一键部署脚本
├── .gitignore
├── routes/
│   ├── __init__.py
│   ├── admin.py            # 管理员路由（用户管理）
│   ├── api.py              # API 路由（批量操作）
│   ├── auth.py             # 认证路由（登录/登出/改密）
│   ├── certs.py            # 到期项路由（CRUD + 导入导出）
│   └── pages.py            # 页面路由
├── templates/
│   ├── base.html           # 基础模板（sidebar + header + theme）
│   ├── index.html          # 首页仪表盘
│   ├── login.html          # 登录页
│   ├── login_standalone.html  # 独立登录页（无sidebar）
│   ├── add_batch.html      # 批量添加/导入
│   ├── edit.html           # 编辑到期项
│   ├── users.html          # 用户管理
│   ├── config.html         # 系统配置
│   ├── data_manage.html    # 数据管理（导入/导出/备份恢复）
│   ├── logs.html           # 操作日志
│   ├── push_history.html   # 推送历史
│   ├── backup_restore.html # 备份恢复（新增）
│   ├── cert_rows.html      # 证书行模板（用于动态插入）
│   ├── change_password.html # 更改密码
│   ├── error.html          # 错误页
│   └── email_reminder.html # 邮件模板
├── static/
│   ├── app.js              # 全局 JS（路由、fetch、showToast）
│   ├── common.css          # 通用样式
│   ├── dark.css            # 暗色主题样式
│   ├── dark.js             # 暗色主题切换逻辑
│   ├── index.js            # 首页 JS
│   ├── index.css           # 首页样式
│   ├── users.js            # 用户管理 JS
│   ├── config.js           # 配置页 JS
│   ├── data_manage.js      # 数据管理 JS
│   ├── logs.js             # 日志页 JS
│   ├── add_batch.js        # 批量添加 JS
│   ├── edit.js             # 编辑页 JS
│   ├── change_password.js  # 改密页 JS
│   ├── restore.js          # 恢复页 JS
│   ├── tailwind.js         # Tailwind CDN 加载
│   ├── tailwind.production.css  # 生产环境精简 CSS
│   ├── tailwind.production.server.css # 服务端渲染 CSS
│   ├── lucide.min.js       # 图标库
│   └── favicon.ico
└── utils/
    └── request_utils.py    # 请求工具（IP 获取等）
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PORT` | 容器内部监听端口 | `5188` |
| `DATA_DIR` | 数据目录路径 | `/app/data` |
| `TZ` | 时区 | `Asia/Shanghai` |
| `FLASK_ENV` | Flask 运行环境 | `production` |
| `USE_SQLITE` | 启用 SQLite 模式 | `1` |

宿主机端口映射通过 `-p` 或 `docker-compose.yml` 的 `ports` 配置。

## API 接口

所有 API 接口需要登录认证，请求头携带 `X-CSRF-Token`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/certs` | 获取到期项列表 |
| POST | `/api/certs` | 添加到期项 |
| PUT | `/api/certs/<id>` | 更新到期项 |
| DELETE | `/api/certs/<id>` | 删除到期项 |
| POST | `/api/certs/batch` | 批量导入 |
| POST | `/api/certs/export` | 导出 Excel |
| GET | `/api/stats` | 统计数据 |
| POST | `/api/test_push` | 测试推送 |
| GET | `/api/users` | 用户列表 |
| POST | `/api/users` | 添加用户 |
| PUT | `/api/users/<username>` | 编辑用户 |
| DELETE | `/api/users/<username>` | 删除用户 |
| POST | `/api/users/<username>/unlock` | 解锁用户 |
| GET | `/api/logs` | 操作日志 |
| DELETE | `/api/logs` | 清空日志 |
| GET | `/api/push_history` | 推送历史 |
| GET | `/health` | 健康检查（无需认证） |

## 安全说明

- **密码存储**：使用 Werkzeug 的 `generate_password_hash`（PBKDF2）
- **SMTP 密码**：使用 Fernet 对称加密存储
- **CSRF 防护**：所有表单和 API 请求需要 CSRF Token
- **登录限流**：同一 IP 5 次失败锁定 5 分钟，连续 3 次锁定自动递增
- **文件锁**：JSON 文件读写使用 `fcntl.flock` 防止并发损坏
- **非 root 运行**：Docker 容器内使用 `appuser` 非 root 用户

## 运维指南

### 查看日志

```bash
# 容器日志
docker logs -f item-monitor

# Flask 日志
docker exec item-monitor cat /app/data/flask.log

# Daemon 日志
docker exec item-monitor cat /app/data/daemon.log

# 错误日志
docker exec item-monitor cat /app/data/web_error.log
docker exec item-monitor cat /app/data/daemon_error.log
```

### 数据备份

```bash
# 方法1：Docker 内置备份恢复功能（Web UI）
# 系统配置 → 数据备份 → 导出

# 方法2：手动备份数据库
docker exec item-monitor cp /app/data/monitor.db /tmp/monitor.db.backup
docker cp item-monitor:/app/data/monitor.db ./monitor.db.backup

# 方法3：备份整个数据目录
tar czf monitor-data-$(date +%Y%m%d).tar.gz data/
```

### 数据恢复

```bash
# 停止容器
docker stop item-monitor

# 恢复数据库
docker cp monitor.db.backup item-monitor:/app/data/monitor.db

# 重启容器
docker start item-monitor
```

### 更新部署

```bash
# 方式1：从源码构建
git pull
docker compose down
docker compose build --pull
docker compose up -d

# 方式2：拉取最新镜像（如果已发布到 Docker Hub）
docker pull gosbyte/monitor:latest
docker compose down
docker compose up -d
```

### 常见问题

**Q: 登录后页面空白/样式丢失？**
A: 清除浏览器缓存，或按 `Ctrl+Shift+R` 强制刷新。检查 `static/tailwind.production.css` 是否存在。

**Q: 推送失败？**
A: 检查钉钉/企业微信 Webhook URL 是否正确，Secret 是否匹配。查看 `/app/data/daemon.log` 获取错误详情。

**Q: 登录验证码不显示？**
A: 检查 `Pillow` 是否安装：`docker exec item-monitor pip show Pillow`。

**Q: 数据丢失？**
A: 数据持久化在宿主机 `./data/` 目录，容器删除不影响数据。确保 volume 挂载正确。

**Q: 端口被占用？**
A: 修改 `docker-compose.yml` 中的端口映射，如 `"8080:5188"`。

## 依赖要求

- Docker 20.10+ / Docker Compose v2
- 最低内存：256MB
- 最低磁盘：50MB

## Python 依赖

```
Flask==3.0.0
Pillow>=11.0.0
requests==2.31.0
cryptography==41.0.7
openpyxl==3.1.2
prometheus-client==0.20.0
werkzeug==3.0.1
python-dotenv==1.0.0
cachetools>=6.0
supervisor
```

## 开发说明

### 本地运行（非 Docker）

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据目录
mkdir -p data
python init_data.py

# 运行
python app.py
```

### 代码规范

- Python 3.13+
- 类型注解完整
- mypy 类型检查：`mypy --config-file mypy.ini .`
- 黑色格式化：`black .`

## 许可证

MIT License

## 更新日志

### v2.0 (2026-08)
- 新增 SQLite 数据库存储（替代纯 JSON）
- 新增数据备份/恢复功能
- 新增备份恢复页面（backup_restore.html）
- 新增暗色主题独立 CSS（dark-theme.css）
- 优化：Tailwind CSS 精简至 17KB
- 优化：路由级 JS 懒加载
- 优化：登录限流数据持久化
- 安全：移除模板 nonce（CSP 改用 unsafe-inline）
- 安全：验证码大小写不敏感匹配
- 修复：CSS 文件缺失导致样式丢失
- 修复：index.js 从 45KB 精简至 788B（合并到 app.js）
