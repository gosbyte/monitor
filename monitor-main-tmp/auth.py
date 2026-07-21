# -*- coding: utf-8 -*-
"""
认证层 - CSRF、验证码、登录/权限装饰器（依赖 Flask）
注意：login_required 使用 url_for("index")，需在 app.py 注册路由后使用
"""
from __future__ import annotations

import secrets
import random
import string
import os
from functools import wraps
from typing import Any
from PIL import Image

from flask import session, redirect, url_for, request, Response
_badge_count_cache: dict | None = None

from data import (
    load_certs, calc_days_left, load_users, save_users,
    verify_user, is_user_locked, get_lock_seconds,
    do_lock_user, reset_failed_attempts,
)


# ── 上下文处理器 ─────────────────────────────────────────
_badge_count_cache: dict | None = None

def inject_globals() -> dict[str, Any]:
    """向所有模板注入 csrf_token, badge_count 和 csp_nonce"""
    global _badge_count_cache
    badge_count = 0
    # Use cached badge count if available (set by route handlers)
    if _badge_count_cache is not None:
        badge_count = _badge_count_cache.get("badge_count", 0)
    elif session.get("username"):
        try:
            certs = load_certs()
            for c in certs:
                # [FIX] P1-4: 使用浅拷贝避免修改原始数据
                cert_copy: dict[str, Any] = dict(c)
                cert_copy["days_left"] = calc_days_left(cert_copy.get("expire_date", ""))
                badge_count += 1 if (
                    cert_copy.get("remind_enabled", True)
                    and not cert_copy.get("handled")
                    and 0 <= cert_copy.get("days_left", 999) <= 7
                ) else 0
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


def csrf_required(f: Any) -> Any:
    """CSRF 验证装饰器，所有 POST 路由使用"""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        # Only check CSRF for state-changing methods, not GET
        if request.method in ("POST", "PUT", "DELETE", "PATCH") and not _check_csrf():
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
    from PIL import ImageDraw, ImageFont
    width, height = 140, 44
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
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
