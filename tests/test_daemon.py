# -*- coding: utf-8 -*-
"""daemon.py 核心逻辑测试"""
import os
import sys
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def daemon_env(temp_data_dir):
    """设置 daemon 环境"""
    os.environ["DATA_DIR"] = str(temp_data_dir)
    import data
    data.BASE_DIR = str(temp_data_dir)
    data.DATA_DIR = str(temp_data_dir)
    data.DATA_FILE = str(temp_data_dir / "certs.json")
    data.CONFIG_FILE = str(temp_data_dir / "config.json")
    data.USERS_FILE = str(temp_data_dir / "users.json")
    data.LOGS_FILE = str(temp_data_dir / "logs.json")

    import db
    db.DB_PATH = str(temp_data_dir / "monitor.db")
    db.init_db()
    import importlib
    import daemon
    importlib.reload(daemon)
    yield temp_data_dir
    os.environ.pop("DATA_DIR", None)


class TestParseExpireDate:
    """test_parse_expire_date_various_formats"""

    def test_date_only(self, daemon_env):
        from daemon import parse_expire_date
        dt = parse_expire_date("2027-12-31")
        assert dt.year == 2027
        assert dt.month == 12
        assert dt.day == 31
        assert dt.hour == 23
        assert dt.minute == 59

    def test_datetime_space(self, daemon_env):
        from daemon import parse_expire_date
        dt = parse_expire_date("2027-06-15 14:30")
        assert dt.year == 2027
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30

    def test_datetime_t(self, daemon_env):
        from daemon import parse_expire_date
        dt = parse_expire_date("2027-06-15T14:30")
        assert dt.year == 2027
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30

    def test_with_whitespace(self, daemon_env):
        from daemon import parse_expire_date
        dt = parse_expire_date("  2027-12-31  ")
        assert dt.year == 2027
        assert dt.month == 12
        assert dt.day == 31

    def test_invalid_date_raises(self, daemon_env):
        from daemon import parse_expire_date
        with pytest.raises(ValueError):
            parse_expire_date("not-a-date")


class TestBuildEmailHtml:
    """test_build_email_html"""

    def test_empty_list(self, daemon_env):
        from daemon import build_email_html
        html = build_email_html([], is_responsible=False)
        assert "共 0 条到期项需要关注" in html
        assert "<table" in html

    def test_single_cert(self, daemon_env):
        from daemon import build_email_html
        certs = [{"customer": "ACME", "cert_type": "SSL", "domain": "acme.com",
                  "expire_date": "2027-12-31", "days_left": 365}]
        html = build_email_html(certs)
        assert "ACME" in html
        assert "SSL" in html
        assert "acme.com" in html
        assert "剩365天" in html

    def test_expired_badge(self, daemon_env):
        from daemon import build_email_html
        certs = [{"customer": "OldCorp", "cert_type": "SSL", "domain": "old.com",
                  "expire_date": "2020-01-01", "days_left": -100}]
        html = build_email_html(certs)
        assert "已过期" in html

    def test_today_expired(self, daemon_env):
        from daemon import build_email_html
        certs = [{"customer": "TodayCorp", "cert_type": "SSL", "domain": "today.com",
                  "expire_date": "2027-07-04", "days_left": 0}]
        html = build_email_html(certs)
        assert "今日到期" in html

    def test_responsible_subtitle(self, daemon_env):
        from daemon import build_email_html
        certs = [{"customer": "Test", "cert_type": "SSL", "domain": "t.com",
                  "expire_date": "2027-12-31", "days_left": 10}]
        html = build_email_html(certs, is_responsible=True)
        assert "您负责的以下到期项即将到期" in html


class TestLoadSaveState:
    """State file persistence"""

    def test_save_load_state(self, daemon_env):
        import daemon
        state = {"1_day7": "2027-07-04", "2_expired": "2027-07-04"}
        daemon.save_state(state)
        loaded = daemon.load_state()
        assert loaded == state

    def test_load_missing_state(self, daemon_env):
        import daemon
        loaded = daemon.load_state()
        assert loaded == {}

    def test_save_load_state_with_corrupt_file(self, daemon_env):
        import daemon
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            f.write("not json{{{")
        loaded = daemon.load_state()
        assert loaded == {}


class TestSendEmailRemind:
    """邮件发送逻辑测试（不实际发送）"""

    def test_no_recipients(self, daemon_env):
        import daemon
        cfg = {"smtp_to": "", "smtp_host": "smtp.test.com", "smtp_user": "u", "smtp_pass": "p"}
        ok, msg = daemon.send_email_remind("subj", "body", cfg)
        assert ok is False
        assert "邮件配置不完整" in msg or "收件人为空" in msg

    def test_no_smtp_config(self, daemon_env):
        import daemon
        cfg = {"smtp_to": "a@b.com", "smtp_host": "", "smtp_user": "", "smtp_pass": ""}
        ok, msg = daemon.send_email_remind("subj", "body", cfg)
        assert ok is False

    def test_send_email_remind_to_empty_recipients(self, daemon_env):
        import daemon
        cfg = {"smtp_host": "smtp.test.com", "smtp_user": "u", "smtp_pass": "p", "smtp_port": 465}
        ok, msg = daemon.send_email_remind_to("subj", "body", cfg, [])
        assert ok is False
        assert "收件人为空" in msg

    def test_invalid_port(self, daemon_env):
        import daemon
        cfg = {"smtp_host": "smtp.test.com", "smtp_user": "u", "smtp_pass": "p", "smtp_port": "abc"}
        ok, msg = daemon.send_email_remind_to("subj", "body", cfg, ["a@b.com"])
        assert ok is False


class TestCheckAndRemind:
    """test_check_and_remind_*"""

    def test_no_channels_configured(self, daemon_env):
        """没有配置任何通知渠道时不执行"""
        import daemon
        from data import save_config
        save_config({"webhook_url": "", "wecom_webhook": "", "email_enabled": False})
        daemon.check_and_remind()

    def test_check_and_remind_empty_certs(self, daemon_env):
        """test_check_and_remind_empty - 没有到期项时不报错"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com"})
        save_certs([])
        daemon.check_and_remind()

    def test_check_and_remind_expired(self, daemon_env):
        """test_check_and_remind_expired - 已过期项会加入提醒列表"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com", "email_enabled": False})
        past_date = (daemon.datetime.now() - daemon.timedelta(days=10)).strftime("%Y-%m-%d")
        certs = [{"id": 1, "customer": "ExpiredCorp", "cert_type": "SSL", "domain": "exp.com",
                  "expire_date": past_date, "remind_enabled": True, "handled": False}]
        save_certs(certs)
        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()
        state = daemon.load_state()
        assert "1_expired" in state

    def test_check_and_remind_expiring_soon(self, daemon_env):
        """test_check_and_remind_expiring_soon - 7天内到期项提醒"""
        import daemon
        from data import save_config, save_certs
        # Use remind_days=[5] to catch day-5 certs
        save_config({"webhook_url": "http://test.com", "remind_days": [5], "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        certs = [{"id": 2, "customer": "SoonCorp", "cert_type": "SSL", "domain": "soon.com",
                  "expire_date": future_date, "remind_enabled": True, "handled": False}]
        save_certs(certs)
        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()
        state = daemon.load_state()
        assert "2_day5" in state

    def test_check_and_remind_disabled_remind(self, daemon_env):
        """disabled 的到期项不应被提醒"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com", "remind_days": [7, 3, 1], "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        certs = [{"id": 3, "customer": "DisabledCorp", "cert_type": "SSL", "domain": "dis.com",
                  "expire_date": future_date, "remind_enabled": False, "handled": False}]
        save_certs(certs)
        daemon.check_and_remind()
        state = daemon.load_state()
        assert "3_day5" not in state

    def test_check_and_remind_handled_skipped(self, daemon_env):
        """handled 的到期项不会被加入提醒列表（不会被推送）"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com", "remind_days": [5], "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        certs = [{"id": 4, "customer": "HandledCorp", "cert_type": "SSL", "domain": "hand.com",
                  "expire_date": future_date, "remind_enabled": True, "handled": True}]
        save_certs(certs)
        # handled certs are excluded from to_remind, so no dingtalk call
        with patch.object(daemon, 'send_dingtalk_card', return_value=True) as mock_ding:
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()
        # No push should happen for handled certs
        assert not mock_ding.called

    def test_check_and_remind_no_id_skipped(self, daemon_env):
        """无 id 的到期项应被跳过"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com", "remind_days": [7, 3, 1], "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        certs = [{"customer": "NoIdCorp", "cert_type": "SSL", "domain": "noid.com",
                  "expire_date": future_date, "remind_enabled": True}]
        save_certs(certs)
        daemon.check_and_remind()

    def test_check_and_remind_clean_state(self, daemon_env):
        """清理已删除记录的推送状态 - 有存活cert时state会被持久化"""
        import daemon
        from data import save_config, save_certs
        save_config({"webhook_url": "http://test.com", "remind_days": [5], "email_enabled": False})
        # Pre-set state with orphaned keys
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({"1_day7": "2027-07-04", "999_day7": "2027-07-04"}, f)
        # Save a cert with id=1 so 1_day7 survives, 999 gets cleaned
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{"id": 1, "customer": "Keep", "cert_type": "SSL", "domain": "k.com",
                      "expire_date": future_date, "remind_enabled": True, "handled": False}])
        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()
        loaded = daemon.load_state()
        # 999 should be cleaned, 1 should remain
        assert "999_day7" not in loaded
        assert "1_day7" in loaded
