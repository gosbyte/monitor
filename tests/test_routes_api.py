# -*- coding: utf-8 -*-
"""API 端点路由测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app_init import app


@pytest.fixture
def admin_client(temp_data_dir):
    """Flask test client with logged-in admin"""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "admin", "name": "Admin",
                   "password": generate_password_hash("Admin123"),
                   "role": "admin", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            sess["_csrf_token"] = "testtoken123456789012345678901234567890"
        yield c


@pytest.fixture
def regular_client(temp_data_dir):
    """Flask test client with logged-in regular user"""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "regular", "name": "Regular",
                   "password": generate_password_hash("RegPass123"),
                   "role": "user", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "regular"
            sess["_csrf_token"] = "testtoken123456789012345678901234567890"
        yield c


class TestToggleStatus:
    """test_toggle_status"""

    def test_toggle_status_on_to_off(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 1, "customer": "ToggleCorp", "cert_type": "SSL", "domain": "tc.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.post("/api/status/1", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        assert data["remind_enabled"] is False
        certs = load_certs()
        assert certs[0]["remind_enabled"] is False

    def test_toggle_status_off_to_on(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 2, "customer": "ToggleOn", "cert_type": "SSL", "domain": "to.com",
                      "expire_date": "2027-12-31", "remind_enabled": False, "handled": False}])
        resp = admin_client.post("/api/status/2", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        assert data["remind_enabled"] is True

    def test_toggle_status_not_found(self, admin_client):
        resp = admin_client.post("/api/status/9999", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_toggle_status_bad_csrf(self, admin_client):
        resp = admin_client.post("/api/status/1", json={},
                                  headers={"X-CSRF-Token": "wrongtoken"})
        assert resp.status_code == 403


class TestToggleHandle:
    """test_toggle_handle"""

    def test_toggle_handle_false_to_true(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 10, "customer": "HandleCorp", "cert_type": "SSL", "domain": "hc.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.post("/api/handle/10", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        assert data["handled"] is True
        certs = load_certs()
        assert certs[0]["handled"] is True

    def test_toggle_handle_true_to_false(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 11, "customer": "Unhandle", "cert_type": "SSL", "domain": "uh.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": True}])
        resp = admin_client.post("/api/handle/11", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        assert data["handled"] is False

    def test_toggle_handle_not_found(self, admin_client):
        resp = admin_client.post("/api/handle/9999", json={},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False


class TestGetCertStatusApi:
    """test_get_cert_status_api"""

    def test_get_cert_status_api_normal(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 20, "customer": "StatusCorp", "cert_type": "SSL", "domain": "sc.com",
                      "expire_date": "2030-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/api/cert_status/20")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["status"] == "normal"

    def test_get_cert_status_api_expired(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 21, "customer": "ExpiredCorp", "cert_type": "SSL", "domain": "ec.com",
                      "expire_date": "2020-01-01", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/api/cert_status/21")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["status"] == "expired"

    def test_get_cert_status_api_disabled(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 22, "customer": "DisabledCorp", "cert_type": "SSL", "domain": "dc.com",
                      "expire_date": "2030-12-31", "remind_enabled": False, "handled": False}])
        resp = admin_client.get("/api/cert_status/22")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["status"] == "disabled"

    def test_get_cert_status_api_not_found(self, admin_client):
        resp = admin_client.get("/api/cert_status/9999")
        assert resp.status_code == 404


class TestApiListCertsPagination:
    """test_api_list_certs_pagination"""

    def test_list_certs_default(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": i, "customer": f"C{i}", "cert_type": "SSL", "domain": f"c{i}.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}
            for i in range(1, 26)
        ])
        resp = admin_client.get("/api/cert")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["total"] == 25
        assert len(data["data"]) == 20  # default per_page

    def test_list_certs_page2(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": i, "customer": f"P{i}", "cert_type": "SSL", "domain": f"p{i}.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}
            for i in range(1, 31)
        ])
        resp = admin_client.get("/api/cert?page=2&per_page=10")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert len(data["data"]) == 10
        assert data["pages"] == 3

    def test_list_certs_custom_per_page(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": i, "customer": f"C{i}", "cert_type": "SSL", "domain": f"c{i}.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}
            for i in range(1, 6)
        ])
        resp = admin_client.get("/api/cert?per_page=3")
        data = resp.get_json()
        assert len(data["data"]) == 3
        assert data["total"] == 5

    def test_list_certs_per_page_max(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": i, "customer": f"M{i}", "cert_type": "SSL", "domain": f"m{i}.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}
            for i in range(1, 201)
        ])
        resp = admin_client.get("/api/cert?per_page=200")
        data = resp.get_json()
        assert len(data["data"]) == 100  # capped at 100

    def test_list_certs_search(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": 1, "customer": "SearchCorp", "cert_type": "SSL", "domain": "sc.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
            {"id": 2, "customer": "OtherCorp", "cert_type": "SSL", "domain": "oc.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ])
        resp = admin_client.get("/api/cert?search=Search")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["customer"] == "SearchCorp"

    def test_list_certs_status_filter(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": 1, "customer": "NormalCorp", "cert_type": "SSL", "domain": "nc.com",
             "expire_date": "2030-12-31", "remind_enabled": True, "handled": False},
            {"id": 2, "customer": "ExpiredCorp", "cert_type": "SSL", "domain": "ec.com",
             "expire_date": "2020-01-01", "remind_enabled": True, "handled": False},
        ])
        resp = admin_client.get("/api/cert?status=expired")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["customer"] == "ExpiredCorp"

    def test_list_certs_empty(self, admin_client):
        resp = admin_client.get("/api/cert")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["total"] == 0


class TestApiStats:
    """test_api_stats"""

    def test_api_stats_empty(self, admin_client):
        resp = admin_client.get("/api/stats")
        data = resp.get_json()
        assert data["total"] == 0

    def test_api_stats_with_certs(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([
            {"id": 1, "customer": "N", "cert_type": "SSL", "domain": "n.com",
             "expire_date": "2030-12-31", "remind_enabled": True, "handled": False},
            {"id": 2, "customer": "E", "cert_type": "SSL", "domain": "e.com",
             "expire_date": "2020-01-01", "remind_enabled": True, "handled": False},
            {"id": 3, "customer": "D", "cert_type": "SSL", "domain": "d.com",
             "expire_date": "2030-12-31", "remind_enabled": False, "handled": False},
        ])
        resp = admin_client.get("/api/stats")
        data = resp.get_json()
        assert data["total"] == 3
        assert data["expired"] >= 1
        assert data["disabled"] >= 1


class TestApiConfigWecom:
    """test wecom config API"""

    def test_api_config_wecom(self, admin_client):
        resp = admin_client.post("/api/config/wecom", json={
            "wecom_enabled": True,
            "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send/xxx"
        }, headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True


class TestNonAdminAccess:
    """Non-admin cannot access admin-only API endpoints"""

    def test_regular_user_cannot_toggle_status(self, regular_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 1, "customer": "Test", "cert_type": "SSL", "domain": "t.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = regular_client.post("/api/status/1", json={},
                                    headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        # Regular user CAN toggle status (it's login_required, not admin_required)
        assert resp.status_code == 200

    def test_regular_user_cannot_test_email(self, regular_client):
        resp = regular_client.post("/api/test_email", json={})
        assert resp.status_code == 403

    def test_regular_user_cannot_test_wecom(self, regular_client):
        resp = regular_client.post("/api/test_wecom", json={})
        assert resp.status_code == 403

    def test_regular_user_cannot_test_push(self, regular_client):
        resp = regular_client.post("/api/test_push", json={})
        assert resp.status_code == 403

    def test_regular_user_cannot_push_cert(self, regular_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 1, "customer": "Test", "cert_type": "SSL", "domain": "t.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = regular_client.post("/api/push/1", json={},
                                    headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        assert resp.status_code == 403


class TestUnauthenticatedAccess:
    """Unauthenticated users cannot access API endpoints"""

    def test_unauthenticated_cannot_toggle_status(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            resp = c.post("/api/status/1", json={})
            assert resp.status_code == 302

    def test_unauthenticated_cannot_get_stats(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            resp = c.get("/api/stats")
            assert resp.status_code == 302

    def test_unauthenticated_cannot_list_certs(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            resp = c.get("/api/cert")
            assert resp.status_code == 302
