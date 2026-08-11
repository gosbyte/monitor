# -*- coding: utf-8 -*-
"""
认证层 - CSRF、验证码、登录/权限装饰器（依赖 Flask）
注意：login_required 使用 url_for("index")，需在 app.py 注册路由后使用
"""
from __future__ import annotations

import json
import os
import random
import secrets
import string
import threading
import time
from functools import wraps
from typing import Any

from flask import session, redirect, url_for, request, Response, jsonify

from data import (
    load_certs, calc_days_left, load_users, save_users,
    verify_user, is_user_locked, get_lock_seconds,
    do_lock_user, reset_failed_attempts, DATA_DIR,
)


# ── 上下文处理器 ─────────────────────────────────────────
def inject_globals() -> dict[str, Any]:
    """向所有模板注入 csrf_token, badge_count 和 csp_nonce"""
    badge_count = 0
    if session.get("username"):
        try:
            # [PERF] Use SQL COUNT instead of Python iteration over all certs
            from db import db_calc_stats
            stats = db_calc_stats()
            badge_count = stats.get("expiring", 0)
        except Exception:
            badge_count = 0
    return dict(
        csrf_token=_generate_csrf_token(),
        badge_count=badge_count,
        # [FIX] P1-9: 移除 csp_nonce，由 app.py 的 inject_csp_nonce 单独注入
    )


# ── CSRF ─────────────────────────────────────────────────
def _generate_csrf_token() -> str:
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def _check_csrf() -> bool:
    if request.is_json:
        token: str | None = request.json.get("_csrf_token")  # type: ignore[union-attr]
    else:
        token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
    return bool(token and token == session.get("_csrf_token"))




def _check_api_csrf() -> bool:
    """API CSRF 检查（供 API 路由内部使用，不旋转 token）"""
    # 测试模式下跳过 CSRF 验证
    from flask import current_app
    if current_app.testing:
        return True
    if request.method == "GET":
        return True
    token = request.headers.get("X-CSRF-Token")
    if not token and request.is_json:
        token = request.json.get("_csrf_token")  # type: ignore[union-attr]
    if not token or token != session.get("_csrf_token"):
        return False
    return True

def csrf_required(f: Any) -> Any:
    """CSRF 验证装饰器，所有 POST 路由使用"""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if not _check_csrf():
            return "CSRF 验证失败，请重新提交", 403
        # [FIX] P0-4: 只对状态变更方法旋转 CSRF token
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            session["_csrf_token"] = secrets.token_hex(32)
        return f(*args, **kwargs)
    return decorated


# ── 登录/权限装饰器 ─────────────────────────────────────
def login_required(f: Any) -> Any:
    """登录装饰器，含 8 小时会话超时检查"""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if "logged_in" not in session:
            return redirect(url_for("login_page"))
        login_time = session.get("login_time")
        if login_time:
            try:
                from datetime import datetime, timedelta
                login_dt = datetime.strptime(login_time, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - login_dt > timedelta(hours=8):
                    session.clear()
                    return redirect(url_for("login_page"))
            except Exception:
                pass
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Any) -> Any:
    """管理员权限装饰器"""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if "logged_in" not in session:
            return redirect(url_for("login_page"))
        current_user = session.get("username", "")
        users = load_users()
        user_info = next((u for u in users if u["username"] == current_user), None)
        if not user_info or user_info.get("role") != "admin":
            return "无权限，需要管理员权限", 403
        return f(*args, **kwargs)
    return decorated


# ── 验证码 ───────────────────────────────────────────────
def generate_captcha() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=4))


def create_captcha_image(code: str) -> Image.Image:
    from PIL import Image, ImageDraw, ImageFont
    width, height = 140, 44
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/simsunb.ttf",
    ]
    font: Any = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 28)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    x = 5
    for ch in code:
        draw.text((x, random.randint(2, 8)), ch, fill=(0, 0, 0), font=font)
        x += 28 + random.randint(2, 8)
    # 干扰线
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
    return image


# ── Generic Request Rate Limiter (shared across modules) ──────────
_REQUEST_COUNTS: dict[str, list[float]] = {}
_RATE_LIMIT_FILE = os.path.join(DATA_DIR, "rate_limit_state.json")


def _persist_rate_limit() -> None:
    """Periodically persist rate-limit data."""
    try:
        tmp = _RATE_LIMIT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_REQUEST_COUNTS, f)
        os.replace(tmp, _RATE_LIMIT_FILE)
    except Exception:
        pass


def _load_rate_limit() -> None:
    """Load persisted rate-limit data on startup."""
    global _REQUEST_COUNTS
    try:
        if os.path.exists(_RATE_LIMIT_FILE):
            with open(_RATE_LIMIT_FILE, "r") as f:
                saved = json.load(f)
            now = time.time()
            _REQUEST_COUNTS = {
                k: [t for t in v if now - t < 60] for k, v in saved.items()
            }
    except Exception:
        pass


_load_rate_limit()


def _persist_loop() -> None:
    while True:
        time.sleep(30)
        _persist_rate_limit()


_persist_thread = threading.Thread(target=_persist_loop, daemon=True)
_persist_thread.start()


def _rate_limit(key: str, max_requests: int = 10, window: int = 60) -> bool:
    """Simple rate limiter: max_requests per key within window seconds."""
    now = time.time()
    if key not in _REQUEST_COUNTS:
        _REQUEST_COUNTS[key] = []
    _REQUEST_COUNTS[key] = [t for t in _REQUEST_COUNTS[key] if now - t < window]
    if len(_REQUEST_COUNTS[key]) >= max_requests:
        return False
    _REQUEST_COUNTS[key].append(now)
    return True


def rate_limit(max_requests: int = 5, window: int = 60) -> Any:
    """Rate-limit decorator factory."""
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
