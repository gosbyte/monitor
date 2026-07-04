# -*- coding: utf-8 -*-
"""Tests for app_init.py - configuration, security headers, and metrics."""
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from flask import Flask


class TestLoadConfigEnvOverride:
    """测试环境变量覆盖配置的行为。"""

    def test_secret_key_from_env(self, temp_data_dir):
        """测试 SECRET_KEY 环境变量优先于文件。"""
        # 确保环境变量存在
        os.environ["SECRET_KEY"] = "env-secret-key-overridden"

        # 重新导入 app_init 以使用环境变量
        import importlib
        import sys
        # 清除缓存
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            del sys.modules[mod]

        import app_init
        # 验证 secret_key 使用了环境变量
        assert app_init.app.secret_key == "env-secret-key-overridden"

        # 清理
        os.environ.pop("SECRET_KEY", None)
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_secret_key_from_file(self, temp_data_dir):
        """测试从文件加载 SECRET_KEY。"""
        # 确保没有环境变量
        os.environ.pop("SECRET_KEY", None)

        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init
        # secret_key 不应为空
        assert len(app_init.app.secret_key) > 0
        assert app_init.app.secret_key != "env-secret-key-overridden"

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_max_content_length_config(self, temp_data_dir):
        """测试文件上传大小限制配置。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init
        assert app_init.app.config["MAX_CONTENT_LENGTH"] == 10 * 1024 * 1024

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_session_cookie_httponly(self, temp_data_dir):
        """测试 SESSION_COOKIE_HTTPONLY 配置。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init
        assert app_init.app.config["SESSION_COOKIE_HTTPONLY"] is True

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_session_cookie_samesite_strict(self, temp_data_dir):
        """测试 SESSION_COOKIE_SAMESITE 配置为 Strict。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init
        assert app_init.app.config["SESSION_COOKIE_SAMESITE"] == "Strict"

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_permanent_session_lifetime(self, temp_data_dir):
        """测试 SESSION_PERMANENT 和会话生命周期。"""
        import importlib
        import sys
        from datetime import timedelta
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init
        assert app_init.app.config["SESSION_PERMANENT"] is True
        assert app_init.app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=8)

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]


class TestValidatePasswordEnhanced:
    """测试 validate_password 函数。"""

    def test_valid_password_minimal(self):
        """测试满足最低要求的有效密码。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Abcdef123456!")
        assert ok is True
        assert score > 0

    def test_valid_password_long(self):
        """测试长密码。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("A" * 64 + "b1!")
        assert ok is True
        assert score > 0

    def test_password_too_short(self):
        """测试密码太短。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Ab1")
        assert ok is False
        assert "长度" in msg

    def test_password_no_uppercase(self):
        """测试密码缺少大写字母。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("abcdef123456!")
        assert ok is False

    def test_password_no_lowercase(self):
        """测试密码缺少小写字母。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("ABCDEF123456!")
        assert ok is False

    def test_password_no_digit(self):
        """测试密码缺少数字。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Abcdefghijkl!")
        assert ok is False

    def test_password_no_special_char(self):
        """测试密码缺少特殊字符但仍可能通过（取决于策略）。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Abcdefg12345")
        # 该密码满足最小长度和复杂度要求，可能通过
        assert isinstance(ok, bool)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_password_empty(self):
        """测试空密码。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("")
        assert ok is False
        assert "空" in msg

    def test_password_none(self):
        """测试 None 密码。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password(None)
        assert ok is False
        assert "空" in msg

    def test_password_strength_returns_tuple(self):
        """测试返回值包含强度等级。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Abcdef123456!")
        assert isinstance(strength, str)
        assert strength in ("极弱", "弱", "一般", "强", "极强")

    def test_password_score_range(self):
        """测试密码分数范围。"""
        from app_init import validate_password
        ok, msg, score, strength = validate_password("Abcdef123456!")
        assert 0 <= score <= 100


class TestSecurityHeadersPresent:
    """测试安全头中间件。"""

    def test_x_frame_options(self, temp_data_dir):
        """测试 X-Frame-Options 安全头。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            assert resp.headers["X-Frame-Options"] == "DENY"

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_x_content_type_options(self, temp_data_dir):
        """测试 X-Content-Type-Options 安全头。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            assert resp.headers["X-Content-Type-Options"] == "nosniff"

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_x_xss_protection(self, temp_data_dir):
        """测试 X-XSS-Protection 安全头。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            assert "1; mode=block" in resp.headers["X-XSS-Protection"]

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_referrer_policy(self, temp_data_dir):
        """测试 Referrer-Policy 安全头。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_x_request_id_present(self, temp_data_dir):
        """测试 X-Request-ID 响应头。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            assert "X-Request-ID" in resp.headers
            assert len(resp.headers["X-Request-ID"]) > 0

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_csp_on_html_response(self, temp_data_dir):
        """测试 HTML 响应包含 Content-Security-Policy。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/")
            csp = resp.headers.get("Content-Security-Policy", "")
            assert "default-src" in csp
            assert "'self'" in csp

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_csp_not_on_json_response(self, temp_data_dir):
        """测试 JSON 响应不包含 CSP。"""
        import importlib
        import sys
        mods_to_remove = [k for k in sys.modules if k.startswith('app_init') or k == 'dingtalk' or k == 'webhook' or k.startswith('routes')]
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        import app_init

        with app_init.app.test_client() as client:
            resp = client.get("/health")
            # /health 返回 JSON，不应有 CSP
            assert "Content-Security-Policy" not in resp.headers or "default-src" not in resp.headers.get("Content-Security-Policy", "")

        # 清理
        for mod in mods_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]
