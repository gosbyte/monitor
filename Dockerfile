##############################################
# Stage 1: Builder — install dependencies
##############################################
FROM python:3.13-slim AS builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    fonts-dejavu-core \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies into the venv
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir supervisor -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

##############################################
# Stage 2: Runtime — minimal production image
##############################################
FROM python:3.13-slim AS runtime

LABEL maintainer="monitor-team" \
      description="Item Monitor — Flask web + background daemon"

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy application files
COPY app.py .
COPY routes/ ./routes/
COPY data.py .
COPY db.py .
COPY daemon.py .
COPY dingtalk.py .
COPY webhook.py .
COPY auth.py .
COPY cache.py .
COPY exceptions.py .
COPY init_data.py .
COPY supervisord.conf .
COPY utils/ ./utils/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory and set ownership
RUN mkdir -p /app/data /var/log/supervisor \
    && chown -R appuser:appgroup /app \
    && chmod -R 755 /app

# Environment variables
ENV TZ=Asia/Shanghai \
    PORT=5188 \
    DATA_DIR=/app/data \
    FLASK_ENV=production \
    USE_SQLITE=1

# Expose port
EXPOSE 5188

# Healthcheck (matches docker-compose.yml)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5188/health')" || exit 1

# Switch to non-root user
USER appuser

# Start supervisord (manages web + daemon)
ENTRYPOINT ["/opt/venv/bin/supervisord", "-c", "/app/supervisord.conf"]
