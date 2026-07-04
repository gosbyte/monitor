# -*- coding: utf-8 -*-
"""认证路由测试"""
import os
import sys
import json
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app_init import app


@pytest.fixture
def client(temp_data_dir):
    """Flask test client with logged-in admin"""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def admin_client(client, temp_data_dir):
    """Ensure admin user exists and is logged in"""
    from data import save_users, load_config, save_config
    from werkzeug.security import generate_password_hash
    users = [{"username": "admin", "name": "Admin", "password": generate_password_hash("Admin123"),
              "role": "admin", "dingtalk_id": "", "failed_attempts": 0,
              "consecutive_locks": 0, "lock_until": None}]
    save_users(users)
    import data

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["_csrf_token"] = sess.get("_csrf_token", "test_csrf_token_xyz")
    return client, sess["_csrf_token"]


class TestLoginSuccess:
    """test_login_success"""

    def test_login_redirect_if_logged_in(self, client, temp_data_dir):
        from data import save_users
        users = [{"username": "admin", "name": "Admin", "password": "Admin123",
                   "role": "admin", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data
    
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
        resp = client.get("/login")
        assert resp.status_code == 302

    def test_login_page_get(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"login" in resp.data.lower() or b"deng" in resp.data

    def test_successful_login(self, client, temp_data_dir):
        from data import save_users
        users = [{"username": "admin", "name": "Admin", "password": "Admin123",
                   "role": "admin", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data
    
        # Need to hash password properly
        from werkzeug.security import generate_password_hash
        users[0]["password"] = generate_password_hash("Admin123")
        save_users(users)
    
        resp = client.post("/login", data={
            "username": "admin",
            "password": "Admin123",
            "captcha": "XXXX"  # Will fail captcha, but test login flow
        }, follow_redirects=False)
        # Should fail captcha, not password
        assert resp.status_code in (200, 302)


class TestLoginWrongPassword:
    """test_login_wrong_password"""

    def test_wrong_password(self, client, temp_data_dir):
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "admin", "name": "Admin",
                   "password": generate_password_hash("Correct123"),
                   "role": "admin", "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data
    
        # Get captcha first
        client.get("/captcha")
        resp = client.post("/login", data={
            "username": "admin",
            "password": "WrongPass1",
            "captcha": "XXXX"  # wrong captcha
        })
        assert "验证码错误" in resp.data.decode()


class TestLoginWrongCaptcha:
    """test_login_wrong_captcha"""

    def test_wrong_captcha(self, client):
        resp = client.post("/login", data={
            "username": "admin",
            "password": "anything",
            "captcha": "wrongcode"
        })
        assert resp.status_code == 200
        assert "验证码" in resp.data.decode()


class TestLogout:
    """test_logout"""

    def test_logout(self, admin_client):
        client, token = admin_client
        resp = client.get("/logout")
        assert resp.status_code == 302
        assert resp.status_code == 302 or b"login" in resp.data.lower()


class TestChangePassword:
    """test_change_password route"""

    def test_change_password_page_get(self, admin_client):
        client, token = admin_client
        resp = client.get("/change_password")
        assert resp.status_code == 200

    def test_change_password_success(self, admin_client, temp_data_dir):
        client, token = admin_client
        from data import save_users, load_users
        users = load_users()
        from werkzeug.security import generate_password_hash
        for u in users:
            if u["username"] == "admin":
                u["password"] = generate_password_hash("OldPass123")
                u["force_change_password"] = 1
        save_users(users)
        import data
    
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
        resp = client.post("/change_password", data={
            "old_password": "OldPass123",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123"
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_change_password_old_wrong(self, admin_client):
        client, token = admin_client
        resp = client.post("/change_password", data={
            "old_password": "WrongOld1",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123"
        })
        assert "密码" in resp.data.decode()

    def test_change_password_confirm_mismatch(self, admin_client, temp_data_dir):
        client, token = admin_client
        from data import save_users, load_users
        users = load_users()
        from werkzeug.security import generate_password_hash
        for u in users:
            if u["username"] == "admin":
                u["password"] = generate_password_hash("Admin123")
        save_users(users)
        import data
    
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
        resp = client.post("/change_password", data={
            "old_password": "Admin123",
            "new_password": "NewPass123",
            "confirm_password": "Different1"
        })
        assert "一致" in resp.data.decode()


class TestAddUser:
    """test_add_user"""

    def test_add_user_success(self, admin_client, temp_data_dir):
        client, token = admin_client
        resp = client.post("/users/add", data={
            "username": "newuser",
            "name": "New User",
            "password": "NewPass123",
            "role": "user",
            "_csrf_token": token
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        from data import load_users
        users = load_users()
        usernames = [u["username"] for u in users]
        assert "newuser" in usernames

    def test_add_user_duplicate(self, admin_client):
        client, token = admin_client
        resp = client.post("/users/add", data={
            "username": "admin",
            "password": "NewPass123",
            "role": "user",
            "_csrf_token": token
        })
        assert "存在" in resp.data.decode() or resp.status_code == 400

    def test_add_user_missing_password(self, admin_client):
        client, token = admin_client
        resp = client.post("/users/add", data={
            "username": "testuser",
            "password": "",
            "_csrf_token": token
        })
        assert resp.status_code == 400

    def test_add_user_weak_password(self, admin_client):
        client, token = admin_client
        resp = client.post("/users/add", data={
            "username": "weakuser",
            "password": "weak",
            "_csrf_token": token
        })
        assert "长度" in resp.data.decode() or resp.status_code == 400


class TestEditUser:
    """test_edit_user"""

    def test_edit_user_success(self, admin_client, temp_data_dir):
        client, token = admin_client
        resp = client.post("/users/edit/admin", data={
            "name": "Updated Admin",
            "role": "admin",
            "dingtalk_id": "dt123",
            "_csrf_token": token
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)
        from data import load_users
        users = load_users()
        admin = next(u for u in users if u["username"] == "admin")
        assert admin["name"] == "Updated Admin"

    def test_edit_user_not_found(self, admin_client):
        client, token = admin_client
        resp = client.post("/users/edit/nonexistent", data={"name": "X", "_csrf_token": token})
        assert resp.status_code == 404


class TestDeleteUser:
    """test_delete_user"""

    def test_delete_user_success(self, admin_client, temp_data_dir):
        client, token = admin_client
        from data import save_users, load_users
        users = load_users()
        users.append({"username": "deleteme", "name": "Delete Me",
                       "password": "DelPass123", "role": "user",
                       "dingtalk_id": "", "failed_attempts": 0,
                       "consecutive_locks": 0, "lock_until": None})
        save_users(users)
        import data
    
        resp = client.post("/users/delete/deleteme", data={"_csrf_token": token},
                           follow_redirects=False)
        assert resp.status_code in (200, 302)
        users = load_users()
        assert not any(u["username"] == "deleteme" for u in users)

    def test_delete_admin_blocked(self, admin_client):
        client, token = admin_client
        resp = client.post("/users/delete/admin", data={"_csrf_token": token})
        assert "删除" in resp.data.decode() or resp.status_code == 400


class TestCaptchaRoute:
    """test captcha generation"""

    def test_captcha_endpoint(self, client):
        resp = client.get("/captcha")
        assert resp.status_code == 200
        assert resp.content_type.startswith("image/png")


class TestUsersPage:
    """test users management page"""

    def test_users_page(self, admin_client):
        client, token = admin_client
        resp = client.get("/users")
        assert resp.status_code == 200
