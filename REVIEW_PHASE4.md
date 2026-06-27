# Phase 4 部署验证报告

> **日期：** 2026-06-27
> **仓库：** https://github.com/gosbyte/monitor
> **当前 HEAD：** `main` → `731153b`
> **审查人：** 小白（架构师 + PM + 测试）

---

## 一、代码审查结果

### ✅ 已正确修复

| # | 文件 | 问题 | 修复内容 |
|---|------|------|----------|
| 1 | `app.py:304` | `chart_certs` 未定义 | 改为 `certs` |
| 2 | `app.py:321` | `page_certs`、`page`、`per_page`、`total`、`total_pages` 未定义 | 移除未定义变量，`certs=page_certs` → `certs=certs` |
| 3 | `daemon.py:88` | `load_data()` 不走 SQLite | 优先 `from data import load_certs`，异常回退 JSON |
| 4 | `daemon.py:97` | `load_config()` 不走 SQLite | 优先 `from data import load_config_decrypted`，异常回退 JSON |

### 🔴 P0 — 阻塞 Bug

| # | 文件 | 位置 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 1 | `app.py` | 第 159 行 | **`captcha()` 函数缺少 `@app.route("/captcha")` 装饰器** | 在 `def captcha():` 上方添加 `@app.route("/captcha")` |

**影响：** 登录页 `<img src="/captcha">` 请求返回 404，验证码图片无法加载，用户无法登录。

### ⚠️ P1 — 配置问题

| # | 文件 | 位置 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 1 | `docker-compose.yml` | healthcheck 段 | healthcheck 指向 `/`（返回 404），应指向 `/health` | 将 `http://localhost:5188/` 改为 `http://localhost:5188/health` |

**影响：** 容器 health check 一直失败，Docker 判定 unhealthy。

### 💡 P2 — 优化建议

| # | 文件 | 位置 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 1 | `app.py` | 路由定义 | 根路径 `/` 无路由，访问返回 404 | 添加 `@app.route("/")` 重定向到 `/login` 或 `/health` |

---

## 二、部署验证结果

| 测试项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| 容器状态 | Running, healthy | Running, healthy | ✅ |
| 端口映射 | 5188→5188 | 0.0.0.0:5188→5188/tcp | ✅ |
| 登录页 `/login` | 200 | 200 | ✅ |
| 健康检查 `/health` | 200 | 200 | ✅ |
| **验证码 `/captcha`** | 200, image/png | **404** | 🔴 **FAIL** |
| supervisord 日志 | 无报错 | 无报错 | ✅ |
| daemon 日志 | 正常运行 | 正常运行 | ✅ |
| web 日志 | Flask 正常启动 | Flask 正常启动 | ✅ |

---

## 三、修复优先级

| 优先级 | 数量 | 说明 |
|--------|------|------|
| **P0** | 1 | 验证码 404，用户无法登录 — **必须立即修复** |
| P1 | 1 | healthcheck 路径错误 — 建议修复，不影响功能 |
| P2 | 1 | 根路径 404 — 体验优化，可延后 |

---

## 四、修复指引

### 1. `app.py` — 添加 captcha 路由（P0）

找到第 159 行的 `def captcha():`，在它上面加一行：

```python
@app.route("/captcha")
def captcha():
    """获取验证码图片"""
    ...
```

### 2. `docker-compose.yml` — 修复 healthcheck 路径（P1）

把这一行：
```yaml
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5188/')"]
```
改为：
```yaml
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5188/health')"]
```

### 3. `app.py` — 添加根路径重定向（P2，可选）

在路由定义区域添加：
```python
@app.route("/")
def root_redirect():
    return redirect(url_for("login_page"))
```

---

## 五、注意事项

1. 修复后需要重新构建 Docker 镜像并重启容器：
   ```bash
   cd /root/item-monitor
   docker build -t item-monitor:latest .
   docker compose up -d
   ```
2. 如果改了 `docker-compose.yml` 的 healthcheck，也需要重新 build（因为 compose 会重建容器）。
3. 修复完成后记得更新 `REVIEW_SUMMARY.md` 的 Phase 4 状态。
