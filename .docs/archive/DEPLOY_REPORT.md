# 部署报告 — 2026-06-26

## 部署结果

✅ **系统已成功部署到腾讯云 124.222.198.26**  
🔗 访问地址：`http://124.222.198.26:5188/login`

---

## 部署过程

### 1. 代码上传
- 通过 SCP 将代码上传到服务器 `/workspace/`
- 使用腾讯云镜像源加速 Docker 构建（apt 下载从 300s+ 降到 6s）

### 2. 构建修复
- 移除 `fonts-dejavu-core` 和 `fonts-wqy-microhei`（captcha 已有 fallback）
- 使用腾讯云 VPC 内网镜像源

### 3. Bug 修复
- **supervisord.conf 环境变量展开**：`PORT="%(_env_PORT)s"` → `PORT="5188"`
- **CSRF Token 模板错误**：`{{ csrf_token() }}` → `{{ csrf_token }}`（9 个模板 + auth.py）

### 4. 部署验证
- ✅ 容器正常运行
- ✅ supervisor 管理 web 和 daemon 进程
- ✅ `/login` 返回 200
- ✅ Flask 正常启动

---

## 已知问题

1. **`/` 根路径返回 404** — 需要添加根路径路由或重定向到 `/login`
2. **GitHub 推送失败** — SSH key 和 token 都不在当前机器可用
3. **`db.py` 仍未集成** — SQLite 层是空壳
4. **部分"证书"文字未替换** — 在 deploy.sh、README.md 等文件中

---

## 给小黑的建议

### 必须修复（P0）

1. **添加根路径路由**
   ```python
   @app.route("/")
   def root():
       return redirect(url_for("login_page"))
   ```

2. **集成 `db.py` 到 `app.py` 和 `daemon.py`**
   - 当前 `db.py` 完全未被使用
   - 建议在 `data.py` 中加 `USE_SQLITE` 开关，实现双写兼容

3. **修复 `db.py` 迁移逻辑**
   - 布尔值比较：`True` vs `true`（SQLite 存储为 `true`/`false`）

### 应该修复（P1）

4. **清理多余依赖**
   - `prometheus-client`：写了但没集成
   - `pyOpenSSL`：未使用

5. **supervisord.conf 端口硬编码**
   - 两个进程都硬编码 `PORT="5188"`，应使用环境变量

6. **Dockerfile 中 `COPY supervisord.conf` 路径**
   - 确保与 `docker-compose.yml` 中的 `COPY` 路径一致

### 建议改进（P2）

7. **添加 `/` 重定向**
8. **完善 README.md**
9. **添加健康检查端点 `/health` 的监控**

---

## 部署命令参考

```bash
# SSH 到服务器
ssh -i /opt/data/workspace/server_key.pem root@124.222.198.26

# 查看容器状态
docker ps

# 查看日志
docker logs item-monitor --tail 50

# 重启
cd /workspace && docker compose down && docker compose up -d

# 重新构建
cd /workspace && docker compose build --no-cache
```

---

*报告人：小白*
