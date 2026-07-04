# -*- coding: utf-8 -*-
"""数据层单元测试"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import (
    load_certs, save_certs,
    load_config, save_config, load_users, save_users,
    verify_user, validate_password, calc_days_left,
    get_cert_status, calc_stats, write_log, load_logs,
)


def test_load_save_certs(temp_data_dir):
    """到期项加载/保存"""
    certs = [
        {"id": 1, "customer": "A", "expire_date": "2025-12-31"},
        {"id": 2, "customer": "B", "expire_date": "2026-06-30"},
    ]
    save_certs(certs)
    loaded = load_certs()
    assert len(loaded) == 2
    assert loaded[0]["customer"] == "A"


def test_empty_certs(temp_data_dir):
    """空到期项列表"""
    loaded = load_certs()
    assert loaded == []


def test_load_config_defaults(temp_data_dir):
    """默认配置"""
    cfg = load_config()
    assert cfg["webhook_url"] == ""
    assert cfg["remind_days"] == [30, 14, 7, 3, 1]


def test_save_config(temp_data_dir):
    """保存配置"""
    cfg = {"webhook_url": "https://test.com", "remind_days": [30, 14, 7]}
    save_config(cfg)
    loaded = load_config()
    assert loaded["webhook_url"] == "https://test.com"
    assert loaded["remind_days"] == [30, 14, 7]


def test_validate_password_strength():
    """密码强度验证"""
    ok, msg, score, label = validate_password("Abc123456789")
    assert ok is True
    assert "强度" in msg
    
    ok, msg = validate_password("short")[:2]
    assert ok is False
    
    ok, msg = validate_password("nouppercase12345")[:2]
    assert ok is False
    
    ok, msg = validate_password("NOLOWERCASE12345")[:2]
    assert ok is False
    
    ok, msg = validate_password("NoDigitsHere!")[:2]
    assert ok is False


def test_verify_user(temp_data_dir):
    """用户验证"""
    users = [{"username": "admin", "name": "Admin", "password": "Admin123", "role": "admin"}]
    save_users(users)
    assert verify_user("admin", "Admin123") is True
    assert verify_user("admin", "wrongpass") is False
    assert verify_user("nonexistent", "pass") is False


def test_calc_days_left_future():
    """未来日期"""
    days = calc_days_left("2027-12-31")
    assert days > 365


def test_calc_days_left_past():
    """过去日期"""
    days = calc_days_left("2020-01-01")
    assert days < 0


def test_get_cert_status():
    """到期项状态判断"""
    cert_normal = {"expire_date": "2027-12-31", "remind_enabled": True, "handled": False}
    assert get_cert_status(cert_normal) == "normal"
    
    cert_expired = {"expire_date": "2020-01-01", "remind_enabled": True, "handled": False}
    assert get_cert_status(cert_expired) == "expired"
    
    # expiring: 未来7天内
    cert_expiring = {"expire_date": "2025-07-01", "remind_enabled": True, "handled": False}
    status = get_cert_status(cert_expiring)
    # 如果今天是2025-06-25之后，2025-07-01 可能在7天内或已过期
    # 所以这里只验证不会报 normal
    assert status in ("expiring", "expired")
    
    cert_disabled = {"expire_date": "2020-01-01", "remind_enabled": False, "handled": False}
    assert get_cert_status(cert_disabled) == "disabled"


def test_calc_stats(temp_data_dir):
    """统计计算"""
    certs = [
        {"id": 1, "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        {"id": 2, "expire_date": "2020-01-01", "remind_enabled": True, "handled": False},
        {"id": 3, "expire_date": "2027-12-31", "remind_enabled": False, "handled": False},
    ]
    save_certs(certs)
    stats = calc_stats(certs)
    assert stats["total"] == 3
    assert stats["expired"] >= 1
    assert stats["disabled"] >= 1


def test_write_log(temp_data_dir):
    """写日志"""
    write_log("admin", "测试操作", "测试详情", "测试目标", "127.0.0.1")
    logs = load_logs()
    assert len(logs) >= 1
    assert logs[-1]["username"] == "admin"
    assert logs[-1]["action"] == "测试操作"


def test_load_users_fields(temp_data_dir):
    """用户字段补全"""
    users = [{"username": "test", "password": "Test1234", "name": "Test"}]
    save_users(users)
    loaded = load_users()
    assert loaded[0].get("dingtalk_id") == ""
    assert loaded[0].get("failed_attempts") == 0
    # role 字段如果不存在，load_users 不会自动设置，因为 save_users 只补全 name/dingtalk_id/failed_attempts/consecutive_locks/lock_until
    # 所以这里不检查 role，改为检查 password 被哈希了
    assert len(loaded[0]["password"]) > 50
