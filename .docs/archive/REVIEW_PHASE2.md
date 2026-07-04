# 小黑 Phase 2 审查结果 — 小白

> **审查时间：** 2026-06-26  
> **审查者：** 小白（架构师 + 产品经理）  
> **状态：** ✅ Phase 1 bug 已修复，Phase 2 核心问题仍需处理

---

## 一、Phase 1 修复确认 ✅

以下问题已确认修复：

| 问题 | 状态 |
|------|------|
| `_certs_cache` 未初始化 | ✅ 已修复（data.py:203） |
| `DATA_DIR` 定义在 `_get_fernet()` 之后 | ✅ 已修复（data.py:24） |
| `conftest.py` 缺少 `_certs_cache` 重置 | ✅ 已修复 |
| `db.py` 迁移用 `INSERT` 而非 `INSERT OR REPLACE` | ✅ 已修复 |
| `docker-compose.yml` 服务名 `cert-monitor` → `item-monitor` | ✅ 已修复 |
| 大部分"证书"文字替换为"到期项" | ✅ 已修复 |

---

## 二、Phase 2 仍需处理的问题

### 🔴 P0 — 致命（阻塞部署）

#### 2.1 `db.py` 仍未集成到 `app.py` 和 `daemon.py`

**这是最大的问题。** 小黑创建了完整的 SQLite 数据库层（415 行，含 init_db、migrate_json_to_sqlite、db_load_certs、db_save_cert 等全部 CRUD），但 **`app.py` 和 `daemon.py` 没有调用任何 `db.*` 函数**。

现状：
- `_auto_migrate()` 在 app.py:107 调用了一次 `init_db()` 和 `migrate_json_to_sqlite()`
- 之后所有的 `load_certs()`、`save_certs()`、`load_users()` 等仍然走 `data.py`（JSON 文件）
- SQLite 中的数据迁移后不会被读取、更新或删除
- `db.py` 的所有 `db_load_*`、`db_save_*`、`db_delete_*` 函数从未被调用
- **SQLite 是一个完全未被使用的空壳**

**影响：** 整个 SQLite 迁移白做，系统仍然是 JSON 文件架构，P0 问题（无索引、无事务、无搜索）依然存在。

**修复方案：** 需要在 `app.py` 和 `daemon.py` 中所有 `data.py` 的调用处替换为 `db.py` 的对应函数。

**推荐方案（最小改动）：** 在 `data.py` 中添加一个 `USE_SQLITE` 开关：

```python
USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"

def load_certs():
    if USE_SQLITE:
        from db import db_load_certs
        return db_load_certs()
    # 原有 JSON 逻辑
    ...
```

这样只需改一个环境变量即可切换，不需要大规模修改 app.py。

---

#### 2.2 `db.py` 迁移逻辑有缺陷

**问题 1：** 迁移用户时没有处理密码哈希格式兼容。

```python
# db.py:168
conn.execute("""INSERT OR IGNORE INTO users ...""",
    (u.get("password", ""), ...))
```

如果 `users.json` 中的密码已经是 werkzeug 哈希（>50 字符），直接插入没问题。但如果之前 `_migrate_password()` 已经改过，密码格式可能不一致。

**问题 2：** 迁移配置时，布尔值 `True/False` 被转为字符串 `"True"/"False"`，但 `db_load_config()` 只检查 `"true"/"false"`（小写），导致 `remind_days` 等配置加载异常。

```python
# db.py:186-193
for k, v in cfg.items():
    if isinstance(v, list):
        v = json_mod.dumps(v)
    else:
        v = str(v)  # True -> "True" (大写)
```

```python
# db.py:339
elif v.lower() in ("true", "false"):  # 只匹配小写
    v = v.lower() == "true"
```

**修复：** 迁移时用 `str(v).lower()` 或者在 `db_load_config()` 中也匹配大写。

---

### 🟡 P1 — 重要

#### 2.3 少量"证书"文字未替换

以下文件仍有"证书"文字：

| 文件 | 行数 | 内容 |
|------|------|------|
| `deploy.sh` | 3 | `# 一键部署脚本 — 证书到期监控系统` |
| `README.md` | 7 | `添加/编辑/删除证书` |
| `CHANGELOG.md` | 16, 79 | 描述性文字 |
| `templates/add_batch.html` | 138 | `如：SSL证书、年报截止` |
| `templates/edit.html` | 120 | datalist 选项 `SSL证书` |
| `templates/index.html` | 612 | datalist 选项 `SSL证书` |
| `tests/test_data.py` | 29, 41, 106 | 测试 docstring |
| `tests/test_db.py` | 54 | 测试 docstring |
| `tests/conftest.py` | 45 | 测试 docstring |
| `webhook.py` | 34, 52, 68 | 函数 docstring |

**建议：** 统一替换为"到期项"/"到期数据"。datalist 中的 `SSL证书` 作为示例类型可以保留（和其他如"许可证""系统维保"并列）。

---

#### 2.4 `supervisord.conf` 硬编码了端口

```ini
[program:web]
environment=PORT="5188"
```

应改为从环境变量读取：
```ini
environment=PORT="%(_env_PORT)s"
```

---

#### 2.5 `Dockerfile` 中 HEALTHCHECK 引用端口可能不生效

```dockerfile
ARG PORT=5188
...
HEALTHCHECK CMD python -c "... http://localhost:${PORT}/health ..."
```

`${PORT}` 在 Dockerfile ARG 中是构建时变量，但 HEALTHCHECK 的 CMD 在运行时执行。如果构建时 PORT 不是 5188，HEALTHCHECK 会失败。

**修复：** 使用环境变量而非 ARG：
```dockerfile
ENV PORT=5188
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"
```

---

#### 2.6 `webhook.py` 已创建但未集成

小黑创建了 `webhook.py`（76 行），定义了 webhook 回调功能，但：
- `app.py` 中没有调用 `send_webhook()` 的端点
- `daemon.py` 中没有在推送成功后触发 webhook 回调
- 配置文件里没有 webhook 相关配置

**建议：** 要么删除 `webhook.py`（未完成的功能），要么在 `app.py` 中添加 `POST /api/webhook/test` 端点并在推送成功后触发。

---

#### 2.7 `prometheus-client` 和 `pyOpenSSL` 依赖多余

```
prometheus-client==0.20.0
pyOpenSSL==23.3.0
```

代码中没有使用 Prometheus 指标导出，也没有使用 OpenSSL 模块。

---

#### 2.8 `docker-compose.yml` 端口变量名改了但 Dockerfile 没改

`docker-compose.yml` 用了 `${ITEM_MONITOR_PORT:-5188}`，但 `Dockerfile` 中仍然是 `PORT=5188`。

---

### 🟢 P2 — 建议改进

#### 2.9 测试覆盖率低

- `test_db.py` 测试的是 `db.py` 的 SQLite 功能，而 `db.py` 根本没被集成到 app 中
- 没有测试 `daemon.py` 的核心逻辑
- 没有测试 `dingtalk.py` 的签名算法
- `test_auth.py` 只有 30 行

#### 2.10 无优雅关停

`daemon.py` 的 SIGTERM 处理只是设置 `_running = False`，没有 flush logs、save state 等操作。

#### 2.11 `.dockerignore` 忽略了 `README.md` 和 `tests/`

虽然对运行时没影响，但不利于调试。

---

## 三、给小黑的实施建议

### 第一步：集成 `db.py`（最关键）

在 `data.py` 顶部添加：
```python
USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"
```

修改 `load_certs()`、`save_certs()`、`load_users()`、`save_users()`、`load_config()`、`save_config()`、`load_logs()`、`save_logs()`、`write_log()`、`calc_stats()` 等函数，根据 `USE_SQLITE` 开关分发到 `db.py` 或原有 JSON 逻辑。

### 第二步：修复 `db.py` 迁移逻辑

- `db.py:189` 改为 `v = str(v).lower()` 以匹配 `db_load_config()` 的小写判断
- 确保 `INSERT OR REPLACE` 用于所有迁移

### 第三步：统一术语

全量替换"证书"→"到期项"（除 datalist 示例外）。

### 第四步：清理

- 删除 `webhook.py` 或完成集成
- 删除 `prometheus-client` 和 `pyOpenSSL` 依赖
- 修复 `supervisord.conf` 和 `Dockerfile` 中的硬编码

---

## 四、总结

| 类别 | 状态 |
|------|------|
| Phase 1 bug 修复 | ✅ 已完成 |
| SQLite 集成 | ❌ 未完成（最大问题） |
| 术语统一 | ⚠️ 基本完成，少量遗漏 |
| Docker/部署配置 | ⚠️ 有小问题 |
| 测试覆盖 | ⚠️ 偏低 |
| 代码清理 | ⚠️ 有多余依赖和未集成模块 |

**核心建议：** 先把 `db.py` 集成到 `app.py` 和 `daemon.py`，这是最有价值的改进。其他问题都是锦上添花。
