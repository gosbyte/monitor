# 小黑修复审查 V6 — 最终全面审查

**审查人**: 小白（架构师 + 测试）  
**审查日期**: 2026-06-28  
**审查版本**: commit ec21939  

---

## 一、V5 遗留问题修复验证

| 问题 | 状态 | 评价 |
|------|------|------|
| P1: CSP 中的 `'unsafe-inline'` | ⏸️ 暂缓 | 小黑选择不修，保留 TODO 注释，可接受 |
| P2: 补充单元测试 | ⏸️ 暂缓 | 有 conftest.py 基础，完整测试延后，可接受 |

---

## 二、全面代码审查 — 新发现的问题

### 🔴 P0-7: `api_list_certs` GET API 可能 KeyError

```python
# app.py line 716
return jsonify({...,"csrf_token": session["_csrf_token"]})
```

**问题**: 用户首次访问 `/api/cert`（GET）时，session 中可能还没有 `_csrf_token` 键。`_generate_csrf_token()` 只在模板渲染时被调用（通过 `inject_globals` 上下文处理器），但 GET API 不渲染模板。

**复现**: 新部署 → 用户首次登录 → 访问 `/api/cert` → KeyError。

**影响**: 前端 AJAX 获取证书列表失败，页面白屏。

**修复**: 在 `api_list_certs` 中改用 `session.get("_csrf_token", "")` 或在 `@login_required` 装饰器中确保 token 已生成。

### 🔴 P0-8: `db_transaction` 每个事务创建新连接，但 `get_db()` 未设置 `row_factory`

```python
# db.py line 18-24
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ...
```

**问题**: `db_transaction` 每次调用都 `get_db()` → 新连接 → `yield` → `close()`。但 `db_save_cert()` 中调用了 `db_transaction()` 两次（一次检查 existence，一次 UPDATE/INSERT），这是两个独立事务。如果第一次查到不存在，第二次 INSERT 成功，但中间有其他事务修改了数据，会导致竞态条件。

**更严重的问题**: `db_save_cert` 在 `isinstance(certs, list)` 时逐条调用 `db_save_cert(c)`，每条都是一个独立事务。`save_certs` 中传入的是完整列表，每次保存都要执行 N 次独立事务。

**修复**: `save_certs` 在 SQLite 模式下应使用单个事务批量保存。

### 🟡 P1-8: `_check_api_csrf` 对 GET 请求也要求 CSRF token

```python
def _check_api_csrf():
    token = request.headers.get("X-CSRF-Token")
    if not token and request.is_json:
        token = request.json.get("_csrf_token")
    if not token or token != session.get("_csrf_token"):
        return False
```

**问题**: 虽然当前所有 GET 路由都不调用 `_check_api_csrf()`，但这个函数的设计是"必须有 CSRF token"。如果未来有人在 GET API 上加了 `_check_api_csrf()` 调用，GET 请求会被拒绝。

**建议**: 在 `_check_api_csrf` 开头加 `if request.method == "GET": return True`，明确 GET 不需要 CSRF。

### 🟡 P1-9: `inject_globals` 和 `inject_csp_nonce` 两个 context_processor 的优先级

```python
# app.py line 110
app.context_processor(inject_globals)  # auth.py 的 inject_globals

# app.py line 130-133
@app.context_processor
def inject_csp_nonce():
    return dict(csp_nonce=getattr(g, 'csp_nonce', ''))
```

**问题**: Flask 的 `context_processor` 返回值会被合并。`inject_globals` 返回 `{csrf_token, badge_count, csp_nonce=""}`，`inject_csp_nonce` 返回 `{csp_nonce=real_nonce}`。由于 `inject_csp_nonce` 是后来注册的，它的 `csp_nonce` 会覆盖 `inject_globals` 的空值。

**实际影响**: 功能正常（`inject_csp_nonce` 的 nonce 正确覆盖），但代码可读性差。

**建议**: 统一到一个 context_processor 中，或至少在 `inject_globals` 中移除 `csp_nonce=""`。

### 🟡 P1-10: `data.py` 中 `_migrate_password_sqlite` 在每次 `load_users()` 时被调用

```python
def load_users():
    if USE_SQLITE:
        users = db_load_users()
        _migrate_password_sqlite(users)  # 每次 load 都检查！
        return users
```

**问题**: `_migrate_password_sqlite` 遍历所有用户，检查密码长度 < 50。如果用户数很多，每次 `load_users()` 都执行这个检查，性能浪费。而且 `_migrate_password_sqlite` 修改了传入的 users 列表后写回数据库，这意味着每次 `load_users()` 都可能触发一次数据库写操作。

**建议**: 只在首次检测到明文密码时迁移一次，之后不再检查。

### 🟢 P2-3: `db.py` 中 `init_db()` 硬编码了默认管理员密码

```python
# db.py line 132-137
default_password = generate_password_hash("admin123")
conn.execute(
    "INSERT OR IGNORE INTO users (username, name, password, role) VALUES (?, ?, ?, ?)",
    ("admin", "管理员", default_password, "admin")
)
```

**问题**: 如果 `init_db()` 被多次调用（比如每次 app.py 启动），`INSERT OR IGNORE` 会跳过已存在的 admin 用户。但如果数据库被清空重建，admin 密码始终是 `admin123`。

**建议**: 这是设计意图（首次部署默认密码），但可以加注释说明。

### 🟢 P2-4: `daemon.py` 中 `load_config()` 和 `_load_config()` 命名混淆

```python
# daemon.py
from data import load_config  # 公开函数
def _load_config():  # 私有函数，尝试解密
    ...
    result = load_config()  # 调用公开的 load_config
```

**问题**: `_load_config()` 定义了但从未被调用。`check_and_remind()` 中直接调用 `load_config()`（公开函数）。

**建议**: 删除 `_load_config()` 死代码。

---

## 三、综合评分

| 维度 | V5 | V6 |
|------|----|----|
| 架构改进 | 9 | **9.5** |
| 安全性 | 8.5 | **9** |
| 代码质量 | 9 | **8.5** |
| 测试覆盖 | 6 | **6** |
| **整体** | **8.3** | **8.3** |

---

## 四、总结

小黑修复非常认真，从 V3 到 V5 解决了 14 个问题，架构从混乱走向统一。V6 发现的主要问题集中在：

1. **P0-7**: GET API 的 `session["_csrf_token"]` 可能不存在 → 容易复现
2. **P0-8**: `save_certs` 在 SQLite 模式下逐条事务保存 → 性能问题

其余都是 P1/P2 级别的优化建议。

**建议小黑优先修复 P0-7 和 P0-8**，这两个是实际会影响运行的问题。
