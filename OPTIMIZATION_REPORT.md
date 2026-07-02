# item-monitor 全面优化报告

## 审查范围
- 服务器实际运行代码 (124.222.198.26)
- 对比本地仓库代码
- 覆盖 app.py, index.html, edit.html, add.html, config.html, users.html, logs.html, data_manage.html, dark.css, dark.js

## 发现的问题

### P0 - 关键问题
1. **domain 字段丢失** - 编辑弹窗（AJAX 方式）缺少 domain 输入框，编辑后 domain 被清空
2. **CSRF token 刷新缺失** - 配置保存后 redirect 回首页，但页面仍用旧 CSRF token
3. **inject_globals 注册方式** - 服务器用 `app.context_processor(inject_globals)` 非装饰器写法

### P1 - 体验问题
4. **Toast 通知简陋** - 只有 Unicode 符号，无 Lucide 图标，无动画，无进度条
5. **键盘快捷键全部移除** - Ctrl+K(搜索)/Ctrl+N(新建)/Ctrl+Enter(提交)/ESC(关闭) 都没了
6. **确认弹窗不支持 ESC 关闭**
7. **批量操作按钮过多** - 工具栏横向拥挤，移动端几乎不可用
8. **表格行操作按钮过多** - 每行 6 个按钮，移动端溢出
9. **统计卡片点击无视觉反馈** - 点击后不知道当前处于哪个筛选模式
10. **使用说明默认折叠且无记忆**

### P2 - 代码质量
11. **write_log 缺少 target 参数** - 添加/编辑/删除日志记录不准确
12. **closeModal 没有清理 modal-open class**
13. **本地仓库缺少 dark.js** - 版本不一致

## 优化方案

### 1. 编辑弹窗补 domain 字段
- 在 add-modal 和 edit-modal 中都加上 domain 输入框
- AJAX 提交时包含 domain 字段

### 2. Toast 通知增强
- 使用 Lucide 图标替代 Unicode
- 添加 slideIn 动画
- 添加进度条效果

### 3. 恢复键盘快捷键
- Ctrl+K: 聚焦搜索框
- Ctrl+N: 打开添加弹窗
- Ctrl+Enter: 提交表单
- ESC: 关闭弹窗/菜单

### 4. 批量操作优化
- 改为下拉菜单形式，节省空间
- 移动端只显示主要操作按钮

### 5. 表格行操作优化
- 改为下拉菜单，避免按钮过多
- 常用操作（编辑/删除）直接显示，其他放菜单

### 6. 统计卡片筛选反馈
- 点击后高亮当前筛选状态
- 显示筛选标签

### 7. 确认弹窗支持 ESC
- 添加 ESC 键关闭

### 8. 使用说明默认展开
- 首次访问自动展开
- 记住用户选择

### 9. write_log 补全
- 添加 target 参数
