# 小黑 — 第三轮审查反馈（部署实测 + 代码审查）

> **审查者：** 小白（架构师 + 产品经理 + 测试工程师 三重视角）  
> **审查时间：** 2026-06-26  
> **审查方式：** 实际在宿主机 124.222.198.26 上 Docker 部署并测试  
> **状态：** 🔴 有阻塞性 bug，部署失败

---

## 一、部署实测发现的新 Bug（本次新增）

### 🔴 P0 — `csrf_token()` 模板调用错误（阻塞登录）

**现象：** 访问 `http://124.222.198.26:5188/login` 返回 **500 Internal Server Error**

**根因：** `auth.py:inject_globals()` 返回 `dict(csrf_token=_generate_csrf_token())`，其中 `csrf_token` 是一个**字符串**。但所有模板中使用的是 `{{ csrf_token() }}`（带括号调用函数），Jinja2 尝试调用字符串对象，抛出 `TypeError: 'str' object is not callable`。

**受影响文件（17 处）：**

| 文件 | 出现次数 |
|------|----------|
| `templates/login.html` | 1 |
| `templates/index.html` | 4 |
| `templates/edit.html` | 1 |
| `templates/config.html` | 3 |
| `templates/users.html` | 4 |
| `templates/logs.html` | 1 |
| `templates/restore.html` | 1 |
| `templates/add_batch.html` | 1 |
| `templates/data_manage.html` | 1 |

**修复方案（二选一）：**

**方案 A（推荐）：** 改模板，去掉括号 —— 把所有 `{{ csrf_token() }}` 改为 `{{ csrf_token }}`。改动小，风险低。

**方案 B：** 改 `auth.py`，让 `csrf_token` 变成可调用对象：
```python
def inject_globals():
    def _csrf():
        return _generate_csrf_token()
    return dict(csrf_token=_csrf, badge_count=badge_count)
```

**我的建议：选方案 A**，因为 `_generate_csrf_token()` 本来就是返回字符串值的，模板不该用 `()` 调用。

---

### 🔴 P0 — `index()` 函数未定义变量导致 500

**文件：** `app.py:260-323`

**现象：** 即使登录成功，首页 `index` 也会崩溃。

**根因：** `index()` 函数中使用了 `page_certs`、`page`、`per_page`、`total`、`total_pages` 这些变量，但这些变量在函数中**从未定义**。函数末尾 `render_template(..., certs=page_certs, page=page, ...)` 引用了未定义的变量。

同时，`chart_certs` 也未定义（第 304 行 `len(chart_certs)`），实际应该用 `certs`。

**影响：** 登录后首页白屏，系统完全不可用。

---

## 二、之前 review 中的问题状态跟踪

### ✅ 已确认修复

| 编号 | 问题 | 来源 |
|------|------|------|
| 1 | `_certs_cache` 未初始化 | Phase 1 REVIEW_BLACK |
| 2 | `DATA_DIR` 定义顺序 | Phase 1 REVIEW_BLACK |
| 3 | conftest.py 缓存重置 | Phase 1 REVIEW_BLACK |
| 4 | 术语"证书"→"到期项" | Phase 1 REVIEW_BLACK |
| 5 | docker-compose.yml 服务名 | Phase 1 REVIEW_BLACK |
| 6 | db.py 迁移 INSERT OR REPLACE | Phase 1 REVIEW_BLACK |
| 7 | supervisord.conf 端口硬编码 | Phase 1 REVIEW_BLACK |
| 8 | Dockerfile HEALTHCHECK | Phase 1 REVIEW_BLACK |
| 9 | webhook 集成 | Phase 2 REVIEW_BLACK |
| 10 | pyOpenSSL 多余依赖 | Phase 2 REVIEW_BLACK |
| 11 | .dockerignore 过度忽略 | Phase 2 REVIEW_BLACK |

### ❌ 仍未解决

| 编号 | 问题 | 来源 | 严重度 |
|------|------|------|--------|
| 12 | **`db.py` 未集成到 app.py/daemon.py** | Phase 2 REVIEW_BLACK | 🔴 P0 |
| 13 | **`csrf_token()` 模板调用错误** | 本次部署实测 | 🔴 P0 |
| 14 | **`index()` 未定义变量 `page_certs`/`chart_certs`** | 本次部署实测 | 🔴 P0 |
| 15 | `db.py` 迁移布尔值大小写不一致 | Phase 2 REVIEW_BLACK | 🟡 P1 |

---

## 三、给小黑的修复清单

### 第一轮：止血（今天必须完成）

1. **修复 `csrf_token()` 模板调用** — 17 处模板全部改为 `{{ csrf_token }}`（去掉括号）
2. **修复 `index()` 函数未定义变量** — `page_certs`、`chart_certs` 等变量需正确定义
3. **修复 `db.py` 迁移逻辑** — `str(v)` 改为 `str(v).lower()` 匹配小写判断

### 第二轮：核心架构（本周内）

4. **集成 `db.py` 到 `app.py` 和 `daemon.py`** — 在 `data.py` 加 `USE_SQLITE` 开关分发
5. **补充 `daemon.py` 的 SQLite 支持** — `daemon.py` 目前仍用 JSON 读写，需适配 `db.py`

### 第三轮：完善（下周）

6. **补充测试覆盖** — `daemon.py` 核心逻辑、`dingtalk.py` 签名算法
7. **清理未集成模块** — 确认 `webhook.py` 是否完成集成

---

## 四、本次部署总结

| 项目 | 结果 |
|------|------|
| SSH 连接 | ✅ 成功 |
| Docker 版本 | ✅ 29.3.0 + Compose v5.1.0 |
| 镜像构建 | ✅ 成功 |
| 容器启动 | ✅ supervisord 启动成功（web + daemon 两进程） |
| Web 页面 | ❌ 500 错误（`csrf_token()` 调用失败） |
| 登录功能 | ❌ 阻塞 |
| 首页 | ❌ 未定义变量崩溃 |
| 后台 daemon | ✅ 日志无报错（但 JSON 层仍在运行） |

**一句话总结：构建和启动都没问题，但应用层有两个 P0 bug 导致系统完全不可用。**
