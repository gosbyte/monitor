# 项目架构文档

> 最后更新: 2026-07-04  
> 基于多轮代码审查（REVIEW_V2-V7）后的最终架构

---

## 1. 技术栈

| 层级 | 技术 |
|------|------|
| **框架** | Flask (Python 3.13) |
| **数据存储** | SQLite (`monitor.db`) + JSON 文件双模式 (`USE_SQLITE` 开关) |
| **前端** | Tailwind CSS v4 (Play CDN), Lucide Icons, 原生 JavaScript |
| **进程管理** | Supervisor (管理 web + daemon 两个进程) |
| **部署** | Docker + docker-compose |
| **通知** | 钉钉自定义机器人 / 企业微信群机器人 / Webhook |

---

## 2. 目录结构

```
monitor-main-tmp/
├── app_init.py          # Flask 应用工厂 & 全局配置 (CSP/CSRF/安全头)
├── app.py               # 主路由文件 (登录/首页/API)
├── auth.py              # 认证模块 (登录/验证码/CSRF/全局注入)
├── daemon.py            # 后台守护进程 (精确到分钟的到期监控)
├── data.py              # 数据层抽象 (JSON/SQLite 双模式路由)
├── db.py                # SQLite ORM 层 (表结构/CRUD/迁移)
├── dingtalk.py          # 钉钉/企业微信消息推送
├── webhook.py           # 通用 Webhook 回调
├── init_data.py         # 首次运行初始化脚本
├── requirements.txt     # Python 依赖
│
├── routes/              # 蓝图模块化路由
│   ├── api.py           # REST API 路由
│   ├── pages.py         # 页面路由 (编辑/批量/日志等)
│   ├── admin.py         # 管理员路由 (用户管理/数据管理)
│   ├── certs.py         # 证书/到期项路由
│   ├── auth.py          # 认证相关路由
│   └── __init__.py      # 蓝图注册
│
├── templates/           # Jinja2 模板 (12 个 HTML 文件)
│   ├── index.html       # 主页 (最大, 1775 行)
│   ├── login.html       # 登录页
│   ├── edit.html        # 编辑记录
│   ├── add_batch.html   # 批量添加
│   ├── config.html      # 推送配置
│   ├── users.html       # 用户管理
│   ├── logs.html        # 操作日志
│   ├── data_manage.html # 数据管理
│   ├── restore.html     # 数据恢复
│   ├── change_password.html
│   ├── push_history.html
│   └── error.html
│
├── static/              # 静态资源
│   ├── dark.css         # 暗色模式 CSS
│   └── dark.js          # 暗色模式切换 JS
│
├── data/                # 运行时数据目录 (挂载卷)
│   ├── monitor.db       # SQLite 数据库
│   ├── certs.json       # 到期项数据 (JSON 模式)
│   ├── config.json      # 系统配置
│   ├── users.json       # 用户数据
│   └── logs.json        # 操作日志
│
├── tests/               # pytest 测试套件
├── Dockerfile           # 多阶段构建
├── docker-compose.yml   # 编排配置
├── supervisord.conf     # 进程管理配置
├── deploy.sh            # 一键部署脚本
├── .env.example         # 环境变量模板
└── .docs/               # 文档目录
    ├── ARCHITECTURE.md  # 本文档
    ├── CHANGELOG.md     # 变更日志
    └── archive/         # 历史审查文档归档
```

---

## 3. 架构流程图

```
                    ┌─────────────┐
                    │  Browser     │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │  Supervisor  │
                    │  ┌────────┐ │
                    │  │  Web   │ │  ← Flask app (app_init.py)
                    │  │  Port  │ │     routes/ 蓝图模块化
                    │  └────────┘ │
                    │  ┌────────┐ │
                    │  │ Daemon │ │  ← 后台监控 (daemon.py)
                    │  │ Min-1  │ │     精确到期提醒
                    │  └────────┘ │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ SQLite   │ │ JSON     │ │ External │
        │ monitor  │ │ files    │ │ APIs     │
        │  .db     │ │ (.json)  │ │ DingTalk │
        └──────────┘ └──────────┘ └──────────┘
```

---

## 4. 核心模块说明

### 4.1 `app_init.py` — 应用工厂
- 创建 Flask 应用实例
- 注册所有蓝图 (routes/)
- 配置 CSP/CSRF/安全头
- 注册 Prometheus metrics 和健康检查端点
- 处理信号 (SIGTERM/SIGINT)

### 4.2 `data.py` — 数据层抽象
- `USE_SQLITE` 开关路由到 SQLite 或 JSON 模式
- 所有 CRUD 操作的统一入口
- 文件锁 (JSON 模式) / 数据库事务 (SQLite 模式)
- 密码迁移 (`_migrate_password_sqlite`)
- 加密/解密工具 (`encrypt_field`/`decrypt_field`)

### 4.3 `db.py` — SQLite ORM
- 表结构定义 (certs, users, logs, config)
- 自动迁移 (JSON → SQLite)
- 原子写入 (临时文件 + os.replace)
- WAL 模式提高并发性能

### 4.4 `daemon.py` — 守护进程
- 每分钟检查一次到期项
- 支持到期前 N 天、当天、精确到分钟、已过期多种提醒
- 深拷贝避免修改共享对象
- 优雅关停 (SIGTERM 保存状态)

### 4.5 `auth.py` — 认证与安全
- 登录/登出/密码修改
- 验证码生成 (PIL)
- CSRF token 管理与轮换
- 登录锁定 (IP + 账户级)
- 全局变量注入 (badge_count, csp_nonce)

---

## 5. 安全设计

| 措施 | 实现 |
|------|------|
| **CSP** | `before_request` 注入 nonce, `context_processor` 传递到模板 |
| **CSRF** | 表单 token + Header token 双重保护, 状态变更方法轮换 token |
| **密码** | bcrypt 哈希存储, 默认密码强制修改 |
| **加密** | Fernet 加密 SMTP 密码 |
| **并发** | 文件锁 (JSON) / 数据库事务 (SQLite) |
| **登录保护** | 验证码 + IP 限流 + 账户锁定 (5 次失败) |
| **API 限流** | 测试端点 IP 级限流 (60s/5次) |

---

## 6. 前端架构

- **Tailwind CSS v4**: 通过 CDN (`cdn.jsdelivr.net`) 加载, 不再本地存储
- **Lucide Icons**: 通过 CDN (`unpkg.com`) 加载, 不再本地存储
- **暗色模式**: `dark.css` + `dark.js` 独立模块, localStorage 持久化
- **12 个页面模板**: 无 Jinja2 继承, 均为独立 HTML 文件
- **CSP 兼容**: 所有内联脚本/样式均带 `nonce="{{ csp_nonce }}"`

---

## 7. 部署架构

```
Dockerfile (多阶段构建)
  ├─ Stage 1 (builder): Python 3.13-slim, 安装依赖
  └─ Stage 2 (runtime): 最小镜像, 非 root 用户
       │
docker-compose.yml
  ├─ 端口映射: ${CERT_MONITOR_PORT:-5188}:5188
  ├─ 数据卷: ./data:/app/data
  ├─ 环境变量: TZ, PORT, USE_SQLITE, DATA_DIR
  └─ 健康检查: /health 端点
```

---

## 8. 审查历史

所有代码审查记录已归档至 `.docs/archive/`:

| 文件 | 内容 |
|------|------|
| `REVIEW_BLACK.md` | Phase 1 基础审查 (bug 修复, 术语统一) |
| `REVIEW_PHASE2.md` | Phase 2 (db.py 集成, webhook 集成) |
| `REVIEW_PHASE3.md` | Phase 3 (csrf_token 修复, index 变量修复) |
| `REVIEW_SUMMARY.md` | 审查总览, 跨阶段进度跟踪 |
| `REVIEW_V2-V7.md` | 迭代审查 (安全性, 并发, 数据一致性) |
| `REVIEW_V7.md` | 最终审查 + 部署验证 + 修复记录 |
| `REVIEW_V*.md` | 各版本审查细节 |
| `UX_REVIEW*.md` | 用户体验审查 |
| `FUNCTIONAL_REVIEW.md` | 功能审查 |
| `OPTIMIZATION_PLAN.md` | 优化方案与实施计划 |
| `OPTIMIZATION_REPORT.md` | 优化报告 |
| `BUG_FIX_SUMMARY.md` | Bug 修复汇总 |
| `FIX_SUMMARY.md` | 具体修复总结 |
| `DEPLOY_REPORT.md` | 部署报告 |

---

*文档维护: 小白 (架构审查)*
