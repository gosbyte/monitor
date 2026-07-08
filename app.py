# -*- coding: utf-8 -*-
"""Flask Web 管理界面 - 带登录和验证码（安全加固版）"""
import json
import os
import io
import sys
import signal
import time
import random
import string
import re
import logging
import logging.handlers
import secrets
from functools import wraps
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session, make_response, g
from werkzeug.security import generate_password_hash, check_password_hash
from data import (
    atomic_write_json, save_logs, write_log,
    load_config, save_config, load_certs, save_certs,
    load_users, save_users, verify_user, is_user_locked,
    get_lock_seconds, do_lock_user, reset_failed_attempts, load_logs,
    validate_password, calc_days_left, get_cert_status, calc_stats,
    DATA_DIR, BASE_DIR, DATA_FILE, CONFIG_FILE, USERS_FILE,
    LOGS_FILE, SECRET_KEY_FILE, USE_SQLITE,
    FileLock, locked_read_json, locked_write_json, encrypt_field, decrypt_field,
)
from auth import (
    inject_globals, csrf_required, login_required, admin_required,
    generate_captcha, create_captcha_image,
)

from webhook import (
    send_webhook,
    build_item_expiry_payload,
    build_item_added_payload,
    build_item_deleted_payload,
)
from PIL import Image, ImageDraw, ImageFont


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.handlers.RotatingFileHandler(
        os.path.join(DATA_DIR, 'flask.log'), maxBytes=10_485_760, backupCount=5, encoding='utf-8'
    ), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── IP 级别登录限流 ──────────────────────────────────────
_LOGIN_ATTEMPTS = {}  # {ip: [(timestamp, success)]}
_LOGIN_MAX_ATTEMPTS = 10  # 10 次/分钟
_LOGIN_COOLDOWN = 300  # 5 分钟冷却

# ── 通用请求速率限制 ──────────────────────────────────────
_REQUEST_COUNTS = {}

# [FIX] P2-7: 限流数据持久化到文件（重启后保留部分状态）
_RATE_LIMIT_FILE = os.path.join(DATA_DIR, "rate_limit_state.json")

def _persist_rate_limit():
    """定期持久化限流数据"""
    try:
        tmp = _RATE_LIMIT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_REQUEST_COUNTS, f)
        os.replace(tmp, _RATE_LIMIT_FILE)
    except Exception:
        pass

def _load_rate_limit():
    """从文件加载限流数据"""
    global _REQUEST_COUNTS
    try:
        if os.path.exists(_RATE_LIMIT_FILE):
            with open(_RATE_LIMIT_FILE, "r") as f:
                saved = json.load(f)
            now = time.time()
            _REQUEST_COUNTS = {k: [t for t in v if now - t < 60] for k, v in saved.items()}
    except Exception:
        pass

# 启动时加载限流状态
_load_rate_limit()

# 定时持久化（每 30 秒）
import threading
def _persist_loop():
    while True:
        time.sleep(30)
        _persist_rate_limit()

_persist_thread = threading.Thread(target=_persist_loop, daemon=True)
_persist_thread.start()

def _rate_limit(key, max_requests=10, window=60):
    """简单速率限制：同一 key 在 window 秒内最多 max_requests 次"""
    now = time.time()
    if key not in _REQUEST_COUNTS:
        _REQUEST_COUNTS[key] = []
    _REQUEST_COUNTS[key] = [t for t in _REQUEST_COUNTS[key] if now - t < window]
    if len(_REQUEST_COUNTS[key]) >= max_requests:
        return False
    _REQUEST_COUNTS[key].append(now)
    return True

def rate_limit(max_requests=5, window=60):
    """速率限制装饰器工厂"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            key = f"{f.__name__}:{ip}"
            if not _rate_limit(key, max_requests, window):
                return jsonify({"ok": False, "message": f"请求过于频繁，请 {window} 秒后再试"}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__, template_folder="templates")

# ── 安全配置 ──────────────────────────────────────────────
def _load_or_create_secret_key():
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "r") as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(key)
    return key

app.secret_key = _load_or_create_secret_key()

# [FIX] P1-5: 文件上传大小限制 10MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# [FIX] P0-1: 使用 g 对象确保每请求独立 nonce
@app.before_request
def _before_request_setup():
    g.csp_nonce = secrets.token_hex(16)

@app.context_processor
def inject_csp_nonce():
    return dict(csp_nonce=getattr(g, 'csp_nonce', ''))

# [FIX] Inject CSRF token and badge count into all templates
@app.context_processor
def inject_template_globals():
    return inject_globals()

# [FIX] P0-2: 重新启用 CSP
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP - 仅对 HTML 响应设置，使用 unsafe-inline 避免 nonce 同步问题
    if response.content_type and 'text/html' in response.content_type:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://o404879.oss-cn-shanghai.oss.aliyuncs.com;"
        )
    return response


# ── Prometheus 监控指标 ──────────────────────────────────────
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry as Registry, Gauge

_custom_registry = Registry()
_gauge_total_certs = Gauge('cert_total', 'Total certificates', registry=_custom_registry)
_gauge_expiring_certs = Gauge('cert_expiring_soon', 'Certificates expiring within 7 days', registry=_custom_registry)
_gauge_expired_certs = Gauge('cert_expired', 'Expired certificates', registry=_custom_registry)
_gauge_disabled_certs = Gauge('cert_disabled', 'Disabled certificate reminders', registry=_custom_registry)

_METRICS_ALLOWED_IPS = os.environ.get("METRICS_ALLOWED_IPS", "127.0.0.1,::1").split(",")


@app.route("/metrics")
def prometheus_metrics():
    client_ip = request.remote_addr or "unknown"
    if client_ip not in _METRICS_ALLOWED_IPS:
        return jsonify({"ok": False, "message": "Forbidden"}), 403
    certs = load_certs()
    expired = expiring = disabled = 0
    for c in certs:
        d = calc_days_left(c.get("expire_date", ""))
        if d < 0:
            expired += 1
        elif d <= 7:
            expiring += 1
        if not c.get("remind_enabled", True):
            disabled += 1
    _gauge_total_certs.set(len(certs))
    _gauge_expiring_certs.set(expiring)
    _gauge_expired_certs.set(expired)
    _gauge_disabled_certs.set(disabled)
    return generate_latest(_custom_registry), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# ── 健康检查 ──────────────────────────────────────────────
@app.route("/health")
def health():
    """[FIX] P3-5: 返回详细健康状态"""
    health_status = {"status": "healthy", "checks": {}}
    try:
        if USE_SQLITE:
            from db import get_db
            with get_db() as conn:
                conn.execute("SELECT 1")
            health_status["checks"]["database"] = "ok"
        else:
            health_status["checks"]["database"] = "ok" if os.path.exists(DATA_FILE) else "warning"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    try:
        import shutil
        total, used, free = shutil.disk_usage(DATA_DIR)
        free_pct = free / total * 100
        disk_status = "ok" if free_pct > 10 else ("warning" if free_pct > 5 else "critical")
        health_status["checks"]["disk_space"] = {"status": disk_status, "free_percent": round(free_pct, 1), "free_gb": round(free / 1024**3, 2)}
        if disk_status == "critical":
            health_status["status"] = "unhealthy"
        elif disk_status == "warning" and health_status["status"] != "unhealthy":
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["disk_space"] = f"error: {str(e)}"
    try:
        daemon_log = os.path.join(DATA_DIR, "daemon.log")
        daemon_running = False
        if os.path.exists(daemon_log) and time.time() - os.path.getmtime(daemon_log) < 300:
            daemon_running = True
        health_status["checks"]["daemon"] = "running" if daemon_running else "stopped"
        if not daemon_running:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["daemon"] = f"error: {str(e)}"
    return jsonify(health_status)

def _shutdown_signal_handler(signum, frame):
    logger.info(f"收到信号 {signum}，正在关闭服务...")
    sys.exit(0)

signal.signal(signal.SIGTERM, _shutdown_signal_handler)
signal.signal(signal.SIGINT, _shutdown_signal_handler)


# ── Register routes from modular blueprint functions ──────────────
from routes.auth import register_auth_routes
from routes.certs import register_cert_routes
from routes.admin import register_admin_routes
from routes.api import register_api_routes
from routes.pages import register_page_routes

register_auth_routes(app)
register_cert_routes(app)
register_admin_routes(app)
register_api_routes(app)
register_page_routes(app)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5188))
    app.run(host="0.0.0.0", port=port, debug=False)
