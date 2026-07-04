# Changelog

All notable changes to this project.

---

## [Unreleased] — 2026-07-04

### 🏗️ Architecture

- **`app.py` 拆分为 Blueprint 架构** — 从 1,426 行单体文件拆分为 `app_init.py`（初始化）+ `routes/{auth,certs,admin,api,pages}.py`（路由），共 7 个模块
- **创建 `templates/base.html`** — 统一基础模板，所有页面继承，包含响应式侧边栏、导航、flash messages、toast 通知
- **创建 `cache.py`** — 轻量级 LRU 内存缓存（线程安全、TTL 支持），用于 certs/users/config 三级缓存
- **创建 `exceptions.py`** — 统一异常体系：`MonitorException` 基类 + 7 种错误码（ERR_VALIDATION, ERR_NOT_FOUND, ERR_PERMISSION, ERR_DATA, ERR_SERVICE, ERR_IMPORT, ERR_EXPORT）

### 🔒 Security

- **密码策略增强** — 最小长度从 8 位提升到 12 位，新增 30+ 常见密码黑名单，返回 4 元组 `(valid, message, score, label)` 强度评分
- **会话安全加固** — `SESSION_COOKIE_SAMESITE` 从 `Lax` 改为 `Strict`，`SESSION_COOKIE_SECURE` 根据 DEBUG 动态设置
- **X-Request-ID 中间件** — 每个请求生成 UUID，记录到响应头和 audit.log
- **Audit Logger** — 所有请求/响应记录到 `audit.log`（RotatingFileHandler）

### 💾 Data Layer

- **存储统一为 SQLite** — 删除 JSON 模式兼容代码、FileLock、原子写入、缓存字典；所有数据操作走 SQLite
- **init_data.py 简化** — 只保留 SQLite 初始化逻辑
- **migrate_json_to_sqlite 保留** — 从 JSON 迁移到 SQLite 的工具函数保留

### 🧪 Testing

- **测试从 256 行扩展到 4,765 行** — 新增 14 个测试文件
- **测试覆盖率从 7% 提升到 80%+** — 覆盖 daemon.py、data.py、routes/*、cache.py、exceptions.py
- **新增端到端集成测试** — 完整登录流程、CRUD 流程、批量操作、导入导出、备份恢复
- **新增部署测试** — Dockerfile、docker-compose.yml、supervisord.conf 验证

### 📦 Docker & Deployment

- **创建多阶段 Dockerfile** — builder 阶段安装依赖，runtime 阶段仅复制必要文件，非 root 用户（appuser），HEALTHCHECK 指令
- **创建 `.dockerignore`** — 排除 .git、data、__pycache__、测试文件、日志
- **supervisord.conf 修改** — user 从 root 改为 appuser

### 🌐 Frontend

- **Tailwind CSS 改为 CDN** — 移除 407KB 本地文件，使用 `cdn.jsdelivr.net`
- **Lucide Icons 改为 CDN** — 移除 410KB 本地文件，使用 `unpkg.com`
- **dark.css 优化** — 移除所有 `!important`，改用 `@layer base`
- **移动端适配** — 汉堡菜单、抽屉式侧边栏、overlay 遮罩、触摸目标 ≥ 44px、表单 16px 防 iOS 缩放、表格横向滚动、卡片视图
- **Inline JS 提取** — 模板中的 inline `<script>` 提取到 `static/app.js`（公共逻辑）和各页面专属 JS

### 📊 Monitoring & Observability

- **Prometheus metrics** — `/metrics` 端点暴露计数器、直方图、仪表盘
- **`/health` 端点** — 健康检查，验证 SQLite 连接
- **日志自动清理** — 定时清理（每天凌晨 3 点）+ 手动触发 API（`/api/admin/cleanup-logs`），超过 50MB 压缩归档，保留 7 天
- **缓存统计 API** — `/api/cache-stats` 管理员端点，返回命中率、条目数

### 📥 Data Management

- **导入预览** — `POST /api/import-preview` 验证数据格式并返回预览，用户确认后导入
- **CSV 导入** — 自动检测分隔符（逗号/制表符/分号/管道）和编码（UTF-8/GBK/GB2312），智能字段映射
- **增量导入** — 支持 `mode=incremental`，基于 cert_id 或 (domain, ip) 去重
- **数据质量报告** — `GET /api/data-quality` 扫描重复记录、缺失字段、过期未处理、长期未更新
- **可配置导出** — CSV 导出支持查询参数选择列，UTF-8 BOM 编码

### ⚙️ Configuration

- **环境变量覆盖** — `load_config()` 支持 `MONITOR_*` 前缀的环境变量覆盖（如 `MONITOR_WEBHOOK_URL`）
- **`.env` 文件支持** — 通过 `python-dotenv` 加载 `.env` 文件
- **配置热更新** — `reload_config()` 函数清除缓存并重新加载，`POST /api/admin/reload-config` API
- **`requirements.txt` 更新** — 新增 `python-dotenv==1.0.0`、`cachetools>=6.0`

### 📝 Documentation

- **`.docs/ARCHITECTURE.md`** — 项目架构文档（技术栈、目录结构、模块描述、安全设计、部署架构）
- **`.docs/archive/`** — 18 个审查文档归档（REVIEW_V2-V7, UX_REVIEW, OPTIMIZATION_PLAN, BUG_FIX_SUMMARY 等）
- **根目录清理** — 只保留 README.md、CHANGELOG.md、Dockerfile、docker-compose.yml 等核心文件
- **mypy.ini** — 类型检查配置，strict 模式

### 📈 Statistics

| 维度 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| Python 源码 | ~2,500 行 | ~5,071 行 | +103% |
| 测试代码 | 256 行 | 4,765 行 | +1,761% |
| 测试覆盖率 | ~7% | 80%+ | +73% |
| app.py | 1,426 行 | 17 行 | Blueprint 拆分 |
| 审查文档 | 16 个（根目录） | 18 个（.docs/archive/） | 根目录清爽 |
| 模板 | 12 个独立 HTML | 1 个 base.html + 11 个继承模板 | 统一布局 |

---

## [Previous Versions]

See `.docs/archive/` for historical review documents.
