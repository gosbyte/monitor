# -*- coding: utf-8 -*-
"""管理员功能路由 - 配置/批量操作/日志/推送历史/数据管理"""
from __future__ import annotations

import json
import os
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Any, Union

from flask import Flask, request, jsonify, render_template, redirect, url_for, session

from exceptions import ValidationError, DataError, ServiceError

from data import (
    load_certs, save_certs, load_config, save_config, write_log,
    calc_days_left, get_cert_status, load_logs, save_logs, load_users,
    DATA_DIR, BASE_DIR, reload_config,
)
from auth import login_required, admin_required, csrf_required


# Flask route handlers can return str, tuple[str, int], or Response
_FlaskResponse = Union[str, tuple[str, int], Any]

logger = logging.getLogger(__name__)


def _check_api_csrf() -> bool:
    """API CSRF 检查"""
    if request.method == "GET":
        return True
    token = request.headers.get("X-CSRF-Token")
    if not token and request.is_json:
        token = request.json.get("_csrf_token")  # type: ignore[union-attr]
    if not token or token != session.get("_csrf_token"):
        return False
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        session["_csrf_token"] = secrets.token_hex(32)
    return True


def register_admin_routes(app: Flask) -> None:
    """注册管理员功能路由"""

    @app.route("/config", methods=["GET", "POST"])
    @admin_required
    def config_page() -> _FlaskResponse:
        cfg = load_config()
        users = load_users()
        current_username = session.get("username", "")
        current_user = next((u for u in users if u["username"] == current_username), None)
        is_admin = current_user.get("role") == "admin" if current_user else False
        if request.method == "POST":
            cfg["webhook_url"] = request.form.get("webhook_url", "").strip()
            cfg["remind_days"] = [int(x) for x in request.form.getlist("remind_days") if x.strip().isdigit()]
            if not cfg["remind_days"]:
                cfg["remind_days"] = [7, 3, 1]
            save_config(cfg)
            return redirect(url_for("index") + "?success=配置已保存")
        return render_template("config.html", cfg=cfg, is_admin=is_admin)

    @app.route("/api/save_config", methods=["POST"])
    @login_required
    @admin_required
    def api_save_config() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        cfg = load_config()
        data = request.get_json()
        if data:
            for k, v in data.items():
                if k == 'remind_days' and isinstance(v, list):
                    cfg[k] = v
                elif k != '_csrf_token':
                    cfg[k] = v
            save_config(cfg)
        return jsonify({"ok": True, "message": "保存成功", "csrf_token": session.get("_csrf_token", "")})

    # ── 批量操作 ──────────────────────────────────────────────
    @app.route("/api/batch_delete", methods=["POST"])
    @login_required
    @admin_required
    def api_batch_delete() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        data = request.get_json() or {}
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"ok": False, "message": "未选择记录"}), 400
        certs = load_certs()
        deleted_ids = [c["id"] for c in certs if c["id"] in ids]
        certs = [c for c in certs if c["id"] not in ids]
        save_certs(certs)
        # 清理 remind_state 中已删除的记录
        state_file = os.path.join(DATA_DIR, "remind_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if isinstance(state, dict):
                    cleaned = {k: v for k, v in state.items()
                              if not any(str(cid) in k for cid in ids)}
                    tmp = state_file + ".tmp"
                    with open(tmp, "w") as f:
                        json.dump(cleaned, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, state_file)
            except Exception:
                pass
        current_user = session.get("username", "?")
        write_log(current_user, "批量删除", f"删除 {len(deleted_ids)} 条记录", "到期项", request.remote_addr or '')
        return jsonify({"ok": True, "message": f"删除 {len(deleted_ids)} 条记录", "deleted_ids": deleted_ids, "csrf_token": session.get("_csrf_token", "")})

    @app.route("/api/batch_handle", methods=["POST"])
    @login_required
    @admin_required
    def api_batch_handle() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        data = request.get_json() or {}
        ids = data.get("ids", [])
        handled = data.get("handled", True)
        if not ids:
            return jsonify({"ok": False, "message": "未选择记录"}), 400
        certs = load_certs()
        count = 0
        for c in certs:
            if c["id"] in ids:
                c["handled"] = handled
                count += 1
        save_certs(certs)
        label = "标记已处理" if handled else "取消已处理"
        current_user = session.get("username", "?")
        write_log(current_user, f"批量{label}", f"{count} 条记录", "到期项", request.remote_addr or '')
        return jsonify({"ok": True, "message": f"{label} {count} 条记录", "csrf_token": session.get("_csrf_token", "")})

    @app.route("/api/batch_remind", methods=["POST"])
    @login_required
    @admin_required
    def api_batch_remind() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        data = request.get_json() or {}
        ids = data.get("ids", [])
        remind_enabled = data.get("remind_enabled", True)
        if not ids:
            return jsonify({"ok": False, "message": "未选择记录"}), 400
        certs = load_certs()
        count = 0
        for c in certs:
            if c["id"] in ids:
                c["remind_enabled"] = remind_enabled
                count += 1
        save_certs(certs)
        label = "启用提醒" if remind_enabled else "禁用提醒"
        current_user = session.get("username", "?")
        write_log(current_user, f"批量{label}", f"{count} 条记录", "到期项", request.remote_addr or '')
        return jsonify({"ok": True, "message": f"{label} {count} 条记录", "csrf_token": session.get("_csrf_token", "")})

    # ── 日志管理 ──────────────────────────────────────────────
    @app.route("/logs")
    @admin_required
    def logs_page() -> _FlaskResponse:
        logs = load_logs()
        logs.sort(key=lambda x: x["time"], reverse=True)
        users = load_users()
        current_username = session.get("username", "")
        current_user = next((u for u in users if u["username"] == current_username), None)
        is_admin = current_user.get("role") == "admin" if current_user else False
        return render_template("logs.html", logs=logs[:200], total=len(logs), users=users, is_admin=is_admin)

    @app.route("/logs/clear", methods=["POST"])
    @admin_required
    @csrf_required
    def clear_logs() -> _FlaskResponse:
        save_logs([])
        write_log(session.get("username", "?"), "清空日志", "清空全部操作日志", "系统", request.remote_addr or '')
        return redirect(url_for("logs_page") + "?success=日志已清空")

    # ── 推送历史 ──────────────────────────────────────────────
    @app.route("/push_history")
    @admin_required
    def push_history_page() -> _FlaskResponse:
        users = load_users()
        current_username = session.get("username", "")
        current_user = next((u for u in users if u["username"] == current_username), None)
        is_admin = current_user.get("role") == "admin" if current_user else False
        push_history_file = os.path.join(DATA_DIR, "push_history.json") if DATA_DIR != BASE_DIR else os.path.join(BASE_DIR, "push_history.json")
        history: list[dict[str, Any]] = []
        if os.path.exists(push_history_file):
            with open(push_history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        history.sort(key=lambda x: x.get("time", ""), reverse=True)
        return render_template("push_history.html", history=history, is_admin=is_admin)

    # ── 数据管理 ──────────────────────────────────────────────
    @app.route("/data_manage")
    @login_required
    @admin_required
    def data_manage_page() -> _FlaskResponse:
        return render_template("data_manage.html")

    # ── 日志清理 API ──────────────────────────────────────
    @app.route("/api/admin/cleanup-logs", methods=["POST"])
    @login_required
    @admin_required
    @csrf_required
    def api_cleanup_logs() -> Any:
        """手动触发日志清理"""
        try:
            # 从 app_init 导入 cleanup_logs 函数
            from app_init import cleanup_logs
            cleaned, freed = cleanup_logs()
            msg = f"清理完成: {cleaned} 项, 释放 ~{freed / 1024 / 1024:.1f}MB"
            write_log(session.get("username", "?"), "日志清理", msg, "系统", request.remote_addr or '')
            return jsonify({"ok": True, "message": msg, "csrf_token": session.get("_csrf_token", "")})
        except Exception as e:
            logger.exception("日志清理失败")
            raise ServiceError(f"清理失败: {str(e)}")

    # ── 配置热更新 API ────────────────────────────────────
    @app.route("/api/admin/reload-config", methods=["POST"])
    @login_required
    @admin_required
    @csrf_required
    def api_reload_config() -> Any:
        """手动触发配置热更新"""
        try:
            cfg = reload_config()
            msg = "配置已热更新"
            write_log(session.get("username", "?"), "配置热更新", msg, "系统", request.remote_addr or '')
            return jsonify({"ok": True, "message": msg, "config": cfg, "csrf_token": session.get("_csrf_token", "")})
        except Exception as e:
            logger.exception("配置热更新失败")
            raise ServiceError(f"热更新失败: {str(e)}")
