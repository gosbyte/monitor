# -*- coding: utf-8 -*-
"""
初始化数据文件
首次启动时创建默认的配置文件和用户数据
支持 JSON 和 SQLite 双模式
"""
import os
import json
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"


def init_data():
    """初始化数据目录和默认文件"""
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 如果使用 SQLite，初始化数据库
    if USE_SQLITE:
        from db import init_db
        init_db()
        print("[INIT] SQLite database initialized")
        return

    # JSON 模式下的初始化逻辑（保持兼容）
    certs_file = os.path.join(DATA_DIR, "certs.json")
    if not os.path.exists(certs_file):
        with open(certs_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"[INIT] Created {certs_file}")

    config_file = os.path.join(DATA_DIR, "config.json")
    if not os.path.exists(config_file):
        config = {
            "webhook_url": "",
            "secret": "",
            "remind_days": [30, 14, 7, 3, 1],
            "email_enabled": False,
            "smtp_host": "",
            "smtp_port": 465,
            "smtp_user": "",
            "smtp_pass": "",
            "smtp_to": "",
            "smtp_from_name": "到期提醒系统",
            "wecom_enabled": False,
            "wecom_webhook": "",
            "webhook_enabled": True,
            "backup_enabled": True,
            "backup_interval_hours": 24,
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"[INIT] Created {config_file}")

    users_file = os.path.join(DATA_DIR, "users.json")
    if not os.path.exists(users_file):
        try:
            from werkzeug.security import generate_password_hash
        except ImportError:
            import hashlib
            def generate_password_hash(password):
                return hashlib.sha256(password.encode()).hexdigest()
        
        users = [
            {
                "username": "admin",
                "name": "管理员",
                "password": generate_password_hash("admin123"),
                "dingtalk_id": "",
                "role": "admin",
                "failed_attempts": 0,
                "consecutive_locks": 0,
                "lock_until": None
            }
        ]
        with open(users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        print(f"[INIT] Created {users_file}")

    logs_file = os.path.join(DATA_DIR, "logs.json")
    if not os.path.exists(logs_file):
        with open(logs_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"[INIT] Created {logs_file}")

    state_file = os.path.join(DATA_DIR, "remind_state.json")
    if not os.path.exists(state_file):
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        print(f"[INIT] Created {state_file}")

    secret_file = os.path.join(DATA_DIR, ".secret_key")
    if not os.path.exists(secret_file):
        secret_key = secrets.token_hex(32)
        with open(secret_file, "w") as f:
            f.write(secret_key)
        print(f"[INIT] Created {secret_file}")

    enc_file = os.path.join(DATA_DIR, ".encryption_key")
    if not os.path.exists(enc_file):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        with open(enc_file, "wb") as f:
            f.write(key)
        print(f"[INIT] Created {enc_file}")

    print("[INIT] Data initialization complete!")


if __name__ == "__main__":
    init_data()
