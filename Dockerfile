FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 安装 supervisor（进程管理）+ 中文字体（验证码用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    fonts-dejavu-core \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 复制应用代码
COPY . .

# 创建数据目录和日志目录
RUN mkdir -p /app/data /var/log/supervisor

# 首次启动时初始化空白数据（仅当 /app/data 为空时）
RUN python init_data.py

# 配置 supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 暴露端口（默认 5188，可通过环境变量覆盖）
ARG PORT=5188
ENV PORT=${PORT}
EXPOSE ${PORT}

# 设置环境变量
ENV DATA_DIR=/app/data \
    FLASK_ENV=production \
    TZ=Asia/Shanghai

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# 启动 supervisor（管理 web + daemon）
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
