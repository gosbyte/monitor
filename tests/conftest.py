# -*- coding: utf-8 -*-
"""Pytest 配置"""
import os
import sys
import tempfile
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import (
    DATA_DIR, DATA_FILE, CONFIG_FILE, USERS_FILE, LOGS_FILE,
    load_certs, save_certs, load_config, save_config,
    load_users, save_users, verify_user, validate_password,
    calc_days_left, get_cert_status, calc_stats,
    load_logs, save_logs, write_log,
)
import db


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    os.environ["DATA_DIR"] = str(tmp_path)
    # 重置 data.py 模块中的路径常量
    import data
    data.BASE_DIR = str(tmp_path)
    data.DATA_DIR = str(tmp_path)
    data.DATA_FILE = str(tmp_path / "certs.json")
    data.CONFIG_FILE = str(tmp_path / "config.json")
    data.USERS_FILE = str(tmp_path / "users.json")
    data.LOGS_FILE = str(tmp_path / "logs.json")
    data.SECRET_KEY_FILE = str(tmp_path / ".secret_key")
    data._users_cache = {"data": None, "mtime": 0}
    # 同时更新 db 模块的路径
    import db
    db.DB_PATH = str(tmp_path / "monitor.db")
    yield tmp_path
    del os.environ["DATA_DIR"]


@pytest.fixture
def sample_cert(temp_data_dir):
    """创建一个示例证书"""
    cert = {
        "id": 1,
        "customer": "Test Corp",
        "cert_type": "SSL",
        "domain": "test.example.com",
        "expire_date": "2027-12-31",
        "note": "Test certificate",
        "remind_enabled": True,
        "handled": False,
        "responsible_users": ["admin"],
        "created_by": "admin",
        "created_at": "2024-01-01 10:00",
    }
    save_certs([cert])
    return cert


@pytest.fixture
def sample_user(temp_data_dir):
    """创建一个示例用户"""
    user = {
        "username": "testuser",
        "name": "Test User",
        "password": "TestPass123",  # 会被自动哈希
        "dingtalk_id": "",
        "role": "user",
        "failed_attempts": 0,
        "consecutive_locks": 0,
        "lock_until": None,
    }
    save_users([user])
    return user
