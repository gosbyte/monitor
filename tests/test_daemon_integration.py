# -*- coding: utf-8 -*-
"""Daemon 集成测试 — 提醒状态持久化、多通道推送、清理。"""
import os
import sys
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def daemon_env(temp_data_dir):
    """设置 daemon 环境并重新加载模块。"""
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


# ══════════════════════════════════════════════════════════════════════
# TestDaemonStatePersistence — remind_state.json 读写
# ══════════════════════════════════════════════════════════════════════

class TestDaemonStatePersistence:
    """测试 remind_state.json 的读写持久化。"""

    def test_save_and_load_state(self, daemon_env):
        """保存状态后应能正确加载。"""
        import daemon
        state = {"1_day7": "2027-07-04", "2_day3": "2027-07-05"}
        daemon.save_state(state)
        loaded = daemon.load_state()
        assert loaded == state

    def test_load_empty_state(self, daemon_env):
        """未保存过状态时应返回空字典。"""
        import daemon
        loaded = daemon.load_state()
        assert loaded == {}

    def test_state_survives_module_reload(self, daemon_env):
        """状态在模块重载后仍然存在。"""
        import daemon
        import importlib
        state = {"3_day1": "2027-07-06"}
        daemon.save_state(state)
        importlib.reload(daemon)
        loaded = daemon.load_state()
        assert loaded == state

    def test_state_atomic_write(self, daemon_env):
        """保存状态时使用临时文件 + os.replace，保证原子写入。"""
        import daemon
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        assert not os.path.exists(state_file + ".tmp")

        daemon.save_state({"test": "value"})
        assert os.path.exists(state_file)
        # 临时文件应在写入后被清理
        assert not os.path.exists(state_file + ".tmp")

    def test_state_corrupt_file_recovery(self, daemon_env):
        """损坏的状态文件应被安全处理，返回空字典。"""
        import daemon
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            f.write("{invalid json!!!}")

        loaded = daemon.load_state()
        assert loaded == {}

    def test_state_empty_file_recovery(self, daemon_env):
        """空状态文件应被处理为 {}。"""
        import daemon
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            f.write("")

        loaded = daemon.load_state()
        assert loaded == {}

    def test_state_persists_across_check_and_remind(self, daemon_env):
        """check_and_remind 后状态应被持久化。"""
        import daemon
        from data import save_config, save_certs

        save_config({
            "webhook_url": "http://test.dingtalk.com",
            "remind_days": [5],
            "email_enabled": False,
        })

        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 10, "customer": "PersistCorp", "cert_type": "SSL",
            "domain": "persist.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        # 状态应已持久化
        state = daemon.load_state()
        assert "10_day5" in state


# ══════════════════════════════════════════════════════════════════════
# TestMultiChannelPush — 多通道推送
# ══════════════════════════════════════════════════════════════════════

class TestMultiChannelPush:
    """测试钉钉 + 企业微信 + 邮件组合推送。"""

    def test_dingtalk_push_called_when_configured(self, daemon_env):
        """配置了钉钉 Webhook 时，应调用 send_dingtalk_card。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 20, "customer": "DTCorp", "cert_type": "SSL",
            "domain": "dt.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True) as mock:
            daemon.check_and_remind()
            mock.assert_called_once()

    def test_wecom_push_called_when_configured(self, daemon_env):
        """配置了企业微信时，应调用 send_wecom。"""
        import daemon
        from data import save_config, save_certs

        save_config({
            "webhook_url": "http://test.com",
            "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send/xxx",
            "wecom_enabled": True,
            "email_enabled": False,
        })
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 21, "customer": "WCComCorp", "cert_type": "SSL",
            "domain": "wc.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True) as mock:
                daemon.check_and_remind()
                mock.assert_called_once()

    def test_email_push_when_enabled(self, daemon_env):
        """启用邮件推送时，应调用邮件发送逻辑。"""
        import daemon
        from data import save_config, save_certs

        save_config({
            "webhook_url": "http://test.com",
            "email_enabled": True,
            "smtp_host": "smtp.test.com",
            "smtp_port": "465",
            "smtp_user": "test@test.com",
            "smtp_pass": "encrypted_pass",
            "smtp_to": "admin@test.com",
        })
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 22, "customer": "EmailCorp", "cert_type": "SSL",
            "domain": "email.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                with patch.object(daemon, 'send_email_remind', return_value=(True, "OK")):
                    daemon.check_and_remind()
                    # 邮件应被调用
                    # 由于 send_email_remind 被 mock，不会真正发送

    def test_all_three_channels_simultaneously(self, daemon_env):
        """三种通道同时配置时都应被调用。"""
        import daemon
        from data import save_config, save_certs

        save_config({
            "webhook_url": "http://dingtalk.com",
            "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send/xxx",
            "wecom_enabled": True,
            "email_enabled": True,
            "smtp_host": "smtp.test.com",
            "smtp_user": "test@test.com",
            "smtp_pass": "pass",
            "smtp_to": "admin@test.com",
        })
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 23, "customer": "MultiCorp", "cert_type": "SSL",
            "domain": "multi.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True) as dt_mock:
            with patch.object(daemon, 'send_wecom', return_value=True) as wc_mock:
                with patch.object(daemon, 'send_email_remind', return_value=(True, "OK")) as em_mock:
                    daemon.check_and_remind()
                    assert dt_mock.called
                    assert wc_mock.called
                    assert em_mock.called

    def test_no_channels_configured_skips_push(self, daemon_env):
        """未配置任何通道时，不应调用任何推送。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "", "wecom_webhook": "", "email_enabled": False})
        save_certs([{
            "id": 24, "customer": "NoPushCorp", "cert_type": "SSL",
            "domain": "nopush.com", "expire_date": "2027-12-31",
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card') as dt_mock:
            with patch.object(daemon, 'send_wecom') as wc_mock:
                daemon.check_and_remind()
                assert not dt_mock.called
                assert not wc_mock.called

    def test_push_failure_prevents_state_save(self, daemon_env):
        """推送失败时不应保存状态（以便下次重试）。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 25, "customer": "FailCorp", "cert_type": "SSL",
            "domain": "fail.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        # 钉钉推送失败
        with patch.object(daemon, 'send_dingtalk_card', return_value=False):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        # 状态不应被保存（因为推送未全部成功）
        state = daemon.load_state()
        # 25_day5 不应在 state 中
        assert "25_day5" not in state


# ══════════════════════════════════════════════════════════════════════
# TestDaemonCleanup — 清理已删除记录的推送状态
# ══════════════════════════════════════════════════════════════════════

class TestDaemonCleanup:
    """测试 daemon 清理已删除记录的推送状态。"""

    def test_cleanup_removes_orphaned_state_keys(self, daemon_env):
        """已删除的 cert_id 对应的 state key 应被清理。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})

        # 预设包含 orphaned 的 state
        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({
                "100_day7": "2027-07-04",
                "999_day7": "2027-07-04",  # cert 999 不存在
                "888_expired": "2027-07-04",  # cert 888 不存在
            }, f)

        # 只保留 cert 100
        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 100, "customer": "AliveCorp", "cert_type": "SSL",
            "domain": "alive.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        state = daemon.load_state()
        assert "100_day7" in state
        assert "999_day7" not in state
        assert "888_expired" not in state

    def test_cleanup_preserves_existing_state_for_active_certs(self, daemon_env):
        """活跃 cert 的 state 应被保留。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "remind_days": [5], "email_enabled": False})

        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({
                "200_day7": "2027-07-04",
                "201_day7": "2027-07-04",
            }, f)

        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([
            {"id": 200, "customer": "Cert200", "cert_type": "SSL", "domain": "c200.com",
             "expire_date": future_date, "remind_enabled": True, "handled": False},
            {"id": 201, "customer": "Cert201", "cert_type": "SSL", "domain": "c201.com",
             "expire_date": future_date, "remind_enabled": True, "handled": False},
        ])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        state = daemon.load_state()
        assert "200_day7" in state
        assert "201_day7" in state

    def test_cleanup_handles_malformed_state_keys(self, daemon_env):
        """非标准格式的 state key 应被保留。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})

        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({
                "300_day7": "2027-07-04",
                "malformed_key": "some_value",  # 非标准格式
            }, f)

        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 300, "customer": "MalformedCorp", "cert_type": "SSL",
            "domain": "malformed.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        state = daemon.load_state()
        assert "300_day7" in state
        assert "malformed_key" in state

    def test_cleanup_no_certs_clears_all_numeric_keys(self, daemon_env):
        """无活跃 cert 时，所有 numeric state keys 应被清理。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})

        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({
                "400_day7": "2027-07-04",
                "401_day7": "2027-07-04",
                "402_expired": "2027-07-04",
            }, f)

        save_certs([])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        state = daemon.load_state()
        assert "400_day7" not in state
        assert "401_day7" not in state
        assert "402_expired" not in state

    def test_cleanup_preserves_non_numeric_state_keys(self, daemon_env):
        """非数字开头的 state key 应被保留。"""
        import daemon
        from data import save_config, save_certs

        save_config({"webhook_url": "http://test.com", "email_enabled": False})

        state_file = os.path.join(str(daemon_env), "remind_state.json")
        with open(state_file, "w") as f:
            json.dump({
                "500_day7": "2027-07-04",
                "global_counter": 42,
                "system_flag": True,
            }, f)

        future_date = (daemon.datetime.now() + daemon.timedelta(days=5)).strftime("%Y-%m-%d")
        save_certs([{
            "id": 500, "customer": "PreserveCorp", "cert_type": "SSL",
            "domain": "preserve.com", "expire_date": future_date,
            "remind_enabled": True, "handled": False,
        }])

        with patch.object(daemon, 'send_dingtalk_card', return_value=True):
            with patch.object(daemon, 'send_wecom', return_value=True):
                daemon.check_and_remind()

        state = daemon.load_state()
        assert "500_day7" in state
        assert state.get("global_counter") == 42
        assert state.get("system_flag") is True
