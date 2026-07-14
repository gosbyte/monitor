# -*- coding: utf-8 -*-
"""API 端点路由 - 状态切换/测试推送/Webhook"""
from __future__ import annotations

import os
import time
import json
import secrets
import logging
import smtplib
from datetime import datetime
from typing import Any

from flask import Flask, request, jsonify, session

from exceptions import ValidationError, DataError, ServiceError

from data import (
    load_certs, save_certs, load_config, calc_days_left, get_cert_status,
    encrypt_field, decrypt_field, load_users, write_log, DATA_DIR,
)
from auth import login_required, admin_required, csrf_required, _check_api_csrf, rate_limit


logger = logging.getLogger(__name__)


def register_api_routes(app: Flask) -> None:
    """注册 API 端点路由"""

    @app.route("/api/status/<int:cert_id>", methods=["POST"])
    @login_required
    def toggle_status(cert_id: int) -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        certs = load_certs()
        for c in certs:
            if c["id"] == cert_id:
                c["remind_enabled"] = not c.get("remind_enabled", True)
                save_certs(certs)
                return jsonify({"ok": True, "remind_enabled": c["remind_enabled"], "csrf_token": session.get("_csrf_token", "")})
        return jsonify({"ok": False, "csrf_token": session.get("_csrf_token", "")}), 404

    @app.route("/api/handle/<int:cert_id>", methods=["POST"])
    @login_required
    def toggle_handle(cert_id: int) -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        certs = load_certs()
        for c in certs:
            if c["id"] == cert_id:
                c["handled"] = not c.get("handled", False)
                save_certs(certs)
                return jsonify({"ok": True, "handled": c["handled"], "csrf_token": session.get("_csrf_token", "")})
        return jsonify({"ok": False, "csrf_token": session.get("_csrf_token", "")}), 404

    # ── 邮件测试 ──────────────────────────────────────────────
    @app.route("/api/test_email", methods=["POST"])
    @login_required
    @admin_required
    @rate_limit(max_requests=3, window=60)
    def api_test_email() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        cfg = load_config()
        if cfg.get("smtp_pass"):
            cfg["smtp_pass"] = decrypt_field(cfg["smtp_pass"])
        smtp_host = cfg.get("smtp_host", "").strip()
        smtp_port = cfg.get("smtp_port", 465)
        smtp_user = cfg.get("smtp_user", "").strip()
        smtp_pass = cfg.get("smtp_pass", "").strip()
        smtp_to = cfg.get("smtp_to", "").strip()
        if not smtp_host or not smtp_user or not smtp_pass or not smtp_to:
            return jsonify({"ok": False, "message": "请先配置完整的邮件服务器信息"}), 400
        recipients: list[str] = [r.strip() for r in smtp_to.split(",") if r.strip()]
        if not recipients:
            return jsonify({"ok": False, "message": "收件人地址为空"}), 400
        try:
            port = int(smtp_port)
        except ValueError:
            port = 465
        try:
            subject = "到期提醒系统 - 测试邮件"
            content = "这是一封测试邮件，确认邮件提醒功能正常！\n\n发送时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            from_name = cfg.get("smtp_from_name", "到期提醒系统").strip() or "到期提醒系统"
            from_addr = f"{from_name} <{smtp_user}>" if from_name else smtp_user
            msg = f"From: {from_addr}\r\nTo: {','.join(recipients)}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{content}"
            if port == 465:
                with smtplib.SMTP_SSL(smtp_host, port, timeout=10) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, recipients, msg.encode("utf-8"))
            else:
                with smtplib.SMTP(smtp_host, port, timeout=10) as server:
                    server.ehlo()
                    if port == 587:
                        server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, recipients, msg.encode("utf-8"))
            return jsonify({"ok": True, "message": f"测试邮件发送成功！已发送至 {len(recipients)} 个收件人", "csrf_token": session.get("_csrf_token", "")})
        except Exception as e:
            logger.exception("测试邮件发送失败")
            raise ServiceError(f"邮件发送失败: {str(e)}")

    # ── 企业微信配置/测试 ─────────────────────────────────────
    @app.route("/api/config/wecom", methods=["POST"])
    @login_required
    @admin_required
    def api_config_wecom() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        cfg = load_config()
        data = request.get_json() or {}
        cfg["wecom_enabled"] = bool(data.get("wecom_enabled", False))
        cfg["wecom_webhook"] = data.get("wecom_webhook", "").strip()
        save_config(cfg)
        return jsonify({"ok": True, "message": "保存成功", "csrf_token": session.get("_csrf_token", "")})

    @app.route("/api/test_wecom", methods=["POST"])
    @login_required
    @admin_required
    @rate_limit(max_requests=5, window=60)
    def api_test_wecom() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        cfg = load_config()
        webhook_url = (request.get_json() or {}).get("wecom_webhook", "").strip()
        if not webhook_url:
            webhook_url = cfg.get("wecom_webhook", "").strip()
        if not webhook_url:
            return jsonify({"ok": False, "message": "未配置企业微信 Webhook"}), 400
        import requests
        payload: dict[str, Any] = {"msgtype": "markdown", "markdown": {"content": f"🧪 测试消息\n\n到期提醒管理系统连接正常！\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}}
        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
            if r.status_code == 200 and r.json().get("errcode") == 0:
                return jsonify({"ok": True, "message": "测试推送成功", "csrf_token": session.get("_csrf_token", "")})
            return jsonify({"ok": False, "message": f"推送失败：{r.text[:200]}", "csrf_token": session.get("_csrf_token", "")}), 400
        except Exception as e:
            raise ServiceError(f"推送出错: {str(e)}")

    @app.route("/api/test_push", methods=["POST"])
    @login_required
    @admin_required
    @rate_limit(max_requests=5, window=60)
    def api_test_push() -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        from dingtalk import send_dingtalk_card
        cfg = load_config()
        webhook_url = cfg.get("webhook_url", "").strip()
        if not webhook_url:
            return jsonify({"ok": False, "message": "未配置 Webhook 地址"}), 400
        test_content = "🧪 这是一条测试消息\n\n到期提醒管理系统连接正常！\n时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        secret = cfg.get("secret", "")
        success = send_dingtalk_card(webhook_url, "到期提醒系统 - 测试消息", test_content, secret)
        return jsonify({"ok": success, "message": "测试消息发送成功" if success else "发送失败", "csrf_token": session.get("_csrf_token", "")})

    @app.route("/api/push/<int:cert_id>", methods=["POST"])
    @login_required
    @admin_required
    def api_push_cert(cert_id: int) -> Any:
        if not _check_api_csrf():
            return jsonify({"ok": False, "message": "CSRF验证失败"}), 403
        from dingtalk import send_dingtalk_card, build_remind_card
        cfg = load_config()
        webhook_url = cfg.get("webhook_url", "").strip()
        if not webhook_url:
            return jsonify({"ok": False, "message": "未配置 Webhook 地址"}), 400
        certs = load_certs()
        cert = next((c for c in certs if c["id"] == cert_id), None)
        if not cert:
            return jsonify({"ok": False, "message": "到期项不存在"}), 404
        cert["days_left"] = calc_days_left(cert["expire_date"])
        users = load_users()
        users_map: dict[str, dict[str, Any]] = {u["username"]: u for u in users}
        title, content, at_ids = build_remind_card([cert], users_map)
        secret = cfg.get("secret", "")
        success = send_dingtalk_card(webhook_url, title, content, secret, at_user_ids=at_ids if at_ids else None)
        write_log(session.get("username", "?"), "推送提醒", f"推送 {cert['customer']}（剩余 {cert['days_left']:.0f} 天）", f"到期项 #{cert_id}", request.remote_addr or '')
        return jsonify({"ok": success, "message": "推送成功" if success else "推送失败", "csrf_token": session.get("_csrf_token", "")})
