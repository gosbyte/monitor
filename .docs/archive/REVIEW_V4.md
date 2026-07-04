# 小黑修复审查 V4 — 最终反馈

**审查人**: 小白（架构师 + 测试）  
**审查日期**: 2026-06-28  
**审查版本**: commit caef8c3  

---

## 一、上一轮 P0/P1 修复完成情况

| 问题 | 状态 | 评价 |
|------|------|------|
| P0-1: 默认密码检测（哈希长度 → 标志位） | ✅ 已修复 | 改用 `force_change_password` 标志位，正确 |
| P0-2: daemon.py 文件句柄泄漏 | ✅ 已修复 | 加了 `with` 语句 + `try/except` |
| P0-3: init_data.py 跳过迁移 | ✅ 已修复 | 调用了 `migrate_json_to_sqlite()` |
| P0-4: save_users() 逐条 INSERT | ✅ 已修复 | 改用 `executemany` 批量插入 |
| P1-1: CSP nonce 用 builtins | ✅ 已修复 | 改用 `flask.g`，线程安全 |
| P1-2: load_certs() 无缓存 | ✅ 已修复 | 加了 5s TTL 缓存 |
| P1-3: save_certs() id=None | ✅ 已修复 | 加了过滤和 warning 日志 |
| P1-4: load_state/save_state 无异常处理 | ✅ 已修复 | 原子写入 + 异常清理 |

**结论：上一轮提出的 8 个问题全部修复到位，做得很好 👍**

---

## 二、V4 新发现的问题

### 🔴 P0-5: `save_users()` 批量插入时 `executemany` 可能因唯一约束失败

```python
# data.py
conn.executemany("""INSERT OR REPLACE INTO users ...""", [...])
```

**问题**: 如果 `users` 列表中有重复的 `username`（理论上不应该发生，但防御性编程很重要），`executemany` 会在单条失败时整个批次回滚。`INSERT OR REPLACE` 虽然是合法的 SQLite 语法，但批量执行时如果某条记录的主键冲突，会先 DELETE 再 INSERT，这在事务中可能导致外键约束问题。

**更重要的是**: `force_change_password` 列在新建 users 表时默认值是 `1`，但 `executemany` 中 `int(u.get("force_change_password", 1))` 对于**已存在的用户**（比如从 JSON 迁移过来的）会把 `force_change_password` 设为 `1`，意味着所有用户首次登录都会被强制改密码——包括非 admin 用户。

**建议**: 迁移时只对 admin 设置 `force_change_password=1`，普通用户设为 `0`。

### 🔴 P0-6: `load_state()` 异常处理后 `save_state()` 的 `tmp` 变量可能未定义

```python
def save_state(state):
    try:
        tmp = state_file + ".tmp"
        with open(tmp, "w", ...) as f:
            json.dump(state, f, ...)
        os.replace(tmp, state_file)
    except IOError as e:
        logger.error(...)
        try:
            os.unlink(tmp)  # ← 如果 open() 成功但 json.dump() 失败，tmp 已定义；但如果 open() 失败，tmp 未定义
        except OSError:
            pass
```

**问题**: 如果 `open(tmp, "w")` 成功但 `json.dump()` 抛 `IOError`（比如磁盘满了），`tmp` 变量已定义，清理没问题。但如果 `open()` 本身就失败（比如权限不足），`tmp` 变量不会定义，`os.unlink(tmp)` 会报 `NameError`。

**建议**: 在 `try` 之前初始化 `tmp = None`，清理时判断 `if tmp:`。

### 🟡 P1-5: CSP 仍保留 `'unsafe-inline'`

```
script-src 'self' 'nonce-XXX' 'unsafe-inline';
style-src 'self' 'nonce-XXX' 'unsafe-inline';
```

**问题**: `'unsafe-inline'` 完全抵消了 nonce 的安全价值。任何内联脚本/样式都能执行，XSS 攻击者只需注入 `<script>alert(1)</script>` 即可。

**建议**: 
- 短期内保留 `'unsafe-inline'` 但标记 TODO
- 长期目标是移除 `'unsafe-inline'`，将所有内联脚本改为外部文件或 nonce 注入

### 🟡 P1-6: `before_request` 和 `after_request` 的 nonce 不一致风险

```python
@app.before_request
def _inject_csp_nonce():
    g.csp_nonce = secrets.token_hex(16)  # 生成 nonce A

@app.after_request
def set_security_headers(response):
    nonce = getattr(g, 'csp_nonce', secrets.token_hex(16))  # 读取 nonce A
```

**问题**: 如果在 `before_request` 和 `after_request` 之间有中间件或钩子修改了 `g.csp_nonce`，会导致 CSP header 的 nonce 和模板中的 nonce 不一致，脚本加载失败。

**实际风险较低**（Flask 的 `g` 对象是请求级隔离的），但建议在 `after_request` 中直接用 `g.csp_nonce` 而不是 `getattr(g, 'csp_nonce', ...)`，保持一致性。

### 🟡 P1-7: `db.py` 迁移时 `force_change_password` 对所有用户都是 1

```python
# db.py migrate_json_to_sqlite
u.get("lock_until"), 1)  # force_change_password = 1 for ALL migrated users
```

**问题**: 迁移时所有用户（包括普通用户）都被标记为需要改密码。如果系统有多个用户，普通用户首次登录也会被拦截，体验不好。

**建议**: 只对 `role == 'admin'` 的用户设 `force_change_password=1`，普通用户设 `0`。

### 🟢 P2-1: `data.py` 中 `USE_SQLITE` 是模块级变量，daemon.py 也 import 了

daemon.py 从 data.py import 了 `USE_SQLITE`，但 daemon.py 是单进程运行的，而 app.py 是多进程（supervisor 管理的 web 进程）。如果两个进程同时修改 `USE_SQLITE` 环境变量（不太可能），会有不一致。建议加注释说明。

### 🟢 P2-2: `conftest.py` 缺少 SQLite 模式测试

现有的 `temp_data_dir` fixture 设置了 `USE_SQLITE` 环境变量但没在 data.py 中生效（data.py 的 `USE_SQLITE` 在模块加载时就确定了）。测试可能只覆盖了 JSON 模式。

---

## 三、综合评分

| 维度 | V3 得分 | V4 得分 | 变化 |
|------|---------|---------|------|
| 架构改进 | 8/10 | **9/10** | ↑ 数据层统一得很好 |
| 安全性 | 7/10 | **8/10** | ↑ CSP 恢复 + 强制改密码 |
| 代码质量 | 6/10 | **8/10** | ↑ daemon.py 健壮性大幅提升 |
| 测试覆盖 | 5/10 | **6/10** | ↑ 有 conftest.py 了 |
| **整体** | **6.5/10** | **8/10** | ↑↑ 显著进步 |

---

## 四、给小黑的下一步行动

### 必须修复（P0）
1. **迁移时区分 admin 和普通用户** — `force_change_password` 只对 admin 设为 1
2. **save_state 异常处理** — `tmp` 变量初始化防御

### 应该修复（P1）
3. **CSP 逐步移除 `'unsafe-inline'`** — 标记 TODO，制定计划
4. **after_request 用 `g.csp_nonce` 替代 `getattr`** — 保持一致性

### 建议改进（P2）
5. **补充 SQLite 模式测试** — 确保 `USE_SQLITE=1` 下测试通过
6. **save_users 加唯一性校验** — 防止重复用户名
