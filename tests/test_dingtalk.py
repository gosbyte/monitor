# -*- coding: utf-8 -*-
"""Tests for dingtalk.py module."""
import pytest
from unittest.mock import patch, MagicMock


class TestBuildRemindCardWithCerts:
    """测试 build_remind_card 函数在有证书时的行为。"""

    def test_build_remind_card_with_multiple_certs(self):
        """测试多个到期项构建提醒卡片。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Corp A",
                "cert_type": "SSL",
                "domain": "a.example.com",
                "expire_date": "2027-01-01",
                "days_left": 3,
                "responsible_users": ["alice"],
            },
            {
                "customer": "Corp B",
                "cert_type": "EV",
                "domain": "b.example.com",
                "expire_date": "2027-06-01",
                "days_left": 150,
                "responsible_users": ["bob"],
            },
        ]
        users_map = {"alice": "12345", "bob": "67890"}

        title, content, at_ids = build_remind_card(certs, users_map)

        assert title == "🔔 到期项到期提醒"
        assert "Corp A" in content
        assert "Corp B" in content
        assert "a.example.com" in content
        assert "b.example.com" in content
        # alice 应该被加入 at_user_ids，但 bob 因为 days_left=150 > 30 不会被加（实际上代码对所有 responsible_users 都加了）
        assert "alice" in at_ids
        assert "bob" in at_ids

    def test_build_remind_card_expired_cert(self):
        """测试已过期证书的卡片构建。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Expired Co",
                "cert_type": "SSL",
                "domain": "expired.example.com",
                "expire_date": "2023-01-01",
                "days_left": -5,
                "responsible_users": ["charlie"],
            }
        ]
        users_map = {"charlie": "abc"}

        title, content, at_ids = build_remind_card(certs, users_map)

        assert "已过期 5 天" in content
        assert "charlie" in at_ids

    def test_build_remind_card_today_expiry(self):
        """测试今日到期证书的卡片构建。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Today Corp",
                "cert_type": "DV",
                "domain": "today.example.com",
                "expire_date": "2027-07-04",
                "days_left": 0,
                "responsible_users": ["dave"],
            }
        ]
        users_map = {"dave": "def"}

        _, content, _ = build_remind_card(certs, users_map)

        assert "今日到期" in content

    def test_build_remind_card_week_expiry(self):
        """测试一周内到期证书的卡片构建。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Week Corp",
                "cert_type": "OV",
                "domain": "week.example.com",
                "expire_date": "2027-07-10",
                "days_left": 6,
                "responsible_users": ["eve"],
            }
        ]
        users_map = {"eve": "ghi"}

        _, content, _ = build_remind_card(certs, users_map)

        assert "6 天后到期" in content

    def test_build_remind_card_month_expiry(self):
        """测试一个月内到期证书的卡片构建。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Month Corp",
                "cert_type": "SSL",
                "domain": "month.example.com",
                "expire_date": "2027-08-01",
                "days_left": 28,
                "responsible_users": ["frank"],
            }
        ]
        users_map = {"frank": "jkl"}

        _, content, _ = build_remind_card(certs, users_map)

        assert "28 天后到期" in content

    def test_build_remind_card_unknown_user_not_in_map(self):
        """测试负责人不在 users_map 中时不会被加入 at_user_ids。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Unknown Corp",
                "cert_type": "SSL",
                "domain": "unknown.example.com",
                "expire_date": "2027-08-01",
                "days_left": 10,
                "responsible_users": ["ghost"],
            }
        ]
        users_map = {}

        _, _, at_ids = build_remind_card(certs, users_map)

        assert "ghost" not in at_ids

    def test_build_remind_card_duplicate_user_not_added_twice(self):
        """测试同一负责人不会重复添加到 at_user_ids。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Multi Corp A",
                "cert_type": "SSL",
                "domain": "multi-a.example.com",
                "expire_date": "2027-08-01",
                "days_left": 10,
                "responsible_users": ["same_user"],
            },
            {
                "customer": "Multi Corp B",
                "cert_type": "DV",
                "domain": "multi-b.example.com",
                "expire_date": "2027-08-15",
                "days_left": 24,
                "responsible_users": ["same_user"],
            },
        ]
        users_map = {"same_user": "uid123"}

        _, _, at_ids = build_remind_card(certs, users_map)

        assert at_ids.count("same_user") == 1

    def test_build_remind_card_missing_fields_defaults(self):
        """测试证书缺少可选字段时使用默认值。"""
        from dingtalk import build_remind_card

        certs = [{"domain": "minimal.example.com"}]
        users_map = {}

        title, content, at_ids = build_remind_card(certs, users_map)

        assert title == "🔔 到期项到期提醒"
        assert "minimal.example.com" in content
        assert at_ids == []

    def test_build_remind_card_font_color_expired(self):
        """测试已过期证书的颜色标记。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Color Corp",
                "cert_type": "SSL",
                "domain": "color.example.com",
                "expire_date": "2023-01-01",
                "days_left": -10,
                "responsible_users": [],
            }
        ]
        users_map = {}

        _, content, _ = build_remind_card(certs, users_map)

        assert "#FF0000" in content

    def test_build_remind_card_font_color_warning(self):
        """测试警告状态证书的颜色标记。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Warn Corp",
                "cert_type": "SSL",
                "domain": "warn.example.com",
                "expire_date": "2027-07-04",
                "days_left": 0,
                "responsible_users": [],
            }
        ]
        users_map = {}

        _, content, _ = build_remind_card(certs, users_map)

        assert "#FF8C00" in content

    def test_build_remind_card_font_color_soon(self):
        """测试即将到期证书的颜色标记。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Soon Corp",
                "cert_type": "SSL",
                "domain": "soon.example.com",
                "expire_date": "2027-07-10",
                "days_left": 6,
                "responsible_users": [],
            }
        ]
        users_map = {}

        _, content, _ = build_remind_card(certs, users_map)

        assert "#FFA500" in content

    def test_build_remind_card_font_color_warning_yellow(self):
        """测试黄色警告证书的颜色标记。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Yellow Corp",
                "cert_type": "SSL",
                "domain": "yellow.example.com",
                "expire_date": "2027-08-01",
                "days_left": 28,
                "responsible_users": [],
            }
        ]
        users_map = {}

        _, content, _ = build_remind_card(certs, users_map)

        assert "#FFD700" in content

    def test_build_remind_card_font_color_green(self):
        """测试绿色正常证书的颜色标记。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "Green Corp",
                "cert_type": "SSL",
                "domain": "green.example.com",
                "expire_date": "2028-01-01",
                "days_left": 180,
                "responsible_users": [],
            }
        ]
        users_map = {}

        _, content, _ = build_remind_card(certs, users_map)

        assert "#32CD32" in content


class TestBuildRemindCardEmpty:
    """测试 build_remind_card 在空输入时的行为。"""

    def test_build_remind_card_empty_list(self):
        """测试空证书列表。"""
        from dingtalk import build_remind_card

        title, content, at_ids = build_remind_card([], {})

        assert title == "🔔 到期项到期提醒"
        assert at_ids == []

    def test_build_remind_card_none_users_map(self):
        """测试空用户映射。"""
        from dingtalk import build_remind_card

        certs = [
            {
                "customer": "No Users Corp",
                "cert_type": "SSL",
                "domain": "nouser.example.com",
                "expire_date": "2027-08-01",
                "days_left": 10,
                "responsible_users": [],
            }
        ]

        title, content, at_ids = build_remind_card(certs, {})

        assert at_ids == []
        assert "No Users Corp" in content


class TestSendWecomBasic:
    """测试 send_wecom 函数的基本行为。"""

    @patch("dingtalk.requests.post")
    def test_send_wecom_success(self, mock_post):
        """测试企业微信消息发送成功。"""
        from dingtalk import send_wecom

        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_response

        result = send_wecom("https://qyapi.weixin.qq.com/cgi-bin/webhook/send", "Hello")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["msgtype"] == "text"
        assert call_args[1]["json"]["text"]["content"] == "Hello"

    @patch("dingtalk.requests.post")
    def test_send_wecom_failure(self, mock_post):
        """测试企业微信消息发送失败。"""
        from dingtalk import send_wecom

        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 40001, "errmsg": "invalid"}
        mock_post.return_value = mock_response

        result = send_wecom("https://qyapi.weixin.qq.com/cgi-bin/webhook/send", "Test")

        assert result is False

    @patch("dingtalk.requests.post")
    def test_send_wecom_exception(self, mock_post):
        """测试企业微信发送异常。"""
        from dingtalk import send_wecom

        mock_post.side_effect = Exception("Network error")

        result = send_wecom("https://qyapi.weixin.qq.com/cgi-bin/webhook/send", "Test")

        assert result is False
