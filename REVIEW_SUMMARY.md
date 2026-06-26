# 小黑 — 审查总览（小白出品）

> **最后更新：** 2026-06-26  
> **仓库：** https://github.com/gosbyte/monitor  
> **状态：** 🟢 所有 P0/P1 已修复，等待部署验证

---

## 当前状态总览

| 类别 | 状态 | 说明 |
|------|------|------|
| Phase 1 基础 bug | ✅ 全部修复 | `_certs_cache`、`DATA_DIR` 顺序、conftest 缓存重置 |
| 术语统一 | ✅ 全部修复 | "证书" → "到期项" |
| Docker/部署配置 | ✅ 全部修复 | supervisord、Dockerfile、docker-compose、.dockerignore |
| csrf_token 模板 | ✅ 已修复 | 17 处 `{{ csrf_token() }}` → `{{ csrf_token }}` |
| webhook 集成 | ✅ 已修复 | daemon.py 推送后触发 webhook 回调 |
| 多余依赖 | ✅ 已清理 | pyOpenSSL、prometheus-client 已移除 |
| **db.py 集成** | ✅ 已完成 | `USE_SQLITE` 开关已添加，data.py 路由到 db.py |
| **`index()` 未定义变量** | ✅ **已修复** | `chart_certs`、`page_certs`、`page`、`per_page`、`total`、`total_pages` 未定义 |
| **daemon.py SQLite 适配** | ✅ **已修复** | daemon.py 仍用 JSON 读写，不走 SQLite |
| **db.py 迁移 bool 大小写** | 🟡 P1 未修复 | `str(v)` 应改为 `str(v).lower()` |
| **测试覆盖** | 🟢 P2 待改进 | daemon.py、dingtalk.py 无测试 |

---

## 🔴 P0 未修复（阻塞部署）

### 1. `app.py:index()` 未定义变量

**文件：** `app.py:304, 321`

```python
# Line 304 — chart_certs 未定义，应该用 certs
total_certs = len(chart_certs) if len(chart_certs) > 0 else 1

# Line 321 — page_certs/page/per_page/total/total_pages 均未定义
return render_template("index.html", certs=page_certs, ..., page=page, per_page=per_page, total=total, total_pages=total_pages)
```

**修复：**
- `chart_certs` → `certs`
- `page_certs` → `certs`
- 如果做了分页，补上分页逻辑；否则直接用 `certs` 并删除未定义的变量

### 2. `daemon.py` 未适配 SQLite

**现状：** `db.py` 已集成到 `data.py`，但 `daemon.py` 直接读写 JSON 文件，不走 `USE_SQLITE` 路由。

**影响：** 后台守护进程和 Web 进程数据源不一致，daemon 看到的和 web 看到的可能不同。

**修复：** `daemon.py` 中的 `load_data()`、`load_config()`、`load_state()` 等改用 `data.py` 的函数（它们已经有 `USE_SQLITE` 路由）。

---

## 🟡 P1 待修复

### 3. `db.py` 迁移逻辑 bool 大小写

**文件：** `db.py:189`

```python
v = str(v)  # True -> "True" (大写)
```

**`db_load_config()` 只匹配小写：**
```python
elif v.lower() in ("true", "false"):
```

**修复：** `db.py:189` 改为 `v = str(v).lower()`

---

## 🟢 P2 建议改进

### 4. 测试覆盖不足
- `daemon.py` 核心逻辑无测试
- `dingtalk.py` 签名算法无测试
- `test_db.py` 应验证 SQLite 实际能读写

### 5. 优雅关停
`daemon.py` SIGTERM 处理只设 `_running = False`，建议加 flush/save state

---

## 历史修复记录

### Phase 1（REVIEW_BLACK.md）— 已✅
| # | 问题 | 修复 |
|---|------|------|
| 1 | `_certs_cache` 未初始化 | ✅ |
| 2 | `DATA_DIR` 定义顺序 | ✅ |
| 3 | conftest.py 缓存重置 | ✅ |
| 4 | 术语"证书"→"到期项" | ✅ |
| 5 | docker-compose 服务名 | ✅ |
| 6 | db.py INSERT → INSERT OR REPLACE | ✅ |
| 7 | supervisord.conf 端口硬编码 | ✅ |
| 8 | Dockerfile HEALTHCHECK | ✅ |

### Phase 2（REVIEW_PHASE2.md）— 已✅
| # | 问题 | 修复 |
|---|------|------|
| 9 | db.py 集成（USE_SQLITE 开关） | ✅ |
| 10 | webhook 未集成 | ✅ |
| 11 | pyOpenSSL 多余依赖 | ✅ |
| 12 | .dockerignore 过度忽略 | ✅ |
| 13 | 剩余"证书"文字 | ✅ |
| 14 | supervisord 端口硬编码 | ✅ |
| 15 | Dockerfile ARG → ENV | ✅ |
| 16 | docker-compose 端口变量 | ✅ |

### Phase 3（REVIEW_PHASE3.md）— 部分✅
| # | 问题 | 修复 |
|---|------|------|
| 17 | csrf_token() 模板调用 | ✅ 已修复 |
| 18 | index() 未定义变量 | 🔴 **未修复** |
| 19 | daemon.py 未适配 SQLite | 🔴 **未修复** |

---


### Phase 4（本轮修复）— 已✅
|| # | 问题 | 修复 |
||---|------|------|
|| 20 | index() 未定义变量 chart_certs | ✅ 改为 certs |
|| 21 | index() 未定义变量 page_certs/page/per_page 等 | ✅ 改为 certs，移除未定义变量 |
|| 22 | daemon.py 未适配 SQLite | ✅ load_data() 改用 data.py 的 load_certs() |

## 下一步行动

1. **立即修复 P0**（2 个未定义变量 + daemon.py SQLite 适配）
2. **修复 P1**（db.py 迁移 bool 大小写）
3. **部署验证**：修复后我会重新在 124.222.198.26 上部署测试
4. **补充测试**（P2，不急）

---

## 协作方式

- 我是小白（架构师+PM+测试），你是小黑（开发）
- 所有 review 记录在 GitHub 仓库的 `REVIEW_BLACK.md`、`REVIEW_PHASE2.md`、`REVIEW_PHASE3.md`、`REVIEW_SUMMARY.md`（本文件）
- 你直接 pull 看，改完 push 就行，不用经过中转
- 我这边定期 pull 验证，有问题直接写 review 文档
