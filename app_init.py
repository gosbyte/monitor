# -*- coding: utf-8 -*-
"""Flask 应用初始化 - 注册蓝图，全局配置，Prometheus metrics，健康检查"""
from __future__ import annotations

import json
import os
import sys
import signal
import time
import secrets
import logging
import logging.handlers
import threading
import uuid
import glob
import io
import shutil
from functools import wraps
from datetime import datetime, timedelta
from typing import Any

from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session, make_response, g

from exceptions import MonitorException

from data import (
    save_logs, write_log,
    load_config, save_config, load_certs, save_certs,
    load_users, save_users, verify_user, is_user_locked,
    get_lock_seconds, do_lock_user, reset_failed_attempts, load_logs,
    validate_password, calc_days_left, get_cert_status, calc_stats,
    DATA_DIR, BASE_DIR, DATA_FILE, CONFIG_FILE, USERS_FILE,
    LOGS_FILE, SECRET_KEY_FILE, USE_SQLITE,
    encrypt_field, decrypt_field,
    LOG_CLEANUP_MAX_SIZE_MB, LOG_CLEANUP_DIRS,
    reload_config,
    certs_cache, users_cache, config_cache,
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


# ── 通用请求速率限制 ──────────────────────────────────────
_REQUEST_COUNTS: dict[str, list[float]] = {}

# [FIX] P2-7: 限流数据持久化到文件（重启后保留部分状态）
_RATE_LIMIT_FILE = os.path.join(DATA_DIR, "rate_limit_state.json")


def _persist_rate_limit() -> None:
    """定期持久化限流数据"""
    try:
        tmp = _RATE_LIMIT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_REQUEST_COUNTS, f)
        os.replace(tmp, _RATE_LIMIT_FILE)
    except Exception:
        pass


def _load_rate_limit() -> None:
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
def _persist_loop() -> None:
    while True:
        time.sleep(30)
        _persist_rate_limit()


_persist_thread = threading.Thread(target=_persist_loop, daemon=True)
_persist_thread.start()


def _rate_limit(key: str, max_requests: int = 10, window: int = 60) -> bool:
    """简单速率限制：同一 key 在 window 秒内最多 max_requests 次"""
    now = time.time()
    if key not in _REQUEST_COUNTS:
        _REQUEST_COUNTS[key] = []
    _REQUEST_COUNTS[key] = [t for t in _REQUEST_COUNTS[key] if now - t < window]
    if len(_REQUEST_COUNTS[key]) >= max_requests:
        return False
    _REQUEST_COUNTS[key].append(now)
    return True


def rate_limit(max_requests: int = 5, window: int = 60) -> Any:
    """速率限制装饰器工厂"""
    def decorator(f: Any) -> Any:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            ip = request.remote_addr or "unknown"
            key = f"{f.__name__}:{ip}"
            if not _rate_limit(key, max_requests, window):
                return jsonify({"ok": False, "message": f"请求过于频繁，请 {window} 秒后再试"}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ── 日志自动清理 ──────────────────────────────────────────

def cleanup_logs(max_size_mb: int = LOG_CLEANUP_MAX_SIZE_MB) -> tuple[int, int]:
    """清理超过指定大小的 .log 文件（按大小和时间清理）

    清理策略：
    1. 查找 DATA_DIR 下所有 .log 文件
    2. 单个文件超过 max_size_mb 时，归档为 .log.YYYYMMDD_HHMMSS.gz
    3. 超过 7 天的 .log.gz 归档文件被删除
    4. 同时清理 db.py 中的 SQLite 日志（保留最近 1000 条）
    """
    cleaned_count = 0
    freed_bytes = 0

    for log_dir in LOG_CLEANUP_DIRS:
        if not os.path.isdir(log_dir):
            continue

        threshold_bytes = max_size_mb * 1024 * 1024

        # 清理 .log 文件
        for log_file in glob.glob(os.path.join(log_dir, "*.log")):
            try:
                file_size = os.path.getsize(log_file)
                if file_size > threshold_bytes:
                    # 归档旧日志
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    archive_path = log_file + "." + ts + ".gz"
                    with open(log_file, "rb") as f_in:
                        with gzip.open(archive_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    # 截断原文件
                    with open(log_file, "w") as f:
                        f.write("")
                    freed_bytes += file_size
                    cleaned_count += 1
                    logger.info(f"日志归档并清理: {log_file} ({file_size / 1024 / 1024:.1f}MB -> {archive_path})")
            except Exception as e:
                logger.warning(f"清理日志文件失败 {log_file}: {e}")

        # 删除超过 7 天的 .log.gz 归档
        for archive_file in glob.glob(os.path.join(log_dir, "*.log.*.gz")):
            try:
                mtime = os.path.getmtime(archive_file)
                if time.time() - mtime > 7 * 86400:
                    os.remove(archive_file)
                    cleaned_count += 1
                    logger.info(f"删除过期归档: {archive_file}")
            except Exception as e:
                logger.warning(f"删除归档文件失败 {archive_file}: {e}")

    # 清理 SQLite 日志（保留最近 1000 条）
    try:
        from db import get_db
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM logs WHERE rowid NOT IN (SELECT rowid FROM logs ORDER BY rowid DESC LIMIT 1000)"
            )
            if cursor.rowcount > 0:
                cleaned_count += 1
                logger.info(f"SQLite 日志清理: 删除 {cursor.rowcount} 条旧日志")
    except Exception as e:
        logger.warning(f"SQLite 日志清理失败: {e}")

    logger.info(f"日志清理完成: 清理 {cleaned_count} 项, 释放 ~{freed_bytes / 1024 / 1024:.1f}MB")
    return cleaned_count, freed_bytes


# 导入 gzip 用于日志清理
import gzip  # noqa: E402

# ── 定时日志清理任务（每天凌晨 3 点）────────────────────────
_last_cleanup_date: str | None = None

def _scheduled_cleanup_loop() -> None:
    """后台线程：每天凌晨 3 点自动清理日志"""
    global _last_cleanup_date
    while True:
        time.sleep(60)  # 每分钟检查一次
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 检查是否已经在今日清理过
        if _last_cleanup_date == today:
            continue

        # 检查当前时间是否是凌晨 3 点（±5 分钟窗口）
        if now.hour == 3 and now.minute < 5:
            try:
                cleaned, freed = cleanup_logs()
                logger.info(f"定时日志清理执行: 清理 {cleaned} 项, 释放 {freed / 1024 / 1024:.1f}MB")
                _last_cleanup_date = today
            except Exception as e:
                logger.error(f"定时日志清理失败: {e}")
                _last_cleanup_date = None  # 失败则次日重试


_cleanup_thread = threading.Thread(target=_scheduled_cleanup_loop, daemon=True)
_cleanup_thread.start()


# ── 创建 Flask 应用 ──────────────────────────────────────
app = Flask(__name__, template_folder="templates")

# ── 安全配置 ──────────────────────────────────────────────
def _load_or_create_secret_key() -> str:
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

# [SECURITY] SESSION_COOKIE_SAMESITE 改为 Strict
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# [SECURITY] SESSION_COOKIE_SECURE 根据 DEBUG 动态设置
app.config["SESSION_COOKIE_SECURE"] = not app.debug

# [FIX] P0-1: 使用 g 对象确保每请求独立 nonce
@app.before_request
def _before_request_setup() -> None:
    g.csp_nonce = secrets.token_hex(16)
    # [SECURITY] X-Request-ID 中间件
    g.request_id = str(uuid.uuid4())


@app.context_processor
def inject_csp_nonce() -> dict[str, str]:
    return dict(csp_nonce=getattr(g, 'csp_nonce', ''))


# [FIX] Inject CSRF token and badge count into all templates
@app.context_processor
def inject_template_globals() -> dict[str, Any]:
    result = inject_globals()
    # Derive active_page from request path for sidebar highlighting
    path = request.path.lstrip('/') if request.path else ''
    active_pages = {
        '': 'index',
        'index': 'index',
        'login': 'login',
        'logout': 'logout',
        'change_password': 'change_password',
        'users': 'users',
        'config': 'config',
        'logs': 'logs',
        'push_history': 'push_history',
        'data_manage': 'data_manage',
        'add_batch': 'add_batch',
        'restore': 'restore',
        'edit': 'index',
    }
    # Match prefix-based
    active_page = active_pages.get(path, 'index')
    # Handle paths like edit/<id>, delete/<id>, etc.
    if path.startswith('edit/') or path.startswith('delete/') or path.startswith('backup'):
        active_page = 'index'
    elif path.startswith('users/'):
        active_page = 'users'
    elif path.startswith('logs/') or path.startswith('push_history'):
        active_page = 'logs' if path.startswith('logs') else 'push_history'
    elif path.startswith('config'):
        active_page = 'config'
    elif path.startswith('data_manage'):
        active_page = 'data_manage'
    elif path.startswith('add_batch'):
        active_page = 'add_batch'
    elif path.startswith('restore'):
        active_page = 'restore'
    result['active_page'] = active_page
    return result


# [FIX] P0-2: 重新启用 CSP
@app.after_request
def set_security_headers(response: Response) -> Response:
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # [SECURITY] 添加 X-Request-ID 到响应头
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


# ── 请求审计日志 ──────────────────────────────────────────
_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)
_audit_handler = logging.handlers.RotatingFileHandler(
    os.path.join(DATA_DIR, "audit.log"), maxBytes=10_485_760, backupCount=5, encoding='utf-8'
)
_audit_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
_audit_logger.addHandler(_audit_handler)


@app.before_request
def _audit_log_request() -> None:
    """记录请求审计日志"""
    g.request_start_time = time.time()
    if request.path.startswith('/health') or request.path == '/metrics':
        return  # 跳过健康检查和指标

    _audit_logger.info(
        f"REQUEST|id={getattr(g, 'request_id', '?')}|"
        f"method={request.method}|"
        f"path={request.path}|"
        f"remote_addr={request.remote_addr or 'unknown'}|"
        f"user_agent={request.headers.get('User-Agent', '')[:200]}|"
        f"content_length={request.content_length or 0}"
    )


@app.after_request
def _audit_log_response(response: Response) -> Response:
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


# ── 全局错误处理器 ──────────────────────────────────────────

def _log_error(error_msg: str, exc_info=None) -> None:
    """记录错误到 flask.log 和 audit.log。"""
    request_id = getattr(g, 'request_id', '?')
    logger.error(f"[req={request_id}] {error_msg}", exc_info=exc_info)
    _audit_logger.info(
        f"ERROR|id={request_id}|{error_msg}"
    )


@app.errorhandler(MonitorException)
def handle_monitor_exception(e: MonitorException) -> Response:
    """处理 MonitorException 及其子类异常。"""
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]

    _log_error(f"{e.code} | {e.message}")

    if is_html:
        from flask import flash
        flash(f"{e.code}: {e.message}", "error")
        return redirect(url_for("index"))
    else:
        return jsonify({"success": False, "code": e.code, "message": e.message}), e.status_code


@app.errorhandler(Exception)
def handle_unexpected_exception(e: Exception) -> Response:
    """捕获所有未处理的异常。"""
    request_id = getattr(g, 'request_id', '?')
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]

    _log_error(f"UNEXPECTED EXCEPTION | {type(e).__name__}: {e}", exc_info=True)

    if is_html:
        from flask import flash
        if app.debug:
            flash(f"系统错误: {e}", "error")
        else:
            flash("系统发生未知错误，请联系管理员", "error")
        return redirect(url_for("index"))
    else:
        if app.debug:
            return jsonify({
                "success": False,
                "code": "ERR_SERVICE",
                "message": str(e),
            }), 500
        else:
            return jsonify({
                "success": False,
                "code": "ERR_SERVICE",
                "message": "系统内部错误",
            }), 500


@app.errorhandler(404)
def handle_404(e) -> Response:
    """自定义 404 页面。"""
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    if is_html:
        return render_template("error.html", code="404", title="页面未找到", message="您访问的页面不存在或已被移除"), 404
    return jsonify({"success": False, "code": "ERR_NOT_FOUND", "message": "页面不存在"}), 404


@app.errorhandler(500)
def handle_500(e) -> Response:
    """自定义 500 页面。"""
    is_html = request.accept_mimetypes.best == 'text/html' and \
              'application/json' not in [m for m, _ in request.accept_mimetypes]
    if is_html:
        return render_template("error.html", code="500", title="服务器内部错误", message="服务器遇到意外错误，请稍后重试"), 500
    return jsonify({"success": False, "code": "ERR_SERVICE", "message": "服务器内部错误"}), 500


# ── 注册蓝图 ──────────────────────────────────────────────
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


# ── Prometheus 监控指标 ──────────────────────────────────────
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry as Registry, Gauge  # noqa: E402

# [FIX] P1-8: 使用独立 Registry 避免多 worker 冲突
_custom_registry = Registry()
_gauge_total_certs = Gauge('cert_total', 'Total certificates', registry=_custom_registry)
_gauge_expiring_certs = Gauge('cert_expiring_soon', 'Certificates expiring within 7 days', registry=_custom_registry)
_gauge_expired_certs = Gauge('cert_expired', 'Expired certificates', registry=_custom_registry)
_gauge_disabled_certs = Gauge('cert_disabled', 'Disabled certificate reminders', registry=_custom_registry)

# [FIX] P1-6: /metrics 端点添加 IP 白名单
_METRICS_ALLOWED_IPS: list[str] = os.environ.get("METRICS_ALLOWED_IPS", "127.0.0.1,::1").split(",")


@app.route("/metrics")
def prometheus_metrics() -> Response:
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


# ── 缓存统计 ──────────────────────────────────────────────
@app.route("/api/cache-stats")
@admin_required
def cache_stats() -> Any:
    """管理员端点：返回所有缓存的统计信息"""
    return jsonify({
        "certs": certs_cache.stats(),
        "users": users_cache.stats(),
        "config": config_cache.stats(),
    })


# ── 健康检查 ──────────────────────────────────────────────
@app.route("/health")
def health() -> Response:
    """[FIX] P3-5: 返回详细健康状态"""
    health_status: dict[str, Any] = {"status": "healthy", "checks": {}}
    try:
        from db import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    try:
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


def _shutdown_signal_handler(signum: int, frame: Any) -> None:
    logger.info(f"收到信号 {signum}，正在关闭服务...")
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown_signal_handler)
signal.signal(signal.SIGINT, _shutdown_signal_handler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5188))
    app.run(host="0.0.0.0", port=port, debug=False)
