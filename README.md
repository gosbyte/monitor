# 通用到期提醒系统

支持 Docker 部署，一键运行在 Linux 服务器上。

## 功能特性

- 🌐 **Web 管理界面**：添加/编辑/删除证书，支持批量导入
- 🔔 **钉钉推送**：到期前自动推送提醒，支持 Markdown 卡片
- ⏰ **精确到分钟**：后台常驻监控，到期立即推送（不等到第二天）
- 👥 **多用户管理**：支持添加管理员账号
- 📊 **数据持久化**：所有数据存储在 `data/` 目录
- 🔒 **安全加固**：密码哈希存储、Fernet 加密 SMTP 密码、文件锁防并发损坏

## 快速部署（Linux 服务器）

```bash
# 1. 上传整个 item-monitor 目录到服务器

# 2. 一键部署
chmod +x deploy.sh
./deploy.sh
```

## 手动部署

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务（可自定义端口）
CERT_MONITOR_PORT=8080 docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

## 配置

### 1. 配置钉钉机器人

1. 打开钉钉群 → 群设置 → 智能群助手 → 添加机器人
2. 选择「自定义」机器人
3. 安全设置选择「加签」，复制生成的 secret
4. 机器人名称随意，如「SSL监控」
5. 将 Webhook URL 和 Secret 填入 `data/config.json`

**config.json 示例：**
```json
{
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "secret": "SECxxx",
  "remind_days": [30, 14, 7, 3, 1]
}
```

### 2. 修改默认密码

首次部署后请立即修改密码：

```bash
# 编辑用户文件
vim data/users.json
```

## 访问

- **Web 管理界面**：`http://服务器IP:5188`
- **默认账号**：`admin` / 首次登录后请修改

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CERT_MONITOR_PORT` | 宿主机映射端口 | `5188` |
| `PORT` | 容器内部端口 | `5188` |
| `DATA_DIR` | 数据目录 | `/app/data` |
| `TZ` | 时区 | `Asia/Shanghai` |

## 常用命令

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看容器状态
docker-compose ps

# 进入容器
docker exec -it item-monitor bash
```

## 提醒时机

| 类型 | 说明 |
|------|------|
| 提前 N 天 | 30/14/7/3/1 天（按配置） |
| 到期当天 | 到期前 1 小时提醒 |
| 精确分钟 | 到期前 30/10/5/1 分钟提醒 |
| 已过期 | 每天提醒一次 |

## 数据目录

```
data/
├── certs.json          # 到期数据
├── config.json         # 配置文件
├── users.json          # 用户数据
├── logs.json           # 操作日志
├── remind_state.json   # 推送状态（自动生成）
├── .secret_key         # Flask 密钥（自动生成）
└── .fernet_key         # 加密密钥（自动生成）
```

## 升级

```bash
git pull  # 或上传新代码
docker-compose build --no-cache
docker-compose up -d
```

## 端口修改

如需修改默认端口，编辑 `docker-compose.yml`：

```yaml
ports:
  - "8080:5188"  # 改为你想要的端口
```

或在部署时使用环境变量：

```bash
CERT_MONITOR_PORT=8080 docker-compose up -d
```
