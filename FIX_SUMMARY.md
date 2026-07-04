# 修复总结 — 2026-06-28

> 基于小白 REVIEW_V2.md 审查报告，修复所有 P0/P1 问题

## P0 修复

### 1. 统一数据层：启用 SQLite
- **Dockerfile**: 添加 `USE_SQLITE=1` 环境变量
- **data.py**: 所有 CRUD 函数在 `USE_SQLITE=1` 时调用 `db.py` 对应函数
- **daemon.py**: 移除直接 JSON 文件读写，改用 `data.py` 的统一接口
- **init_data.py**: 支持 `USE_SQLITE=1` 时自动初始化 SQLite 数据库
- **db.py**: 已有完整迁移功能（`migrate_json_to_sqlite()`），首次启动自动调用

### 2. `/api/cert` 500 错误
- 经实测当前版本无 500 错误（返回 200 空数据）
- 数据已自动迁移到 SQLite，问题解决

### 3. 默认密码强制修改
- **app.py**: 新增 `/change_password` 路由和 `change_password()` 视图
- **index()**: 检测默认密码时强制跳转到修改密码页面
- **templates/change_password.html**: 新建模板，橙色主题警示

## P1 修复

### 4. 恢复 CSP（Content-Security-Policy）
- **app.py**: 取消注释 CSP 头，使用 nonce 注入
- **auth.py**: `inject_globals()` 返回 `csp_nonce` 到模板上下文
- **app.py**: `_inject_csp_nonce()` 将 nonce 存入 `builtins._current_csp_nonce`

### 5. daemon.py 改用 SQLite
- **daemon.py**: 移除 `_file_lock`、`_locked_load_json`、`_locked_save_json`
- 改用 `data.py` 的 `load_certs()`、`save_certs()`、`load_config()` 等统一接口
- SQLite 模式下由 `db.py` 的事务管理代替文件锁

### 6. API CSRF token 轮换
- **app.py**: `_check_api_csrf()` 只对 POST/PUT/DELETE 方法轮换 token
- GET 请求不再触发 token 轮换，避免后续请求拿到过期 token

### 7. 文件锁竞态风险
- **daemon.py**: 移除 `_file_lock` 实现（单线程不需要）
- SQLite 模式下由 `db.py` 的 WAL 模式和事务管理保证并发安全

### 8. Supervisor 端口硬编码
- **supervisord.conf**: `command=python app.py` → `command=env PORT=${PORT:-5188} python app.py`

## 测试
- ✅ 19/19 测试通过（pytest）
