# -*- coding: utf-8 -*-
"""认证层单元测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import load_users, save_users, verify_user, do_lock_user, is_user_locked, reset_failed_attempts


def test_lock_user(temp_data_dir):
    """用户锁定"""
    users = [{"username": "baduser", "password": "Test1234", "name": "Bad User", "role": "user"}]
    save_users(users)
    
    assert is_user_locked("baduser") is False
    do_lock_user("baduser")
    assert is_user_locked("baduser") is True
    reset_failed_attempts("baduser")
    assert is_user_locked("baduser") is False


def test_verify_migrated_password(temp_data_dir):
    """密码哈希迁移"""
    users = [{"username": "admin", "password": "Admin123", "name": "Admin", "role": "admin"}]
    save_users(users)
    loaded = load_users()
    # 密码应该被自动迁移为哈希
    assert len(loaded[0]["password"]) > 50
    assert verify_user("admin", "Admin123") is True
