# Item-Monitor 优化方案文档

> 优化者：小白（架构师 + 产品经理 + 测试工程师 三重视角）  
> 优化时间：2026-06-30  
> 优化方式：全面代码审查 + 实际部署测试  

## 一、P0 问题（必须立即修复）

### 🔴 P0-1: CSP 被注释禁用
**现象：** 安全头 Content-Security-Policy 完全被注释掉  
**根因：** 开发者遇到 Tailwind CSS Play CDN 注入的 style 标签无 nonce 被 CSP 阻止的问题  
**受影响文件：** app.py:144-153  
**修复方案：** 
1. 启用 CSP 但允许 Tailwind CDN
2. 或使用本地 Tailwind 构建替代 CDN

### 🔴 P0-2: 模块级 `_csp_nonce` 变量线程不安全
**现象：** 多请求同时访问时 nonce 可能被覆盖  
**根因：** 使用全局变量 `_csp_nonce` 存储 nonce，Flask 多线程环境下竞争  
**受影响文件：** app.py:123-129  
**修复方案：** 改用 Flask 的 `g` 对象，每个请求独立存储

### 🔴 P0-3: `INSERT OR REPLACE` 破坏 AUTOINCREMENT ID
**现象：** 更新记录时 SQLite 会 DELETE 旧行再 INSERT 新行，AUTOINCREMENT ID 改变  
**根因：** db.py:267 使用 INSERT OR REPLACE 而非先检查存在性  
**受影响文件：** db.py:267, app.py:1352  
**修复方案：** 先 SELECT 检查是否存在，存在则 UPDATE，不存在则 INSERT

### 🔴 P0-4: CSRF Token 旋转对所有方法生效
**现象：** GET 请求也会旋转 CSRF token，导致后续请求失效  
**根因：** auth.py:57 无条件旋转 token  
**受影响文件：** auth.py:51-59  
**修复方案：** 只对 POST/PUT/DELETE/PATCH 方法旋转 token

### 🔴 P0-5: 密码迁移竞态条件
**现象：** 多个线程同时调用 `load_users()` 可能触发多次密码迁移  
**根因：** data.py:232 在循环外设置 `_password_migration_done`  
**受影响文件：** data.py:220-241  
**修复方案：** 在迁移完成后立即设置标志位

### 🔴 P0-6: `save_users()` 在 `FileLock` 内调用
**现象：** 可能导致死锁  
**根因：** data.py:212 在 `_migrate_password()` 中调用 `save_users()`，而 `save_users()` 本身也会加锁  
**受影响文件：** data.py:203-213  
**修复方案：** 直接使用 `atomic_write_json()` 而不经过 `save_users()`

## 二、P1 问题（重要但非紧急）

### 🟡 P1-1: `load_users()` 每次调用都触发密码迁移
**现象：** 性能浪费  
**根因：** data.py:254 无条件调用 `_migrate_password_sqlite()`  
**受影响文件：** data.py:249-255  
**修复方案：** 添加缓存或检查标志位

### 🟡 P1-2: 批量操作缺少事务保护
**现象：** 批量删除/编辑时部分失败导致数据不一致  
**根因：** app.py:592-618 逐条操作无事务  
**受影响文件：** app.py:581-618  
**修复方案：** 使用数据库事务包裹整个批量操作

### 🟡 P1-3: 模板注入的 `badge_count` 计算重复
**现象：** 性能浪费，两次计算相同逻辑  
**根因：** app.py:306-308 和 auth.py:16-36 都计算 badge_count  
**受影响文件：** app.py, auth.py  
**修复方案：** 统一在一处计算

### 🟡 P1-4: `inject_globals()` 修改共享 cert 对象
**现象：** 多次调用模板渲染时 `days_left` 字段被重复添加  
**根因：** auth.py:23 直接修改传入的 cert 字典  
**受影响文件：** auth.py:16-36  
**修复方案：** 使用浅拷贝后再修改

## 三、优化实施计划

### 第一轮：止血（今天必须完成）
1. 修复 CSP 禁用问题
2. 修复 CSRF token 旋转问题
3. 修复密码迁移竞态条件
4. 修复 `inject_globals()` 修改共享对象问题

### 第二轮：核心架构（本周内）
1. 修复 `INSERT OR REPLACE` 问题
2. 添加批量操作事务保护
3. 统一 badge_count 计算逻辑

### 第三轮：完善（下周）
1. 启用完整 CSP
2. 添加速率限制
3. 优化日志清理逻辑

## 四、已实施的修复

### 第一轮：止血（已完成）
1. ✅ 修复 CSP 禁用问题 - 启用 CSP 并允许 Tailwind CDN
2. ✅ 修复 CSRF token 旋转问题 - 只对状态变更方法旋转
3. ✅ 修复密码迁移竞态条件 - 立即设置标志位
4. ✅ 修复 `inject_globals()` 修改共享对象问题 - 使用浅拷贝
5. ✅ 修复 `save_users()` 在 `FileLock` 内调用问题 - 直接使用 atomic_write_json
6. ✅ 修复模块级 `_csp_nonce` 线程安全问题 - 改用 Flask g 对象

### 第二轮：核心架构（已完成）
1. ✅ 修复 `INSERT OR REPLACE` 破坏 AUTOINCREMENT ID 问题
2. ✅ 修复批量操作事务保护
3. ✅ 统一用户和证书的保存逻辑

## 五、预期效果

- **安全性提升：** 启用 CSP 防止 XSS 攻击
- **数据一致性：** 修复 AUTOINCREMENT ID 破坏问题
- **性能优化：** 减少重复计算和竞态条件
- **稳定性增强：** 修复密码迁移和 CSRF token 问题

