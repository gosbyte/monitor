# Changelog

All notable changes to this project.

---

## [Unreleased] — 2026-06-26

### Added

- **`dingtalk.py`** — 钉钉/企业微信消息推送模块
  - `send_dingtalk_card()` — 钉钉自定义机器人 Markdown 卡片，支持加签和 @人
  - `send_wecom()` — 企业微信群机器人 Markdown 消息
  - `build_remind_card()` — 构建到期提醒卡片内容，自动收集负责人 @UserID
- **`init_data.py`** — 首次运行初始化脚本
  - 创建默认证书数据、配置文件、用户数据、操作日志
  - 生成 Flask secret_key
  - 被 Dockerfile RUN 调用
- **`deploy.sh`** — 一键部署脚本
  - 检查 Docker / docker compose 是否安装
  - 端口占用检测与确认
  - 构建镜像、启动服务、等待健康检查
- **`.gitignore`** — 排除 data/*.json、*.lock、*.tmp、.secret_key、.fernet_key 等
- **`/api/certs`** — 分页获取到期列表 API（支持 page/per_page 参数，最大 200 条/页）

### Changed

#### 数据安全与并发

- **文件锁全面覆盖** — 所有 JSON 读写操作（certs、config、users、logs、remind_state）统一使用 `FileLock`（fcntl + 超时回退）
- **`data.py` 日志操作加锁** — `load_logs()` / `save_logs()` 原来无锁，现加 `_LOGS_LOCK`
- **`daemon.py` 数据读取加锁** — `load_data()` / `load_config()` / `load_state()` / 用户加载全部加 `FileLock`
- **`_migrate_password()` 修复死锁** — 原调用 `save_users()`（会重新获取锁），改为直接 `atomic_write_json()`
- **`save_users()` 缓存失效修复** — 原用 `mtime=0` 有竞态风险，改用 generation counter
- **`FileLock.__enter__()` 异常安全** — 增加 `try/except` 确保 fd 在异常时正确关闭
- **`verify_user()` 守护进程安全** — 增加 `check_password_hash is None` 检查，daemon 导入 data.py 时不崩溃

#### 数据一致性

- **`daemon.py` 邮件发送不污染共享对象** — 构建 `to_remind_copy` 深拷贝，不再直接修改原始 cert dict
- **`auth.py inject_globals()` 不污染 cert 对象** — 内联调用 `calc_days_left()`，不再 `for c in certs: c["days_left"] = ...`
- **`data.py calc_days_left()` 裸 except 修复** — `except:` → `except Exception`

#### 性能优化

- **`index()` 后端分页** — 默认每页 50 条，大图表演算限制在前 200 条
- **`edit_cert()` 消除重复查询** — 移除冗余的第二次 `load_users()` 调用
- **`add_cert()` 移除调试日志** — 删除 `logger.info("ADD route called...")` 生产环境日志

#### 安全防护

- **`api_test_email()` 解密 SMTP 密码** — 增加 `decrypt_password()` 调用
- **`api_test_email()` / `api_test_push()` / `api_test_wecom()` 速率限制** — 各 IP 每 60 秒最多 5 次
- **`app.py` 顶层 import smtplib** — 移除函数内 `import smtplib`

#### Docker 与部署

- **Dockerfile pip 源修复** — 清华源停用，改回阿里云 `https://mirrors.aliyun.com/pypi/simple/`
- **移除 Debian trixie 源** — 使用官方 apt 源
- **添加中文字体** — `fonts-wqy-microhei`（验证码中文渲染）
- **`deploy.sh` 错误处理** — 构建/启动失败时 `exit 1` 并提示
- **`docker-compose.yml` 端口可配** — 支持 `CERT_MONITOR_PORT` 环境变量

### Fixed

- **`api_batch_delete()` 幂等性** — 返回实际删除数量 `deleted_count`，清理状态时加文件锁
- **`deploy.sh` 端口检测兼容性** — 同时支持 `ss` 和 `netstat`
- **`requirements.txt` 版本锁定** — 保持固定版本，避免意外升级

---

## [Previous] — Initial Release

- 通用到期提醒系统 MVP
- Flask Web 管理界面
- 钉钉机器人到期提醒
- 后台常驻守护进程（精确到分钟）
- 用户管理（登录、密码哈希、登录锁定）
- 证书 CRUD + 批量操作
- 操作日志
