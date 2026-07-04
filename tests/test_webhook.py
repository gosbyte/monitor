# -*- coding: utf-8 -*-
"""Tests for webhook.py module."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestBuildItemExpiryPayload:
    """测试 build_item_expiry_payload 函数。"""

    def test_build_item_expiry_payload_basic(self):
        """测试基本的到期载荷构建。"""
        from webhook import build_item_expiry_payload

        cert = {
            "id": 42,
            "customer": "Test Corp",
            "cert_type": "SSL",
            "domain": "test.example.com",
            "expire_date": "2027-12-31",
            "remind_enabled": True,
            "handled": False,
        }
        days_left = 5

        payload = build_item_expiry_payload(cert, days_left)

        assert payload["event"] == "item_expiry"
        assert payload["data"]["id"] == 42
        assert payload["data"]["customer"] == "Test Corp"
        assert payload["data"]["cert_type"] == "SSL"
        assert payload["data"]["domain"] == "test.example.com"
        assert payload["data"]["expire_date"] == "2027-12-31"
        assert payload["data"]["days_left"] == 5
        assert payload["data"]["remind_enabled"] is True
        assert payload["data"]["handled"] is False
        assert "timestamp" in payload
        # 验证 timestamp 是 ISO 格式
        datetime.fromisoformat(payload["timestamp"])

    def test_build_item_expiry_payload_missing_fields(self):
        """测试证书缺少可选字段时使用默认值。"""
        from webhook import build_item_expiry_payload

        cert = {"id": 1}
        days_left = 10

        payload = build_item_expiry_payload(cert, days_left)

        assert payload["data"]["customer"] == ""
        assert payload["data"]["cert_type"] == ""
        assert payload["data"]["domain"] == ""
        assert payload["data"]["expire_date"] == ""
        assert payload["data"]["remind_enabled"] is True
        assert payload["data"]["handled"] is False

    def test_build_item_expiry_payload_negative_days(self):
        """测试已过期的证书（负数天数）。"""
        from webhook import build_item_expiry_payload

        cert = {"id": 99, "customer": "Old Corp", "domain": "old.example.com"}
        days_left = -3

        payload = build_item_expiry_payload(cert, days_left)

        assert payload["data"]["days_left"] == -3

    def test_build_item_expiry_payload_zero_days(self):
        """测试今日到期的证书。"""
        from webhook import build_item_expiry_payload

        cert = {"id": 100, "customer": "Today Corp", "domain": "today.example.com"}
        days_left = 0

        payload = build_item_expiry_payload(cert, days_left)

        assert payload["data"]["days_left"] == 0

    def test_build_item_expiry_payload_handles_true(self):
        """测试已处理的证书。"""
        from webhook import build_item_expiry_payload

        cert = {"id": 101, "customer": "Handled Corp", "handled": True}
        days_left = 5

        payload = build_item_expiry_payload(cert, days_left)

        assert payload["data"]["handled"] is True


class TestBuildItemAddedPayload:
    """测试 build_item_added_payload 函数。"""

    def test_build_item_added_payload_basic(self):
        """测试基本的添加载荷构建。"""
        from webhook import build_item_added_payload

        cert = {
            "id": 5,
            "customer": "New Corp",
            "cert_type": "DV",
            "domain": "new.example.com",
            "expire_date": "2028-06-01",
            "created_by": "admin",
        }

        payload = build_item_added_payload(cert)

        assert payload["event"] == "item_added"
        assert payload["data"]["id"] == 5
        assert payload["data"]["customer"] == "New Corp"
        assert payload["data"]["cert_type"] == "DV"
        assert payload["data"]["domain"] == "new.example.com"
        assert payload["data"]["expire_date"] == "2028-06-01"
        assert payload["data"]["created_by"] == "admin"
        assert "timestamp" in payload
        datetime.fromisoformat(payload["timestamp"])

    def test_build_item_added_payload_missing_created_by(self):
        """测试缺少 created_by 字段时使用默认值。"""
        from webhook import build_item_added_payload

        cert = {"id": 6, "customer": "No Creator Corp", "domain": "nocreator.example.com"}

        payload = build_item_added_payload(cert)

        assert payload["data"]["created_by"] == ""

    def test_build_item_added_payload_event_type(self):
        """测试事件类型正确设置为 item_added。"""
        from webhook import build_item_added_payload

        cert = {"id": 7}
        payload = build_item_added_payload(cert)

        assert payload["event"] == "item_added"


class TestBuildItemDeletedPayload:
    """测试 build_item_deleted_payload 函数。"""

    def test_build_item_deleted_payload_basic(self):
        """测试基本的删除载荷构建。"""
        from webhook import build_item_deleted_payload

        payload = build_item_deleted_payload(10, "Deleted Corp")

        assert payload["event"] == "item_deleted"
        assert payload["data"]["id"] == 10
        assert payload["data"]["customer"] == "Deleted Corp"
        assert "timestamp" in payload
        datetime.fromisoformat(payload["timestamp"])

    def test_build_item_deleted_payload_zero_id(self):
        """测试 id 为 0 的情况。"""
        from webhook import build_item_deleted_payload

        payload = build_item_deleted_payload(0, "")

        assert payload["data"]["id"] == 0
        assert payload["data"]["customer"] == ""

    def test_build_item_deleted_payload_event_type(self):
        """测试事件类型正确设置为 item_deleted。"""
        from webhook import build_item_deleted_payload

        payload = build_item_deleted_payload(1, "Test")

        assert payload["event"] == "item_deleted"


class TestSendWebhook:
    """测试 send_webhook 函数。"""

    @patch("webhook.requests.post")
    def test_send_webhook_success(self, mock_post):
        """测试 webhook 发送成功。"""
        from webhook import send_webhook

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = send_webhook("https://example.com/hook", {"key": "value"})

        assert result is True
        mock_post.assert_called_once_with(
            "https://example.com/hook",
            json={"key": "value"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    @patch("webhook.requests.post")
    def test_send_webhook_non_200(self, mock_post):
        """测试 webhook 返回非 200 状态码。"""
        from webhook import send_webhook

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = send_webhook("https://example.com/hook", {"key": "value"})

        assert result is False

    @patch("webhook.requests.post")
    def test_send_webhook_exception(self, mock_post):
        """测试 webhook 发送异常。"""
        from webhook import send_webhook

        mock_post.side_effect = Exception("Connection refused")

        result = send_webhook("https://example.com/hook", {"key": "value"})

        assert result is False

    @patch("webhook.requests.post")
    def test_send_webhook_custom_timeout(self, mock_post):
        """测试自定义超时参数。"""
        from webhook import send_webhook

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = send_webhook("https://example.com/hook", {"key": "value"}, timeout=30)

        assert result is True
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == 30
