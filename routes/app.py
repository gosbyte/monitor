# -*- coding: utf-8 -*-
"""Flask Web 管理界面 - 带登录和验证码（安全加固版）"""
import os
import io
import sys
import signal
import time
import re
import logging
import logging.handlers
import secrets
import uuid
from functools import wraps
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session, g
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
    certs_cache, users_cache, config_cache,
)
from auth import (
    inject_globals, csrf_required, login_required, admin_required,
    generate_captcha, create_captcha_image, rate_limit,
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
    response.headers["X-Request-ID"] = getattr(g, 'request_id', '')
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


# ── Audit Log Middleware ──────────────────────────────────────
_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)
_audit_handler = logging.handlers.RotatingFileHandler(
    os.path.join(DATA_DIR, "audit.log"), maxBytes=10_485_760, backupCount=5, encoding='utf-8'
)
_audit_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
_audit_logger.addHandler(_audit_handler)


@app.before_request
def _audit_log_request():
    """记录请求审计日志"""
    g.request_start_time = time.time()
    if request.path.startswith('/health') or request.path == '/metrics':
        return
    _audit_logger.info(
        f"REQUEST|id={getattr(g, 'request_id', '?')}|"
        f"method={request.method}|"
        f"path={request.path}|"
        f"remote_addr={request.remote_addr or 'unknown'}|"
        f"user_agent={request.headers.get('User-Agent', '')[:200]}|"
        f"content_length={request.content_length or 0}"
    )


@app.after_request
def _audit_log_response(response):
    """记录响应审计日志"""
    if request.path.startswith('/health') or request.path == '/metrics':
        return response
    duration_ms = int((time.time() - getattr(g, 'request_start_time', time.time())) * 1000)
    _audit_logger.info(
        f"RESPONSE|id={getattr(g, 'request_id', '?')}|"
        f"status={response.status_code}|"
        f"duration={duration_ms}ms|"
        f"path={request.path}|"
        f"user={session.get('username', 'anonymous')}"
    )
    return response


# ── Global Error Handlers ──────────────────────────────────────
from exceptions import MonitorException


@app.errorhandler(MonitorException)
def handle_monitor_exception(e):
    request_id = getattr(g, 'request_id', '?')
    logger.error(f"[req={request_id}] {e.code} | {e.message}")
    _audit_logger.info(f"ERROR|id={request_id}|{e.code} | {e.message}")
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    if is_html:
        from flask import flash
        flash(f"{e.code}: {e.message}", "error")
        return redirect(url_for("index"))
    return jsonify({"success": False, "code": e.code, "message": e.message}), e.status_code


@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    request_id = getattr(g, 'request_id', '?')
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    logger.error(f"[req={request_id}] UNEXPECTED EXCEPTION | {type(e).__name__}: {e}", exc_info=True)
    _audit_logger.info(f"ERROR|id={request_id}|UNEXPECTED EXCEPTION | {type(e).__name__}: {e}")
    if is_html:
        from flask import flash
        if app.debug:
            flash(f"系统错误: {e}", "error")
        else:
            flash("系统发生未知错误，请联系管理员", "error")
        return redirect(url_for("index"))
    if app.debug:
        return jsonify({"success": False, "code": "ERR_SERVICE", "message": str(e)}), 500
    return jsonify({"success": False, "code": "ERR_SERVICE", "message": "系统内部错误"}), 500


@app.errorhandler(404)
def handle_404(e):
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    if is_html:
        return render_template("error.html", code="404", title="页面未找到", message="您访问的页面不存在或已被移除"), 404
    return jsonify({"success": False, "code": "ERR_NOT_FOUND", "message": "页面不存在"}), 404


@app.errorhandler(500)
def handle_500(e):
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    if is_html:
        return render_template("error.html", code="500", title="服务器内部错误", message="服务器遇到意外错误，请稍后重试"), 500
    return jsonify({"success": False, "code": "ERR_SERVICE", "message": "服务器内部错误"}), 500


# ── Cache Stats Endpoint ──────────────────────────────────────
@app.route("/api/cache-stats")
@admin_required
def cache_stats():
    """管理员端点：返回所有缓存的统计信息"""
    return jsonify({
        "certs": certs_cache.stats(),
        "users": users_cache.stats(),
        "config": config_cache.stats(),
    })


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
