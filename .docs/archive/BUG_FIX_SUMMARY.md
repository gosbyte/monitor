# 到期提醒管理系统 - Bug 修复汇总

> 本文档记录了 `item-monitor`（新系统）开发过程中发现的所有 Bug 及其修复方案，供开发（小黑）参考。

---

## P0 - 阻断性 Bug

### 1. 登录接口 500 错误 — 缺少 `import time`

**现象**: 访问 `/login` 返回 500，后端报错 `NameError: name 'time' is not defined`

**原因**: `login()` 函数中使用了 `time.time()`，但文件顶部没有导入 `time` 模块。

**修复**: 在 `app.py` 顶部添加 `import time`

**文件**: `app.py`

---

### 2. 根路径 404 — `index()` 函数缺少路由装饰器

**现象**: 访问首页返回 404

**原因**: `index()` 函数忘记加 `@app.route("/")` 装饰器。

**修复**: 在 `index()` 函数上方添加 `@app.route("/")`

**文件**: `app.py`

---

### 3. 验证码接口 500 错误 — 返回值类型错误

**现象**: 访问 `/captcha` 返回 500，后端报错 `TypeError: the JSON object must be str, bytes or bytearray, not BytesIO`

**原因**: `create_captcha_image()` 函数返回了 `BytesIO` 对象而不是 `PIL.Image` 对象。

**修复**: 将 `return captcha_io` 改为 `return image`（PIL Image 对象）

**文件**: `auth.py`

---

### 4. 前端白屏 — CSP 策略拦截静态资源

**现象**: 页面加载后空白，控制台显示 `Refused to load the script ... because it violates the following Content Security Policy`

**原因**: `set_security_headers()` 设置了严格的 CSP（`script-src 'nonce-{...}'`），但 `tailwind.js` 和 `lucide.min.js` 没有 nonce，被浏览器拒绝加载。

**修复**: 在 CSP 的 `script-src` 和 `style-src` 中添加 `'unsafe-inline'`

**文件**: `app.py` → `set_security_headers()` 函数

---

### 5. 登录后始终提示"用户名或密码错误"

**现象**: 即使输入正确的 admin/admin123 也无法登录

**原因**: `init_db()` 只创建数据库表，没有插入默认管理员用户。`init_data.py` 只处理 JSON 文件，不处理 SQLite。

**修复**: 在 `db.py` 的 `init_db()` 中增加逻辑：如果 `users` 表为空，则自动插入默认管理员账户 `admin/admin123`

**文件**: `db.py` → `init_db()` 函数

---

## P1 - 功能性 Bug

### 6. CSRF Token 显示为函数名而非值

**现象**: 页面源码中 `<input name="csrf_token" value="csrf_token">`，token 值为字符串 `"csrf_token"` 而非实际哈希值

**原因**: `inject_globals()` 返回 `{"csrf_token": csrf_token}` 是函数引用，模板中 `{{ csrf_token }}` 显示为函数名的字符串表示。

**修复**: 模板中改为 `{{ csrf_token() }}`（调用函数获取实际值）

**文件**: `templates/*.html` 所有模板

---

### 7. `after_request` 回调返回 None 导致 500

**现象**: 修复 CSP 后全站返回 500

**原因**: `set_security_headers()` 函数中注释掉的部分导致 `return response` 未执行，函数隐式返回 `None`。Flask 的 `after_request` 回调必须返回 Response 对象。

**修复**: 确保 `set_security_headers()` 始终 `return response`

**文件**: `app.py` → `set_security_headers()` 函数

---

## P2 - 部署配置 Bug

### 8. Dockerfile 重复 HEALTHCHECK 指令

**现象**: `docker build` 报错 `Dockerfile parse error`

**原因**: 重构时 HEALTHCHECK 指令出现了两次。

**修复**: 删除重复的 HEALTHCHECK 行

**文件**: `Dockerfile`

---

### 9. supervisord.conf 不支持 `%(_env_PORT)s` 语法

**现象**: 容器启动后立即重启，日志显示 `ERROR (%(ENV_PORT)s not found)`

**原因**: supervisord 不支持 `%(_env_...)` 这种嵌套变量语法。

**修复**: 改用 `%(ENV_PORT)s`（注意是大写 ENV）

**文件**: `supervisord.conf`

---

### 10. 静态资源缺失 — tailwind.js 和 lucide.min.js

**现象**: 页面样式错乱，图标不显示

**原因**: 重构时 static 目录被清理，但模板仍引用这些 JS 文件。

**修复**: 从旧版 `cert-monitor` 容器中复制 `static/tailwind.js` 和 `static/lucide.min.js` 到新项目的 `static/` 目录

**文件**: `static/tailwind.js`, `static/lucide.min.js`

---

## 部署验证清单

每次部署后请逐项检查：

- [ ] `/health` 返回 `{"status": "ok"}`
- [ ] `/login` 返回 200 且页面正常渲染
- [ ] `/captcha` 返回 200 且图片可显示
- [ ] 使用 admin/admin123 可成功登录
- [ ] 登录后各模块入口按钮可点击跳转
- [ ] 页面无控制台 CSP 错误
- [ ] 表单提交时 CSRF Token 正确传递

---

*文档生成日期: 2026-06-27*
*维护者: 小白 (架构审查)*
