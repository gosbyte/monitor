# -*- coding: utf-8 -*-
"""认证相关路由 - login/logout/change_password/users管理"""
from __future__ import annotations

import json
import os
import io
import time
import random
import string
import secrets
import logging
from datetime import datetime, timedelta
from typing import Any, Union

from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session, make_response, g

# Flask route handlers can return str, tuple[str, int], or Response
_FlaskResponse = Union[str, tuple[str, int], Response]

from exceptions import ValidationError, PermissionDenied, DataError, ServiceError

from data import (
    load_users, save_users, verify_user, is_user_locked,
    get_lock_seconds, do_lock_user, reset_failed_attempts,
    validate_password, generate_password_hash, check_password_hash,
    write_log, DATA_DIR,
)
from auth import (
    inject_globals, csrf_required, login_required, admin_required,
    generate_captcha, create_captcha_image, _check_api_csrf,
)


logger = logging.getLogger(__name__)


# ── IP 级别登录限流 ──────────────────────────────────────
_LOGIN_ATTEMPTS: dict[str, list[tuple[float, bool]]] = {}  # {ip: [(timestamp, success)]}
_LOGIN_MAX_ATTEMPTS: int = 10  # 10 次/分钟
_LOGIN_COOLDOWN: int = 300  # 5 分钟冷却
_LOGIN_ATTEMPTS_FILE = os.path.join(DATA_DIR, "login_attempts.json")


def _persist_login_attempts():
    """定期持久化登录限流数据"""
    try:
        tmp = _LOGIN_ATTEMPTS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_LOGIN_ATTEMPTS, f)
        os.replace(tmp, _LOGIN_ATTEMPTS_FILE)
    except Exception:
        pass


def _load_login_attempts():
    """从文件加载登录限流数据"""
    global _LOGIN_ATTEMPTS
    try:
        if os.path.exists(_LOGIN_ATTEMPTS_FILE):
            with open(_LOGIN_ATTEMPTS_FILE, "r") as f:
                saved = json.load(f)
            now = time.time()
            _LOGIN_ATTEMPTS = {
                ip: [(t, s) for t, s in attempts if now - t < 300]
                for ip, attempts in saved.items()
            }
    except Exception:
        pass


# 启动时加载
_load_login_attempts()

# 定时持久化（每 30 秒）
import threading
from utils.request_utils import get_client_ip


def _persist_login_loop():
    while True:
        time.sleep(30)
        _persist_login_attempts()


_persist_login_thread = threading.Thread(target=_persist_login_loop, daemon=True)
_persist_login_thread.start()


def _rate_limit_login(ip: str) -> bool:
    """IP 级别登录限流"""
    now = time.time()
    if ip not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[ip] = []
    _LOGIN_ATTEMPTS[ip] = [(t, s) for t, s in _LOGIN_ATTEMPTS[ip] if now - t < 60]
    if len(_LOGIN_ATTEMPTS[ip]) >= _LOGIN_MAX_ATTEMPTS:
        return False
    _LOGIN_ATTEMPTS[ip].append((now, True))
    return True


def register_auth_routes(app: Flask) -> None:
    """注册认证相关路由"""

    @app.route("/captcha")
    def captcha() -> Response:
        code = generate_captcha()
        session["captcha"] = code.lower()
        img = create_captcha_image(code)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return Response(buf.read(), mimetype='image/png')

    @app.route("/login")
    def login_page() -> _FlaskResponse:
        if session.get("logged_in"):
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login() -> _FlaskResponse:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        # Captcha disabled per user feedback (mobile input difficulty)
        # captcha_code = request.form.get("captcha", "").strip().lower()
        client_ip = request.remote_addr or "unknown"

        now = time.time()
        if client_ip not in _LOGIN_ATTEMPTS:
            _LOGIN_ATTEMPTS[client_ip] = []
        _LOGIN_ATTEMPTS[client_ip] = [(t, s) for t, s in _LOGIN_ATTEMPTS[client_ip] if now - t < 60]
        if len(_LOGIN_ATTEMPTS[client_ip]) >= _LOGIN_MAX_ATTEMPTS:
            logger.warning(f"IP {client_ip} 登录频率超限")
            return render_template("login.html", error="请求过于频繁，请稍后再试")

        # Captcha validation disabled
        # if captcha_code != session.get("captcha", ""):
        #     _LOGIN_ATTEMPTS.setdefault(client_ip, []).append((now, False))
        #     return render_template("login.html", error="验证码错误")

        if is_user_locked(username):
            secs = get_lock_seconds(username)
            mins = secs // 60
            sec = secs % 60
            return render_template("login.html", error=f"账户已锁定，请 {mins} 分 {sec:02d} 秒后再试")

        users = load_users()
        user_exists = any(u["username"] == username for u in users)

        if verify_user(username, password):
            reset_failed_attempts(username)
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            session["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session.permanent = True
            logger.info(f"用户 {username} 登录成功 (IP: {client_ip})")
            # [FIX] P0-6: 参数正确传递
            write_log(username, "登录", "登录成功", "系统", client_ip)
            if client_ip in _LOGIN_ATTEMPTS:
                _LOGIN_ATTEMPTS[client_ip] = []
            return redirect(url_for("index"))
        else:
            if user_exists:
                for u in users:
                    if u["username"] == username:
                        u["failed_attempts"] = u.get("failed_attempts", 0) + 1
                        remaining = 5 - u["failed_attempts"]
                        save_users(users)
                        if u["failed_attempts"] >= 5:
                            do_lock_user(username)
                            users2 = load_users()
                            lu = next((x for x in users2 if x["username"] == username), None)
                            lock_until = datetime.strptime(lu["lock_until"], "%Y-%m-%d %H:%M:%S")
                            delta = lock_until - datetime.now()
                            total_min = max(1, int(delta.total_seconds() // 60))
                            return render_template("login.html", error=f"用户名或密码错误，账户已锁定 {total_min} 分钟")
                        else:
                            logger.warning(f"用户 {username} 登录失败，剩余 {remaining} 次机会")
                            _LOGIN_ATTEMPTS.setdefault(client_ip, []).append((now, False))
                            return render_template("login.html", error=f"用户名或密码错误，剩余 {remaining} 次机会")
                        break
            logger.warning(f"用户 {username} 登录失败 (IP: {client_ip})")
            _LOGIN_ATTEMPTS.setdefault(client_ip, []).append((now, False))
            return render_template("login.html", error="用户名或密码错误")

    @app.route("/logout")
    def logout() -> str:
        username = session.get("username", "?")
        session.clear()
        return redirect(url_for("login_page"))

    @app.route("/change_password")
    @login_required
    def change_password() -> _FlaskResponse:
        username = session.get("username", "")
        users = load_users()
        current_user = next((u for u in users if u["username"] == username), None)
        if request.method == "POST":
            old_pwd = request.form.get("old_password", "")
            new_pwd = request.form.get("new_password", "")
            confirm_pwd = request.form.get("confirm_password", "")
            if not current_user or not check_password_hash(current_user["password"], old_pwd):
                return render_template("change_password.html", error="原密码错误")
            valid, msg = validate_password(new_pwd)[:2]
            if not valid:
                return render_template("change_password.html", error=msg)
            if new_pwd != confirm_pwd:
                return render_template("change_password.html", error="两次密码不一致")
            current_user["password"] = generate_password_hash(new_pwd)
            current_user["force_change_password"] = 0
            save_users(users)
            write_log(username, "修改密码", "首次登录强制修改密码完成", "系统", get_client_ip(request))
            return redirect(url_for("index"))
        return render_template("change_password.html")

    # ── 用户管理 ────────────────────────────────────────────
    @app.route("/users")
    @admin_required
    def users_page() -> str:
        users = load_users()
        current_user = session.get("username", "")
        user_info = next((u for u in users if u["username"] == current_user), None)
        is_admin = user_info.get("role") == "admin" if user_info else False
        return render_template("users.html", users=users, is_admin=is_admin)

    @app.route("/users/add", methods=["POST"])
    @admin_required
    @csrf_required
    def add_user() -> _FlaskResponse:
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user").strip()
        if not username or not password:
            raise DataError("用户名和密码不能为空")
        valid, msg = validate_password(password)[:2]
        if not valid:
            raise DataError(msg)
        if role not in ("admin", "user"):
            role = "user"
        users = load_users()
        if any(u["username"] == username for u in users):
            raise DataError("用户名已存在")
        users.append({"username": username, "name": name or username, "password": generate_password_hash(password), "dingtalk_id": "", "role": role})
        save_users(users)
        write_log(session.get("username", "?"), "添加用户", f"添加用户 {username}（姓名：{name}）", username, get_client_ip(request))
        return redirect(url_for("users_page") + "?success=用户添加成功")

    @app.route("/users/edit/<username>", methods=["POST"])
    @admin_required
    @csrf_required
    def edit_user(username: str) -> _FlaskResponse:
        users = load_users()
        target = next((u for u in users if u["username"] == username), None)
        if not target:
            raise ValidationError("用户不存在")
        target["name"] = request.form.get("name", "").strip()
        target["role"] = request.form.get("role", "user").strip()
        password = request.form.get("password", "").strip()
        if password:
            valid, msg = validate_password(password)[:2]
            if not valid:
                raise DataError(msg)
            target["password"] = generate_password_hash(password)
        target["dingtalk_id"] = request.form.get("dingtalk_id", "").strip()
        save_users(users)
        write_log(session.get("username", "?"), "编辑用户", f"编辑用户 {username}", username, get_client_ip(request))
        return redirect(url_for("users_page") + "?success=用户信息已保存")

    @app.route("/users/password/<username>", methods=["POST"])
    @login_required
    @csrf_required
    def change_user_password(username: str) -> _FlaskResponse:
        new_pwd = request.form.get("new_password", "").strip()
        valid, msg = validate_password(new_pwd)[:2]
        if not valid:
            raise DataError(msg)
        current_user = session.get("username", "")
        users = load_users()
        for u in users:
            if u["username"] == username:
                if username != current_user:
                    cr = next((x.get("role") for x in users if x["username"] == current_user), "user")
                    if cr != "admin":
                        raise PermissionDenied("无权限修改他人密码")
                u["password"] = generate_password_hash(new_pwd)
                break
        else:
            raise ValidationError("用户不存在")
        save_users(users)
        write_log(session.get("username", "?"), "修改密码", f"修改用户 {username} 的密码", username, get_client_ip(request))
        return redirect(url_for("index") + "?success=密码修改成功")

    @app.route("/users/delete/<username>", methods=["POST"])
    @admin_required
    @csrf_required
    def delete_user(username: str) -> _FlaskResponse:
        if username == "admin":
            raise DataError("不能删除默认管理员")
        users = [u for u in load_users() if u["username"] != username]
        save_users(users)
        write_log(session.get("username", "?"), "删除用户", f"删除用户 {username}", username, get_client_ip(request))
        return redirect(url_for("users_page") + "?success=用户已删除")

    @app.route("/users/unlock/<username>", methods=["POST"])
    @admin_required
    @csrf_required
    def unlock_user(username: str) -> str:
        users = load_users()
        for u in users:
            if u["username"] == username:
                u["failed_attempts"] = 0
                u["lock_until"] = None
                u["consecutive_locks"] = 0
                break
        save_users(users)
        write_log(session.get("username", "?"), "解锁用户", f"解锁用户 {username}", username, get_client_ip(request))
        return redirect(url_for("users_page") + "?success=用户已解锁")

    @app.route("/users/dingtalk_id", methods=["POST"])
    @login_required
    def update_dingtalk_id() -> Response:
        if not _check_api_csrf():
            return jsonify({"ok": False, "error": "CSRF验证失败"}), 403
        username = request.form.get("username", "").strip()
        dingtalk_id = request.form.get("dingtalk_id", "").strip()
        if not username:
            return jsonify({"ok": False, "error": "用户名不能为空"}), 400
        users = load_users()
        for u in users:
            if u["username"] == username:
                u["dingtalk_id"] = dingtalk_id
                break
        else:
            return jsonify({"ok": False, "error": "用户不存在"}), 404
        save_users(users)
        logger.info(f"用户 {username} 钉钉ID已更新: {dingtalk_id}")
        write_log(session.get("username", "?"), "更新钉钉ID", f"为用户 {username} 更新钉钉ID：{dingtalk_id}", username, get_client_ip(request))
        return jsonify({"ok": True})

