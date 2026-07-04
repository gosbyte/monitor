# -*- coding: utf-8 -*-
"""数据工具函数单元测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import validate_password, calc_days_left, get_cert_status


class TestValidatePassword:
    """test_validate_password_strong / test_validate_password_weak"""

    def test_strong_password(self):
        ok, msg = validate_password("Str0ngP@ssw0rd!")[:2]
        assert ok is True
        assert "强度" in msg

    def test_too_short(self):
        ok, msg = validate_password("Ab1")[:2]
        assert ok is False
        assert "长度" in msg

    def test_no_uppercase(self):
        ok, msg = validate_password("lowercase12345")[:2]
        assert ok is False
        assert "大写字母" in msg

    def test_no_lowercase(self):
        ok, msg = validate_password("UPPERCASE12345")[:2]
        assert ok is False
        assert "小写字母" in msg

    def test_no_digits(self):
        ok, msg = validate_password("Abcdefghijklmnop")[:2]
        assert ok is False
        assert "数字" in msg

    def test_exact_twelve_chars(self):
        ok, msg = validate_password("Abcdefghijk1")[:2]
        assert ok is True

    def test_empty_password(self):
        ok, msg = validate_password("")[:2]
        assert ok is False

    def test_special_chars_allowed(self):
        ok, msg = validate_password("Abcdefg1!xyz")[:2]
        assert ok is True

    def test_common_password_rejected(self):
        ok, msg = validate_password("password123456")[:2]
        assert ok is False

    def test_admin_password_rejected(self):
        ok, msg = validate_password("admin1234567")[:2]
        assert ok is False

    def test_simple_password_rejected(self):
        ok, msg = validate_password("123456789012")[:2]
        assert ok is False


class TestCalcDaysLeft:
    """test_calc_days_left_future / test_calc_days_left_past"""

    def test_far_future(self):
        days = calc_days_left("2030-12-31")
        assert days > 1000

    def test_near_future(self):
        days = calc_days_left("2027-07-04")
        assert days >= 364

    def test_yesterday(self):
        days = calc_days_left("2025-07-03")
        assert days < 0

    def test_past_date(self):
        days = calc_days_left("2020-01-01")
        assert days < -1800

    def test_invalid_format_returns_negative(self):
        days = calc_days_left("not-a-date")
        assert days == -999

    def test_empty_string(self):
        days = calc_days_left("")
        assert days == -999

    def test_datetime_format(self):
        days = calc_days_left("2027-12-31T14:30")
        assert days > 300

    def test_datetime_space_format(self):
        days = calc_days_left("2027-12-31 14:30")
        assert days > 300


class TestGetCertStatus:
    """test_get_cert_status_various"""

    def test_normal_status(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert) == "normal"

    def test_expired_status(self):
        cert = {"expire_date": "2020-01-01", "remind_enabled": True}
        assert get_cert_status(cert) == "expired"

    def test_expiring_within_7_days(self):
        cert = {"expire_date": "2025-07-01", "remind_enabled": True}
        status = get_cert_status(cert)
        assert status in ("expiring", "expired")

    def test_disabled_status(self):
        cert = {"expire_date": "2020-01-01", "remind_enabled": False}
        assert get_cert_status(cert) == "disabled"

    def test_disabled_not_expired(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": False}
        assert get_cert_status(cert) == "disabled"

    def test_custom_days_left(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert, days_left=1000) == "normal"

    def test_custom_days_left_expired(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert, days_left=-10) == "expired"

    def test_custom_days_left_expiring(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert, days_left=5) == "expiring"

    def test_explicit_7_days_is_expiring(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert, days_left=7) == "expiring"

    def test_explicit_8_days_is_normal(self):
        cert = {"expire_date": "2030-12-31", "remind_enabled": True}
        assert get_cert_status(cert, days_left=8) == "normal"

    def test_empty_expire_date(self):
        cert = {"expire_date": "", "remind_enabled": True}
        assert get_cert_status(cert) == "expired"
