# -*- coding: utf-8 -*-
"""SQLite 数据层单元测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import init_db, db_load_certs, db_save_cert, db_delete_cert, db_get_cert, db_calc_stats


def test_db_init(temp_data_dir):
    """数据库初始化"""
    init_db()
    db_path = os.path.join(str(temp_data_dir), "monitor.db")
    assert os.path.exists(db_path)


def test_db_crud(temp_data_dir):
    """SQLite CRUD"""
    init_db()
    
    cert = {
        "id": 1,
        "customer": "Test Corp",
        "cert_type": "SSL",
        "domain": "test.example.com",
        "expire_date": "2027-12-31",
        "note": "Test",
        "remind_enabled": True,
        "handled": False,
        "responsible_users": ["admin"],
        "created_by": "admin",
        "created_at": "2024-01-01",
    }
    db_save_cert(cert)
    
    loaded = db_load_certs()
    assert len(loaded) == 1
    assert loaded[0]["customer"] == "Test Corp"
    
    # 更新
    cert["customer"] = "Updated Corp"
    cert["id"] = loaded[0]["id"]
    db_save_cert(cert)
    loaded = db_load_certs()
    assert loaded[0]["customer"] == "Updated Corp"
    
    # 删除
    db_delete_cert(loaded[0]["id"])
    assert len(db_load_certs()) == 0


def test_db_get_cert(temp_data_dir):
    """获取单条证书"""
    init_db()
    cert = {"id": 1, "customer": "Test", "expire_date": "2027-12-31"}
    db_save_cert(cert)
    result = db_get_cert(1)
    assert result is not None
    assert result["customer"] == "Test"
    assert db_get_cert(999) is None


def test_db_stats(temp_data_dir):
    """统计"""
    init_db()
    cert = {"id": 1, "customer": "Test", "expire_date": "2027-12-31"}
    db_save_cert(cert)
    stats = db_calc_stats()
    assert stats["total"] == 1
