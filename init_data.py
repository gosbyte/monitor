# -*- coding: utf-8 -*-
"""
初始化数据文件
首次启动时创建默认的数据库和数据
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)


def init_data():
    """初始化数据目录和数据库"""
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 初始化 SQLite 数据库
    from db import init_db, migrate_json_to_sqlite
    init_db()
    print("[INIT] SQLite database initialized")

    # 自动迁移 JSON 数据到 SQLite
    migrated = migrate_json_to_sqlite()
    if migrated > 0:
        print(f"[INIT] Migrated {migrated} records from JSON to SQLite")
    else:
        print("[INIT] No JSON data to migrate")

    # 创建 .secret_key 和 .encryption_key（这些文件不存入数据库）
    import secrets
    secret_file = os.path.join(DATA_DIR, ".secret_key")
    if not os.path.exists(secret_file):
        secret_key = secrets.token_hex(32)
        with open(secret_file, "w") as f:
            f.write(secret_key)
        print(f"[INIT] Created {secret_file}")

    from cryptography.fernet import Fernet
    enc_file = os.path.join(DATA_DIR, ".encryption_key")
    if not os.path.exists(enc_file):
        key = Fernet.generate_key()
        with open(enc_file, "wb") as f:
            f.write(key)
        print(f"[INIT] Created {enc_file}")

    print("[INIT] Data initialization complete!")


if __name__ == "__main__":
    init_data()
