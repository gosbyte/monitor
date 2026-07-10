# -*- coding: utf-8 -*-
"""到期项路由测试 - CRUD, 批量操作, 导入导出, 备份恢复"""
import os
import sys
import json
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import app


@pytest.fixture
def admin_client(temp_data_dir):
    """Flask test client with logged-in admin"""
    app.config["TESTING"] = True
    with app.test_client() as c:
        from data import save_users
        from werkzeug.security import generate_password_hash
        users = [{"username": "admin", "name": "Admin",
                   "password": generate_password_hash("Admin123"),
                   "role": "admin", "force_change_password": 0, "dingtalk_id": "", "failed_attempts": 0,
                   "consecutive_locks": 0, "lock_until": None}]
        save_users(users)
        import data

        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            sess["_csrf_token"] = "testtoken123456789012345678901234567890"
        yield c


class TestIndexPage:
    """test index page"""

    def test_index_page_get(self, admin_client):
        resp = admin_client.get("/")
        assert resp.status_code == 200

    def test_index_page_with_certs(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 1, "customer": "Test", "cert_type": "SSL", "domain": "t.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/")
        assert resp.status_code == 200
        assert b"Test" in resp.data


class TestAddCertForm:
    """test_add_cert_form"""

    def test_add_cert_post(self, admin_client, temp_data_dir):
        from data import load_certs
        resp = admin_client.post("/add", data={
            "customer": "NewCorp",
            "cert_type": "SSL",
            "domain": "newcorp.com",
            "expire_date": "2027-12-31",
            "expire_time": "23:59",
            "note": "Test cert",
            "remind_enabled": "on",
            "_ajax": "1"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["message"] == "添加成功"
        certs = load_certs()
        assert any(c["customer"] == "NewCorp" for c in certs)

    def test_add_cert_redirect(self, admin_client, temp_data_dir):
        from data import load_certs
        resp = admin_client.post("/add", data={
            "customer": "RedirectCorp",
            "cert_type": "SSL",
            "domain": "rc.com",
            "expire_date": "2027-12-31",
            "expire_time": "",
            "note": "",
            "remind_enabled": "on"
        }, follow_redirects=False)
        assert resp.status_code in (200, 302)


class TestAddCertApi:
    """test_add_cert_api - AJAX variant"""

    def test_add_cert_ajax(self, admin_client, temp_data_dir):
        from data import load_certs
        resp = admin_client.post("/add", data={
            "customer": "AjaxCorp",
            "cert_type": "Wildcard",
            "domain": "*.ajax.com",
            "expire_date": "2028-06-30",
            "expire_time": "12:00",
            "note": "AJAX test",
            "remind_enabled": "on"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert any(c["customer"] == "AjaxCorp" for c in certs)


class TestEditCert:
    """test_edit_cert"""

    def test_edit_cert_post(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 100, "customer": "EditMe", "cert_type": "SSL", "domain": "edit.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.post("/edit/100", data={
            "customer": "EditedCorp",
            "cert_type": "DV",
            "domain": "edited.com",
            "expire_date": "2028-01-01",
            "note": "Updated note",
            "remind_enabled": "on",
            "handled": ""
        })
        assert resp.status_code in (200, 302)
        certs = load_certs()
        cert = next((c for c in certs if c["id"] == 100), None)
        assert cert is not None
        assert cert["customer"] == "EditedCorp"

    def test_edit_cert_not_found(self, admin_client):
        resp = admin_client.get("/edit/9999")
        assert resp.status_code == 404

    def test_edit_cert_ajax(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 101, "customer": "AjaxEdit", "cert_type": "SSL", "domain": "ae.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.post("/edit/101", json={
            "customer": "AjaxEdited",
            "cert_type": "OV",
            "expire_date": "2028-06-30",
            "note": "Ajax update",
            "remind_enabled": True,
            "handled": False
        }, content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True


class TestDeleteCert:
    """test_delete_cert"""

    def test_delete_cert(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 200, "customer": "ToDelete", "cert_type": "SSL", "domain": "del.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.post("/delete/200",
                                  headers={"X-Requested-With": "XMLHttpRequest"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert not any(c["id"] == 200 for c in certs)

    def test_delete_cert_not_found(self, admin_client):
        resp = admin_client.post("/delete/9999",
                                  headers={"X-Requested-With": "XMLHttpRequest"})
        data = resp.get_json()
        assert data["ok"] is True  # Route deletes nothing silently


class TestBatchDelete:
    """test_batch_delete"""

    def test_batch_delete_multiple(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([
            {"id": 300, "customer": "BDel1", "cert_type": "SSL", "domain": "b1.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
            {"id": 301, "customer": "BDel2", "cert_type": "SSL", "domain": "b2.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
            {"id": 302, "customer": "Keep", "cert_type": "SSL", "domain": "k.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ])
        resp = admin_client.post("/api/batch_delete", json={"ids": [300, 301]},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert not any(c["id"] in (300, 301) for c in certs)
        assert any(c["id"] == 302 for c in certs)


class TestBatchHandle:
    """test_batch_handle"""

    def test_batch_handle_true(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([
            {"id": 400, "customer": "BH1", "cert_type": "SSL", "domain": "bh1.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ])
        resp = admin_client.post("/api/batch_handle", json={"ids": [400], "handled": True},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert certs[0]["handled"] is True

    def test_batch_handle_false(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([
            {"id": 401, "customer": "BH2", "cert_type": "SSL", "domain": "bh2.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": True},
        ])
        resp = admin_client.post("/api/batch_handle", json={"ids": [401], "handled": False},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert certs[0]["handled"] is False


class TestBatchRemind:
    """test_batch_remind"""

    def test_batch_remind_enable(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([
            {"id": 500, "customer": "BR1", "cert_type": "SSL", "domain": "br1.com",
             "expire_date": "2027-12-31", "remind_enabled": False, "handled": False},
        ])
        resp = admin_client.post("/api/batch_remind", json={"ids": [500], "remind_enabled": True},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert certs[0]["remind_enabled"] is True

    def test_batch_remind_disable(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([
            {"id": 501, "customer": "BR2", "cert_type": "SSL", "domain": "br2.com",
             "expire_date": "2027-12-31", "remind_enabled": True, "handled": False},
        ])
        resp = admin_client.post("/api/batch_remind", json={"ids": [501], "remind_enabled": False},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert certs[0]["remind_enabled"] is False


class TestImportCertsJson:
    """test_import_certs_json"""

    def test_import_certs_valid(self, admin_client, temp_data_dir):
        from data import load_certs
        certs_before = load_certs()
        resp = admin_client.post("/import", json=[
            {"customer": "Imp1", "cert_type": "SSL", "domain": "imp1.com",
             "expire_date": "2027-12-31", "note": "Imported"},
            {"customer": "Imp2", "cert_type": "DV", "domain": "imp2.com",
             "expire_date": "2028-06-30", "note": "Also imported"},
        ], headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        assert data["imported"] == 2
        certs_after = load_certs()
        assert len(certs_after) == len(certs_before) + 2

    def test_import_certs_invalid_data(self, admin_client):
        resp = admin_client.post("/import", json={"not": "an array"},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_import_certs_missing_fields(self, admin_client, temp_data_dir):
        from data import load_certs
        certs_before = load_certs()
        resp = admin_client.post("/import", json=[
            {"customer": "Valid"},
            {"expire_date": "2027-12-31"},  # missing customer
        ], headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs_after = load_certs()
        # Only valid record imported
        assert len(certs_after) == len(certs_before) + 1


class TestExportCertsJson:
    """test_export_certs_json"""

    def test_export_certs_json(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 600, "customer": "ExportCorp", "cert_type": "SSL", "domain": "exp.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/export/json")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        certs = resp.get_json()
        assert len(certs) >= 1

    def test_export_certs_root(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 601, "customer": "RootExport", "cert_type": "SSL", "domain": "re.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/export")
        assert resp.status_code == 200


class TestExportExcel:
    """test_export_excel"""

    def test_export_excel(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 700, "customer": "ExcelCorp", "cert_type": "SSL", "domain": "ex.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/export/excel")
        assert resp.status_code == 200
        assert "spreadsheet" in resp.content_type


class TestDownloadTemplate:
    """test download import template"""

    def test_download_template(self, admin_client):
        resp = admin_client.get("/import/template")
        assert resp.status_code == 200
        assert "spreadsheet" in resp.content_type


class TestBackupData:
    """test_backup_data"""

    def test_backup_json(self, admin_client, temp_data_dir):
        from data import save_certs, save_config
        save_certs([{"id": 800, "customer": "BackupCorp", "cert_type": "SSL", "domain": "bk.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        save_config({"webhook_url": "http://test.com"})
        resp = admin_client.get("/backup")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        backup = resp.get_json()
        assert "backup_time" in backup
        assert "cert_data" in backup

    def test_backup_empty(self, admin_client, temp_data_dir):
        resp = admin_client.get("/backup")
        assert resp.status_code == 200
        backup = resp.get_json()
        assert backup["cert_data"] == [] or backup["cert_data"] is None


class TestRestoreData:
    """test_restore_data"""

    def test_restore_get(self, admin_client):
        resp = admin_client.get("/restore")
        assert resp.status_code == 200

    def test_restore_post(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        # Create initial data
        save_certs([{"id": 900, "customer": "OrigCorp", "cert_type": "SSL", "domain": "orig.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        # Create backup data
        backup_data = {
            "backup_time": "2027-07-04 12:00:00",
            "version": "2.0",
            "mode": "json",
            "cert_data": [
                {"id": 900, "customer": "RestoredCorp", "cert_type": "SSL", "domain": "rst.com",
                 "expire_date": "2028-06-30", "remind_enabled": True, "handled": False}
            ],
            "config": {"webhook_url": "http://restored.com"},
            "users": [],
            "logs": [],
            "push_history": []
        }
        json_str = json.dumps(backup_data, ensure_ascii=False)
        file_bytes = json_str.encode("utf-8-sig")
        data = {"backup_file": (io.BytesIO(file_bytes), "backup.json")}
        resp = admin_client.post("/restore", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        data_resp = resp.get_json()
        assert data_resp["ok"] is True


class TestApiPreviewImport:
    """test preview import"""

    def test_preview_import_no_file(self, admin_client):
        resp = admin_client.post("/api/preview_import",
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_preview_import_invalid_extension(self, admin_client):
        data = {"file": (io.BytesIO(b"not excel"), "test.csv")}
        resp = admin_client.post("/api/preview_import", data=data,
                                  content_type="multipart/form-data",
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data_resp = resp.get_json()
        assert data_resp["ok"] is False


class TestApiImportExcel:
    """test import excel via API"""

    def test_import_excel_empty(self, admin_client):
        resp = admin_client.post("/api/import_excel", json={"data": []},
                                  headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is False

    def test_import_excel_valid(self, admin_client, temp_data_dir):
        from data import load_certs
        certs_before = load_certs()
        resp = admin_client.post("/api/import_excel", json={
            "data": [
                {"customer": "ExcelImp1", "expiry_date": "2027-12-31", "cert_type": "SSL", "domain": "ei1.com"},
                {"customer": "ExcelImp2", "expiry_date": "2028-06-30", "cert_type": "DV", "domain": "ei2.com"},
            ]
        }, headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs_after = load_certs()
        assert len(certs_after) == len(certs_before) + 2

    def test_import_excel_invalid_date(self, admin_client, temp_data_dir):
        from data import load_certs
        certs_before = load_certs()
        resp = admin_client.post("/api/import_excel", json={
            "data": [
                {"customer": "BadDate", "expiry_date": "not-a-date", "cert_type": "SSL", "domain": "bd.com"},
            ]
        }, headers={"X-CSRF-Token": "testtoken123456789012345678901234567890"})
        data = resp.get_json()
        assert data["ok"] is True
        certs_after = load_certs()
        assert len(certs_after) == len(certs_before)


class TestApiDeleteCert:
    """test API delete cert endpoint"""

    def test_api_delete_cert(self, admin_client, temp_data_dir):
        from data import save_certs, load_certs
        save_certs([{"id": 1000, "customer": "ApiDel", "cert_type": "SSL", "domain": "ad.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.delete("/api/cert/1000")
        data = resp.get_json()
        assert data["ok"] is True
        certs = load_certs()
        assert not any(c["id"] == 1000 for c in certs)

    def test_api_delete_cert_not_found(self, admin_client):
        resp = admin_client.delete("/api/cert/9999")
        data = resp.get_json()
        assert data["ok"] is False


class TestCertStatusApi:
    """test get cert status API"""

    def test_get_cert_status_api(self, admin_client, temp_data_dir):
        from data import save_certs
        save_certs([{"id": 1100, "customer": "StatusCorp", "cert_type": "SSL", "domain": "sc.com",
                      "expire_date": "2027-12-31", "remind_enabled": True, "handled": False}])
        resp = admin_client.get("/api/cert_status/1100")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["customer"] == "StatusCorp"

    def test_get_cert_status_not_found(self, admin_client):
        resp = admin_client.get("/api/cert_status/9999")
        assert resp.status_code == 404


class TestNonAdminAccess:
    """Non-admin cannot access admin routes"""

    def test_non_admin_cannot_add(self, temp_data_dir):
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
            resp = c.post("/add", data={"customer": "X", "cert_type": "SSL", "domain": "x.com",
                                         "expire_date": "2027-12-31", "expire_time": ""})
            assert resp.status_code == 403

    def test_non_admin_cannot_import(self, temp_data_dir):
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
            resp = c.post("/import", json=[{}])
            assert resp.status_code == 403

    def test_non_admin_cannot_export(self, temp_data_dir):
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
            resp = c.get("/export")
            assert resp.status_code == 403

    def test_non_admin_cannot_backup(self, temp_data_dir):
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
            resp = c.get("/backup")
            assert resp.status_code == 403

    def test_unauthenticated_cannot_add(self, temp_data_dir):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            resp = c.post("/add", data={"customer": "X", "cert_type": "SSL", "domain": "x.com",
                                         "expire_date": "2027-12-31", "expire_time": ""})
            assert resp.status_code == 302
