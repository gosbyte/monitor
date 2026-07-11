# Item-Monitor 功能改进建议

> 审查时间：2026-06-29 | 审查者：小白 | 范围：完整功能代码

---

## P0 — 严重问题（影响核心功能）

### P0-1: 前端批量删除 API 路由不存在

**位置**: `templates/index.html` 第 959 行 vs `app.py`

**问题**: 前端 `batchDelete()` 函数调用 `fetch('/api/batch_delete', ...)`，但后端**没有** `/api/batch_delete` 路由。只有 `/api/batch_edit`（死代码，第 581-617 行，return 之后的代码永远不执行）和 `/api/batch_handle`、`/api/batch_remind`。

**影响**: 管理员在前端点击"批量删除"按钮会收到 404 错误，批量删除功能完全不可用。

**修复方案**: 新增 `/api/batch_delete` 路由，参考 `api_batch_handle` 的实现模式：
```python
@app.route("/api/batch_delete", methods=["POST"])
@login_required
@admin_required
def api_batch_delete():
    if not _check_api_csrf():
        return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"ok": False, "message": "未选择记录"}), 400
    certs = load_certs()
    deleted_ids = []
    for c in certs:
        if c["id"] in ids:
            deleted_ids.append(c["id"])
    certs = [c for c in certs if c["id"] not in ids]
    save_certs(certs)
    # 清理 daemon remind_state 中已删除记录的状态
    state_file = os.path.join(DATA_DIR, "remind_state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict):
                cleaned = {k: v for k, v in state.items() 
                          if not any(str(cid) in k for cid in ids)}
                atomic_write_json(state_file, cleaned)
        except Exception:
            pass
    current_user = session.get("username", "?")
    write_log(current_user, "批量删除", f"删除 {len(deleted_ids)} 条记录", "", request.remote_addr or '')
    return jsonify({
        "ok": True, 
        "message": f"删除 {len(deleted_ids)} 条记录",
        "deleted_ids": deleted_ids,
        "csrf_token": session.get("_csrf_token", "")
    })
```

### P0-2: `api_batch_edit` 是死代码

**位置**: `app.py` 第 581-617 行

**问题**: 该函数在第 595 行有一个 `return`，后面第 596-617 行的代码永远不会执行。同时引用了未定义的变量 `count` 和 `deleted_certs`，即使代码被执行也会抛出 `NameError`。

**修复方案**: 删除整个 `/api/batch_edit` 路由，功能已被 `/api/batch_handle` 和 `/api/batch_remind` 替代。

---

## P1 — 重要问题（影响用户体验或数据安全）

### P1-1: 导出 JSON 路由缺失

**位置**: `templates/data_manage.html` 第 125 行

**问题**: 前端有"导出 JSON"按钮链接到 `/export/json`，但后端只有 `/export` 路由（第 920 行）。虽然 Flask 对 `/export` 和 `/export/` 有重定向处理，但文件名是 `cert_data_export.json` 而不是预期的 `export.json`。更重要的是，前端链接是 `/export/json` 而不是 `/export`。

**影响**: 点击"导出 JSON"按钮会 404。

**修复方案**: 添加 `/export/json` 路由或修正前端链接。

### P1-2: CSP 被完全禁用

**位置**: `app.py` 第 143-153 行

**问题**: Content-Security-Policy 被注释掉，理由是 Tailwind Play CDN 注入的 style 标签无 nonce。这意味着：
- 没有 XSS 防护
- 可以注入任意外部脚本
- 在生产环境中是重大安全风险

**修复方案**: 迁移到 Tailwind CSS 预编译版本，或实现自定义 CSP 中间件来动态注入 nonce。

### P1-3: 数据库 schema 缺少多个字段

**位置**: `db.py` 第 42-129 行

**问题**: SQLite schema 中 `certs` 表缺少以下字段，但代码中使用：
- `cert_type` — schema 中有，但 `db_save_cert` 的 UPDATE 语句没有包含 `cert_type` 字段
- `responsible_users` — schema 中有 TEXT 列，但 `db_save_cert` 的 UPDATE 语句没有包含
- `updated_at` — schema 中有，但 `INSERT OR REPLACE` 在某些路径下没有设置

**影响**: 编辑记录时 `cert_type` 和 `responsible_users` 可能被清空。

**修复方案**: 检查 `db_save_cert` 函数中 UPDATE 语句是否遗漏了字段。

### P1-4: 密码复杂度要求过高

**位置**: `data.py` 第 191-201 行

**问题**: 密码必须同时包含大写+小写+数字+至少8位。这对内部系统来说过于严格，且没有提供密码策略配置选项。

**建议**: 降低为"至少8位，包含字母和数字"，或做成可配置项。

### P1-5: 登录限流基于内存，重启即丢失

**位置**: `app.py` 第 53-55 行

**问题**: `_login_attempts` 字典存储在内存中，容器重启后所有登录失败计数清零，攻击者可无限重试。

**修复方案**: 使用 SQLite 或 Redis 存储登录尝试记录。

### P1-6: `parse_expire_date` 不支持多种日期格式

**位置**: `daemon.py` 第 176-186 行

**问题**: 只支持三种格式 `%Y-%m-%dT%H:%M`、`%Y-%m-%d %H:%M`、`%Y-%m-%d`。如果用户输入其他格式（如 `2026/12/31`），会静默跳过记录而不报错。

**建议**: 增加 `dateutil.parser` 或使用多格式尝试解析。

---

## P2 — 一般改进（功能完善/代码质量）

### P2-1: 数据备份/恢复只支持 JSON 模式

**位置**: `app.py` 第 1258-1320 行

**问题**: `backup_data()` 和 `restore_data()` 直接读写 JSON 文件（`DATA_FILE`、`CONFIG_FILE` 等），但在 SQLite 模式下这些数据在数据库中。备份不会包含任何数据。

**修复方案**: 在 SQLite 模式下改为从数据库导出。

### P2-2: 操作日志在 SQLite 模式下不限制数量

**位置**: `data.py` 第 163-170 行

**问题**: JSON 模式下 `save_logs` 会保留最近 1000 条（`logs = logs[-1000:]`），但 SQLite 模式下 `write_log` 没有数量限制，日志表会无限增长。

**修复方案**: 在 `db_write_log` 中增加清理逻辑，或定期清理。

### P2-3: 没有数据完整性校验

**位置**: 多处

**问题**: 导入 Excel 时没有校验重复 ID，可能导致数据重复。备份恢复时也没有校验备份文件完整性。

### P2-4: 定时任务状态文件与数据库不一致

**位置**: `daemon.py` 第 56-66 行

**问题**: `remind_state.json` 在 JSON 模式下使用，但在 SQLite 模式下仍然使用文件存储。两种模式的数据源不同步，可能导致提醒重复或遗漏。

**建议**: SQLite 模式下将推送状态存入数据库。

### P2-5: 邮件发送没有 multipart 支持

**位置**: `daemon.py` 第 117 行

**问题**: 邮件使用纯文本格式拼接（`f"From: ...\r\n..."`），没有使用 `email.mime` 标准库构建 multipart 邮件。如果 HTML 内容包含特殊字符可能导致解析错误。

**建议**: 使用 `email.mime` 标准库构建规范邮件。

### P2-6: 前端分页只对 AJAX 列表有效

**位置**: `templates/index.html` 第 1052-1146 行

**问题**: 前端实现了客户端分页（perPage=20），但首页加载的是全部数据（`certs` 变量来自后端 `index()` 函数）。当数据量大时首屏加载慢。后端 `api_list_certs` 有服务端分页但前端首页没有使用。

**建议**: 首页也改为通过 `api_list_certs` 加载分页数据。

### P2-7: 缺少健康检查的详细信息

**位置**: `app.py` 第 1356-1358 行

**问题**: `/health` 只返回 "OK"，无法判断数据库连接是否正常、daemon 是否在运行等。

**建议**: 增加详细健康检查端点。

### P2-8: `calc_days_left` 精度问题

**位置**: `data.py` 第 435-446 行

**问题**: 使用 `total_seconds() / 86400` 计算天数，会有浮点精度问题。比如 `7.99999` 天可能被误判为 7 天而非 8 天。

**建议**: 使用 `math.floor` 或 `round` 明确处理。

---

## 总结

| 等级 | 数量 | 关键项 |
|------|------|--------|
| P0 | 2 | 批量删除 API 缺失、死代码 |
| P1 | 4 | 导出 JSON 路由缺失、CSP 禁用、数据库 UPDATE 缺字段、密码策略 |
| P2 | 7 | 备份恢复、日志限制、状态同步、邮件格式、分页、健康检查、精度 |

**建议优先修复顺序**: P0-1 → P0-2 → P1-1 → P1-3 → P2-1
