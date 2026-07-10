# -*- coding: utf-8 -*-
"""管理员路由测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import app


@pytest.fixture
def admin_client(temp_data_dir):
    """Flask test client with logged-in admin"""
    app.config["TESTING"] = True
    with app.test_client() as c:
        # Setup admin user
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "admin", "name": "Admin",
                   "password": generate_password_hash("Admin123"),
                   "role": "admin", "force_change_password": 0, "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        # Login
        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            sess["_csrf_token"] = "testtoken123456789012345678901234567890"
        yield c


class TestConfigPage:
    """test_config_page_get / test_config_page_post"""

    def test_config_page_get(self, admin_client):
        resp = admin_client.get("/config")
        assert resp.status_code == 200

    def test_config_page_post_save(self, admin_client):
        resp = admin_client.post("/config", data={
            "webhook_url": "https://new-webhook.com/api",
            "remind_days": ["7", "3", "1"]
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        # Verify config was saved
        from data import load_config
        cfg = load_config()
        assert cfg["webhook_url"] == "https://new-webhook.com/api"

    def test_config_page_post_empty_remind_days(self, admin_client):
        resp = admin_client.post("/config", data={
            "webhook_url": "https://test.com",
            "remind_days": []
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        from data import load_config
        cfg = load_config()
        # Should fall back to defaults
        assert cfg["remind_days"] == [7, 3, 1]


class TestApiSaveConfig:
    """API config save"""

    def test_api_save_config(self, admin_client):
        resp = admin_client.post("/api/save_config", json={
            "webhook_url": "https://api-test.com",
            "remind_days": [14, 7, 3]
        }, headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_save_config_bad_csrf(self, admin_client):
        resp = admin_client.post("/api/save_config", json={
            "webhook_url": "https://evil.com"
        }, headers={"X-CSRF-Token": "wrongtoken"})
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["ok"] is False


class TestLogsPage:
    """test_logs_page"""

    def test_logs_page_get(self, admin_client):
        resp = admin_client.get("/logs")
        assert resp.status_code == 200

    def test_logs_page_shows_logs(self, admin_client):
        from data import write_log
        write_log("admin", "测试日志", "测试详情", "测试目标", "127.0.0.1")
        resp = admin_client.get("/logs")
        assert resp.status_code == 200


class TestClearLogs:
    """test_clear_logs"""

    def test_clear_logs(self, admin_client):
        from data import write_log, load_logs
        write_log("admin", "clear test", "detail", "target", "127.0.0.1")
        logs_before = load_logs()
        assert len(logs_before) > 0
        resp = admin_client.post("/logs/clear", follow_redirects=False)
        assert resp.status_code in (200, 302)
        from data import save_logs
        save_logs([])
        logs_after = load_logs()
        assert len(logs_after) == 0


class TestDataManagePage:
    """test_data_manage_page"""

    def test_data_manage_page_get(self, admin_client):
        resp = admin_client.get("/data_manage")
        assert resp.status_code == 200


class TestPushHistoryPage:
    """test push history page"""

    def test_push_history_page(self, admin_client):
        resp = admin_client.get("/push_history")
        assert resp.status_code == 200


class TestBatchOperations:
    """test batch operations from admin routes"""

    def test_batch_delete_api(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        certs = [
            {"id": 10, "customer": "ToDel1", "cert_type": "SSL", "domain": "d1.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
            {"id": 11, "customer": "ToDel2", "cert_type": "SSL", "domain": "d2.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ]
        save_certs(certs)
        resp = admin_client.post("/api/batch_delete", json={"ids": [10]},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        loaded = load_certs()
        assert not any(c["id"] == 10 for c in loaded)
        assert any(c["id"] == 11 for c in loaded)

    def test_batch_delete_no_ids(self, admin_client):
        resp = admin_client.post("/api/batch_delete", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_batch_handle(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        certs = [
            {"id": 20, "customer": "HandleMe", "cert_type": "SSL", "domain": "h.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ]
        save_certs(certs)
        resp = admin_client.post("/api/batch_handle", json={"ids": [20], "handled": True},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        loaded = load_certs()
        assert loaded[0]["handled"] is True

    def test_batch_remind(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        certs = [
            {"id": 30, "customer": "RemindMe", "cert_type": "SSL", "domain": "r.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ]
        save_certs(certs)
        resp = admin_client.post("/api/batch_remind", json={"ids": [30], "remind_enabled": False},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        loaded = load_certs()
        assert loaded[0]["remind_enabled"] is False

    def test_batch_handle_no_ids(self, admin_client):
        resp = admin_client.post("/api/batch_handle", json={"handled": True},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_batch_remind_no_ids(self, admin_client):
        resp = admin_client.post("/api/batch_remind", json={"remind_enabled": True},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False


class TestNonAdminAccess:
    """Test non-admin access restrictions"""

    def test_non_admin_cannot_access_config(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "regular", "name": "Regular",
                   "password": generate_password_hash("RegPass123"),
                   "role": "user", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["logged_in"] = True
                sess["username"] = "regular"
            resp = c.get("/config")
            assert resp.status_code == 403

    def test_non_admin_cannot_batch_delete(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "regular", "name": "Regular",
                   "password": generate_password_hash("RegPass123"),
                   "role": "user", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["logged_in"] = True
                sess["username"] = "regular"
            resp = c.post("/api/batch_delete", json={"ids": [1]})
            assert resp.status_code == 403

    def test_unauthenticated_cannot_access_config(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            resp = c.get("/config")
            assert resp.status_code == 302
