# -*- coding: utf-8 -*-
"""Flask Web 管理界面入口 - Blueprint 模块化架构

拆分说明:
  routes/auth.py      - 认证相关路由（login/logout/change_password/users管理）
  routes/certs.py     - 到期项 CRUD（增删改查/导入导出/备份恢复）
  routes/admin.py     - 管理员功能（配置/批量操作/日志/推送历史）
  routes/api.py       - API 端点（状态切换/测试推送/Webhook）
  routes/pages.py     - 页面路由（add_batch）
  app_init.py         - Flask 应用初始化，注册蓝图，全局配置
"""
import os
from app_init import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5188))
    app.run(host="0.0.0.0", port=port, debug=False)
