# 小黑修复审查报告 V3

**审查人**: 小白（架构师 + 测试）  
**审查日期**: 2026-06-28  
**审查范围**: commit 099a348 — P0/P1 修复  

---

## 一、修复内容概述

| 修复项 | 状态 | 评价 |
|--------|------|------|
| P0-1: 统一数据层（SQLite） | ✅ 已实现 | 架构合理，但存在隐患（见下文） |
| P0-2: `/api/cert` 500 错误 | ⚠️ 未修复 | 说是"实测无500"，但没说明原因 |
| P0-3: 默认密码强制修改 | ✅ 已实现 | 功能完整，但检测逻辑有缺陷 |
| P1-1: 恢复 CSP | ✅ 已实现 | nonce 注入方案可行 |
| P1-2: daemon.py 改用 data.py | ✅ 已实现 | 代码精简了很多 |
| P1-3: API CSRF token 轮换 | ✅ 已实现 | 只对 POST/PUT/DELETE 轮换，正确 |
| P1-4: 移除文件锁竞态 | ✅ 已实现 | 合理 |
| P1-5: Supervisor 端口硬编码 | ✅ 已实现 | 改为 `${PORT:-5188}` |

---

## 二、发现的新的 P0 问题

### 🔴 P0-1: `save_users()` 在 SQLite 模式下逐条 INSERT，丢失了唯一约束保护

```python
# data.py 中的 save_users 在 USE_SQLITE 模式下：
for u in users:
    db_save_user(u)  # 逐条 INSERT OR REPLACE
```

**问题**: `db_save_user` 使用 `INSERT OR REPLACE`，这意味着如果有重复用户名，后面的会覆盖前面的。**但 `load_users()` 返回的是完整列表**，如果用户数 > 100，每次保存都会触发 100+ 次 INSERT。

**建议**: 改为批量插入或使用 `REPLACE INTO ... VALUES (...), (...), (...)` 一次完成。

### 🔴 P0-2: 默认密码检测逻辑不可靠

```python
# app.py index() 中：
if current_user.get("password", "").startswith("scrypt:") and len(current_user.get("password", "")) < 60:
    return redirect(url_for("change_password"))
```

**问题**:
1. **依赖哈希长度判断** — 这是脆弱的。`admin123` 的 scrypt 哈希长度 < 60，但如果有人设置了短密码（如 `Ab1!`），也会被标记为"默认密码"
2. **无法区分"默认密码"和"用户自己设置的短密码"** — 小黑修改密码后，新密码的哈希同样可能 < 60 字节
3. **没有标记机制** — 应该用 `force_change_password` 标志位，而不是猜哈希长度

**建议**: 在 users 表中增加 `force_change_password BOOLEAN DEFAULT 1` 字段，首次登录后设为 0。

### 🔴 P0-3: `daemon.py` 的 `load_state()` 和 `save_state()` 没有异常处理

```python
def load_state():
    result = json.load(open(...)) if os.exists(...) else {}  # 没有 with 语句！
```

**问题**:
1. **文件句柄泄漏** — `json.load(open(...))` 没有 `with` 语句，文件可能不被关闭
2. **没有异常处理** — 如果 `remind_state.json` 损坏，daemon 会 crash 并退出
3. **非原子写入** — `save_state` 直接写文件，没有 `.tmp` + `os.replace` 原子操作

**建议**: 加 `try/except` 和 `with` 语句。

### 🔴 P0-4: `data.py` 的 `load_certs()` 在 SQLite 模式下不使用缓存

```python
def load_certs():
    if USE_SQLITE:
        from db import db_load_certs  # 每次都查数据库
        return db_load_certs()
    # JSON 模式有 _certs_cache 缓存
    global _certs_cache  # ...
```

**问题**: SQLite 模式每次调用都查数据库，而 JSON 模式有 5 秒缓存。高频 API 调用（如前端轮询）会导致不必要的数据库查询。

**建议**: 在 `db_load_certs()` 中也加缓存，或者统一缓存策略。

---

## 三、发现的新的 P1 问题

### 🟡 P1-1: CSP nonce 注入方式危险

```python
# app.py _inject_csp_nonce():
import builtins
builtins._current_csp_nonce = _csp_nonce
```

**问题**: 使用 `builtins` 模块共享全局状态是反模式。如果多个请求并发进入 `_inject_csp_nonce()`，nonce 可能被覆盖。

**建议**: 用 Flask 的 `g` 对象：`from flask import g; g.csp_nonce = _csp_nonce`

### 🟡 P1-2: `_load_config()` 和 `load_config()` 命名冲突

```python
# daemon.py 中：
def _load_config():  # 私有函数，尝试解密
    ...
# 但 check_and_remind() 中调用的是：
cfg = load_config()  # 这是从 data.py import 的公开函数
```

**问题**: `_load_config()` 定义了但从未被调用。`load_config()` 在 daemon.py 中是从 `data.py` import 的，但 `data.py` 的 `load_config()` 在 USE_SQLITE=1 时调用 `db_load_config()`，后者返回的布尔值是字符串 `"true"/"false"`，而代码中用 `bool()` 判断可能不符合预期。

### 🟡 P1-3: `save_certs()` 在 SQLite 模式下对列表的处理不一致

```python
def save_certs(certs):
    if USE_SQLITE:
        if isinstance(certs, list):
            for c in certs:
                db_save_cert(c)  # 逐条保存
        else:
            db_save_cert(certs)
```

**问题**: `db_save_cert()` 内部用 `INSERT OR REPLACE`，但如果 `certs` 列表中有 `id=None` 的记录，会执行 INSERT 而非 UPDATE，导致重复数据。

### 🟡 P1-4: `init_data.py` 在 SQLite 模式下跳过了所有 JSON 文件的初始化

```python
if USE_SQLITE:
    from db import init_db
    init_db()
    print("[INIT] SQLite database initialized")
    return  # 直接返回！
```

**问题**: 如果 `USE_SQLITE=1` 但数据库已存在（比如从 JSON 迁移过），`init_db()` 只会 `CREATE TABLE IF NOT EXISTS`，**不会迁移数据**。`db.py` 中有 `migrate_json_to_sqlite()` 函数但 `init_data.py` 中没有调用它。

---

## 四、发现的 P2 建议

### 2-1: 缺少单元测试验证
- FIX_SUMMARY.md 说 "19/19 测试通过"，但没说明测试覆盖哪些场景
- 建议补充：SQLite 模式 CRUD、默认密码检测、CSP nonce 注入、CSRF 轮换

### 2-2: `change_password.html` 引用了不存在的 JS 文件
- `<script src="/static/dark-mode.js"></script>` — 这个文件不存在
- `<script src="/static/lucide.umd.min.js"></script>` — 不确定是否已上传

### 2-3: CSP 中保留了 `'unsafe-inline'`
```
script-src 'self' 'nonce-XXX' 'unsafe-inline';
```
`'unsafe-inline'` 削弱了 CSP 的安全性，应该逐步移除。

---

## 五、总结评分

| 维度 | 得分 | 说明 |
|------|------|------|
| 架构改进 | 8/10 | SQLite 统一数据层方向正确，但实现细节需打磨 |
| 安全性 | 7/10 | CSP 恢复 + CSRF 修复是好方向，但默认密码检测和 nonce 注入有隐患 |
| 代码质量 | 6/10 | daemon.py 精简了，但引入了文件句柄泄漏等问题 |
| 测试覆盖 | 5/10 | 声称 19/19 通过，但未见测试代码 |
| 整体 | **6.5/10** | 方向正确，细节待修 |

---

## 六、给小黑的下一步行动

### 必须修复（P0）
1. **默认密码检测** — 改用 `force_change_password` 标志位
2. **daemon.py load_state/save_state** — 加 `with` 语句和 `try/except`
3. **init_data.py** — SQLite 模式下也要调用 `migrate_json_to_sqlite()`
4. **save_users()** — SQLite 模式下改用批量插入

### 应该修复（P1）
5. **CSP nonce 注入** — 改用 `flask.g` 替代 `builtins`
6. **load_certs() 缓存** — SQLite 模式也加缓存
7. **save_certs()** — 处理 `id=None` 的情况

### 建议改进（P2）
8. **补充单元测试** — 覆盖核心逻辑
9. **检查静态资源** — dark-mode.js 和 lucide.umd.min.js 是否存在
10. **逐步移除 CSP 中的 'unsafe-inline'**
