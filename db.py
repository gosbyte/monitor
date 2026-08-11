# -*- coding: utf-8 -*-
"""
数据库层 - SQLite 替代 JSON 文件
支持索引、事务、并发查询
"""
from __future__ import annotations

import os
import sqlite3
import json as json_mod
import logging
from datetime import datetime
from typing import Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__))), "monitor.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 提升并发性能
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_transaction():
    """数据库事务上下文管理器"""
    conn: sqlite3.Connection = get_db()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()


def init_db() -> None:
    """初始化数据库表结构"""
    with db_transaction() as conn:
        conn.executescript("""
            -- 到期项表
            CREATE TABLE IF NOT EXISTS certs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                cert_type TEXT DEFAULT '',
                domain TEXT DEFAULT '',
                expire_date TEXT NOT NULL,
                note TEXT DEFAULT '',
                remind_enabled BOOLEAN DEFAULT 1,
                handled BOOLEAN DEFAULT 0,
                responsible_users TEXT DEFAULT '[]',
                created_by TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
            
            -- 用户表
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                password TEXT NOT NULL,
                dingtalk_id TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                email TEXT DEFAULT '',
                failed_attempts INTEGER DEFAULT 0,
                consecutive_locks INTEGER DEFAULT 0,
                lock_until TEXT DEFAULT NULL,
                force_change_password INTEGER DEFAULT 1
            );
            
            -- 默认管理员用户将在 init_db() 中动态生成密码后插入
            
            -- 配置表
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            
            -- 操作日志表
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT DEFAULT '',
                detail TEXT DEFAULT '',
                ip TEXT DEFAULT ''
            );
            
            -- 推送历史表
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                cert_customer TEXT DEFAULT '',
                cert_domain TEXT DEFAULT '',
                channels TEXT DEFAULT '[]',
                status TEXT DEFAULT 'success',
                message TEXT DEFAULT ''
            );
            
            -- 索引
            CREATE INDEX IF NOT EXISTS idx_certs_expire ON certs(expire_date);
            CREATE INDEX IF NOT EXISTS idx_certs_remind ON certs(remind_enabled);
            CREATE INDEX IF NOT EXISTS idx_certs_handled ON certs(handled);
            CREATE INDEX IF NOT EXISTS idx_certs_type ON certs(cert_type);
            CREATE INDEX IF NOT EXISTS idx_certs_created_by ON certs(created_by);
            CREATE INDEX IF NOT EXISTS idx_certs_responsible ON certs(responsible_users);
            CREATE INDEX IF NOT EXISTS idx_certs_composite ON certs(handled, remind_enabled, expire_date);
            CREATE INDEX IF NOT EXISTS idx_logs_time ON logs(time);
            CREATE INDEX IF NOT EXISTS idx_logs_username ON logs(username);
            CREATE INDEX IF NOT EXISTS idx_logs_composite ON logs(username, time);
            CREATE INDEX IF NOT EXISTS idx_push_time ON push_history(time);
            CREATE INDEX IF NOT EXISTS idx_push_cert ON push_history(cert_customer);
            
            -- 插入默认配置
            INSERT OR IGNORE INTO config (key, value) VALUES ('webhook_url', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('secret', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('remind_days', '[30, 14, 7, 3, 1]');
            INSERT OR IGNORE INTO config (key, value) VALUES ('email_enabled', 'false');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_host', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_port', '465');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_user', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_pass', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_to', '');
            INSERT OR IGNORE INTO config (key, value) VALUES ('smtp_from_name', 'Item Monitor');
            INSERT OR IGNORE INTO config (key, value) VALUES ('wecom_enabled', 'false');
            INSERT OR IGNORE INTO config (key, value) VALUES ('wecom_webhook', '');
        """)
        
        # 插入默认管理员用户
        from werkzeug.security import generate_password_hash
        default_password = generate_password_hash("admin123")
        conn.execute(
            "INSERT OR IGNORE INTO users (username, name, password, role) VALUES (?, ?, ?, ?)",
            ("admin", "管理员", default_password, "admin")
        )
        conn.commit()
        logger.info("Database initialized successfully")


def migrate_json_to_sqlite() -> int:
    """从 JSON 文件迁移数据到 SQLite"""
    
    json_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
    certs_file = os.path.join(json_dir, "certs.json")
    users_file = os.path.join(json_dir, "users.json")
    config_file = os.path.join(json_dir, "config.json")
    logs_file = os.path.join(json_dir, "logs.json")
    
    migrated = 0
    
    # 迁移到期项
    if os.path.exists(certs_file):
        with open(certs_file, "r", encoding="utf-8-sig") as f:
            certs = json_mod.load(f)
        if certs:
            with db_transaction() as conn:
                conn.executemany(
                    """INSERT OR REPLACE INTO certs (id, customer, cert_type, domain, expire_date, note,
                       remind_enabled, handled, responsible_users, created_by, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(c.get("id"), c.get("customer"), c.get("cert_type", ""), c.get("domain", ""),
                      c.get("expire_date"), c.get("note", ""),
                      int(c.get("remind_enabled", True)), int(c.get("handled", False)),
                      json_mod.dumps(c.get("responsible_users", []), ensure_ascii=False),
                      c.get("created_by", ""), c.get("created_at", ""),
                      datetime.now().strftime("%Y-%m-%d %H:%M"))
                     for c in certs]
                )
                migrated += len(certs)
            logger.info(f"Migrated {len(certs)} certs from JSON")
    
    # 迁移用户（跳过，因为密码哈希格式可能不同）
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8-sig") as f:
            users = json_mod.load(f)
        if users:
            with db_transaction() as conn:
                for u in users:
                    # [FIX] P0-5: 只对 admin 标记强制改密码，普通用户不拦截
                    force_change = 1 if u.get("role") == "admin" else 0
                    conn.execute(
                        """INSERT OR IGNORE INTO users (username, name, password, dingtalk_id, role, email,
                           failed_attempts, consecutive_locks, lock_until, force_change_password)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (u.get("username"), u.get("name", u.get("username", "")),
                         u.get("password", ""), u.get("dingtalk_id", ""),
                         u.get("role", "user"), u.get("email", ""),
                         u.get("failed_attempts", 0), u.get("consecutive_locks", 0),
                         u.get("lock_until"), force_change)
                    )
                migrated += len(users)
            logger.info(f"Migrated {len(users)} users from JSON")
    
    # 迁移配置
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8-sig") as f:
            cfg = json_mod.load(f)
        with db_transaction() as conn:
            for k, v in cfg.items():
                if isinstance(v, list):
                    v = json_mod.dumps(v)
                else:
                    v = str(v).lower()
                conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, v))
            migrated += len(cfg)
        logger.info(f"Migrated {len(cfg)} config entries from JSON")
    
    # 迁移日志
    if os.path.exists(logs_file):
        with open(logs_file, "r", encoding="utf-8-sig") as f:
            logs = json_mod.load(f)
        if logs:
            with db_transaction() as conn:
                conn.executemany(
                    "INSERT INTO logs (time, username, action, target, detail, ip) VALUES (?, ?, ?, ?, ?, ?)",
                    [(l.get("time", ""), l.get("username", ""), l.get("action", ""),
                      l.get("target", ""), l.get("detail", ""), l.get("ip", ""))
                     for l in logs]
                )
                migrated += len(logs)
            logger.info(f"Migrated {len(logs)} logs from JSON")
    
    if migrated > 0:
        logger.info(f"Migration complete: {migrated} records migrated")
    else:
        logger.info("No data to migrate")
    
    return migrated


# ── 到期项 CRUD ──────────────────────────────────────────────
def db_load_certs() -> list[dict[str, Any]]:
    """加载所有到期项"""
    with db_transaction() as conn:
        rows = conn.execute("SELECT * FROM certs ORDER BY expire_date ASC").fetchall()
        certs: list[dict[str, Any]] = []
        for r in rows:
            cert = dict(r)
            cert["responsible_users"] = json_mod.loads(cert.get("responsible_users", "[]"))
            cert["remind_enabled"] = bool(cert.get("remind_enabled", True))
            cert["handled"] = bool(cert.get("handled", False))
            certs.append(cert)
        return certs


def db_save_cert(cert_data: dict[str, Any]) -> None:
    """保存单条到期项（先检查存在性，避免 INSERT OR REPLACE 破坏 AUTOINCREMENT ID）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cert_id = cert_data.get("id")
    with db_transaction() as conn:
        if cert_id:
            # 检查是否存在
            existing = conn.execute("SELECT id FROM certs WHERE id=?", (cert_id,)).fetchone()
            if existing:
                # 存在则 UPDATE，避免破坏 AUTOINCREMENT
                conn.execute("""UPDATE certs SET customer=?, cert_type=?, domain=?, expire_date=?,
                               note=?, remind_enabled=?, handled=?, responsible_users=?, updated_at=?
                               WHERE id=?""",
                    (cert_data["customer"], cert_data.get("cert_type", ""), cert_data.get("domain", ""),
                     cert_data["expire_date"], cert_data.get("note", ""),
                     int(cert_data.get("remind_enabled", True)), int(cert_data.get("handled", False)),
                     json_mod.dumps(cert_data.get("responsible_users", []), ensure_ascii=False),
                     now, cert_id))
            else:
                # 不存在则 INSERT
                conn.execute("""INSERT INTO certs (id, customer, cert_type, domain, expire_date, note,
                              remind_enabled, handled, responsible_users, created_by, created_at, updated_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cert_id, cert_data["customer"], cert_data.get("cert_type", ""), cert_data.get("domain", ""),
                     cert_data["expire_date"], cert_data.get("note", ""),
                     int(cert_data.get("remind_enabled", True)), int(cert_data.get("handled", False)),
                     json_mod.dumps(cert_data.get("responsible_users", []), ensure_ascii=False),
                     cert_data.get("created_by", ""), now, now))
        else:
            conn.execute("""INSERT INTO certs (customer, cert_type, domain, expire_date, note,
                          remind_enabled, handled, responsible_users, created_by, created_at, updated_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cert_data["customer"], cert_data.get("cert_type", ""), cert_data.get("domain", ""),
                 cert_data["expire_date"], cert_data.get("note", ""),
                 int(cert_data.get("remind_enabled", True)), int(cert_data.get("handled", False)),
                 json_mod.dumps(cert_data.get("responsible_users", []), ensure_ascii=False),
                 cert_data.get("created_by", ""), now, now))


def db_delete_cert(cert_id: int) -> None:
    """删除到期项"""
    with db_transaction() as conn:
        conn.execute("DELETE FROM certs WHERE id=?", (cert_id,))


def db_batch_delete_cert_ids(ids: list[int]) -> int:
    """批量删除到期项，返回实际删除数量"""
    if not ids:
        return 0
    # [SEC] Validate all IDs are integers before building query
    ids = [int(i) for i in ids]
    with db_transaction() as conn:
        placeholders = ",".join("?" for _ in ids)
        cursor = conn.execute(f"DELETE FROM certs WHERE id IN ({placeholders})", ids)
        return cursor.rowcount


def db_get_cert(cert_id: int) -> dict[str, Any] | None:
    """获取单条到期项"""
    with db_transaction() as conn:
        row = conn.execute("SELECT * FROM certs WHERE id=?", (cert_id,)).fetchone()
        if row:
            cert = dict(row)
            cert["responsible_users"] = json_mod.loads(cert.get("responsible_users", "[]"))
            cert["remind_enabled"] = bool(cert.get("remind_enabled", True))
            cert["handled"] = bool(cert.get("handled", False))
            return cert
        return None


# ── 用户 CRUD ──────────────────────────────────────────────
def db_load_users() -> list[dict[str, Any]]:
    """加载所有用户"""
    with db_transaction() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]


def db_save_user(user_data: dict[str, Any]) -> None:
    """保存用户（先检查存在性，避免 INSERT OR REPLACE 问题）"""
    with db_transaction() as conn:
        existing = conn.execute("SELECT username FROM users WHERE username=?", (user_data["username"],)).fetchone()
        if existing:
            # 存在则 UPDATE
            conn.execute("""UPDATE users SET name=?, password=?, dingtalk_id=?,
                          role=?, email=?, failed_attempts=?, consecutive_locks=?, lock_until=?, force_change_password=?
                          WHERE username=?""",
                (user_data.get("name", user_data["username"]),
                 user_data["password"], user_data.get("dingtalk_id", ""),
                 user_data.get("role", "user"), user_data.get("email", ""),
                 user_data.get("failed_attempts", 0),
                 user_data.get("consecutive_locks", 0),
                 user_data.get("lock_until"),
                 int(user_data.get("force_change_password", 1)),
                 user_data["username"]))
        else:
            # 不存在则 INSERT
            conn.execute("""INSERT INTO users (username, name, password, dingtalk_id,
                       role, email, failed_attempts, consecutive_locks, lock_until, force_change_password)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_data["username"], user_data.get("name", user_data["username"]),
                 user_data["password"], user_data.get("dingtalk_id", ""),
                 user_data.get("role", "user"), user_data.get("email", ""),
                 user_data.get("failed_attempts", 0),
                 user_data.get("consecutive_locks", 0),
                 user_data.get("lock_until"),
                 int(user_data.get("force_change_password", 1))))


def db_delete_user(username: str) -> None:
    """删除用户"""
    with db_transaction() as conn:
        conn.execute("DELETE FROM users WHERE username=?", (username,))


# ── 配置 CRUD ──────────────────────────────────────────────
def db_load_config() -> dict[str, Any]:
    """加载配置"""
    with db_transaction() as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        cfg: dict[str, Any] = {}
        for r in rows:
            v = r["value"]
            # 尝试解析 JSON 数组
            if v.startswith("["):
                try:
                    v = json_mod.loads(v)
                except json_mod.JSONDecodeError:
                    pass
            elif v.lower() in ("true", "false"):
                v = v.lower() == "true"
            cfg[r["key"]] = v
        return cfg


def db_save_config(cfg_dict: dict[str, Any]) -> None:
    """保存配置"""
    with db_transaction() as conn:
        for k, v in cfg_dict.items():
            if isinstance(v, (list, dict)):
                v = json_mod.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                v = str(v).lower()
            else:
                v = str(v)
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, v))


# ── 日志 CRUD ──────────────────────────────────────────────
def db_write_log(username: str, action: str, detail: str = "", target: str = "", ip: str = "") -> None:
    """写操作日志（自动限制最近1000条）"""
    with db_transaction() as conn:
        conn.execute(
            "INSERT INTO logs (time, username, action, target, detail, ip) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, action, target, detail, ip)
        )
        # 清理超过1000条的旧日志
        conn.execute("DELETE FROM logs WHERE rowid NOT IN (SELECT rowid FROM logs ORDER BY rowid DESC LIMIT 1000)")


def db_load_logs(limit: int = 200) -> list[dict[str, Any]]:
    """加载日志"""
    with db_transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def db_clear_logs() -> None:
    """清空日志"""
    with db_transaction() as conn:
        conn.execute("DELETE FROM logs")


# ── 推送历史 CRUD ──────────────────────────────────────────
def db_save_push_history(customer: str, domain: str, channels: list[str], status: str, message: str = "") -> None:
    """保存推送历史"""
    with db_transaction() as conn:
        conn.execute(
            "INSERT INTO push_history (time, cert_customer, cert_domain, channels, status, message) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer, domain,
             json_mod.dumps(channels, ensure_ascii=False), status, message)
        )


def db_load_push_history(limit: int = 100) -> list[dict[str, Any]]:
    """加载推送历史"""
    with db_transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM push_history ORDER BY time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── 统计 ───────────────────────────────────────────────────
def db_calc_stats() -> dict[str, int]:
    """计算统计信息"""
    with db_transaction() as conn:
        total = conn.execute("SELECT COUNT(*) FROM certs").fetchone()[0]
        expired = conn.execute("SELECT COUNT(*) FROM certs WHERE remind_enabled=1 AND handled=0 AND expire_date < datetime('now')").fetchone()[0]
        expiring = conn.execute("""SELECT COUNT(*) FROM certs 
                                   WHERE remind_enabled=1 AND handled=0 
                                   AND expire_date >= datetime('now')
                                   AND expire_date <= datetime('now', '+7 days')""").fetchone()[0]
        disabled = conn.execute("SELECT COUNT(*) FROM certs WHERE remind_enabled=0").fetchone()[0]
        return {"total": total, "normal": total - expired - expiring - disabled,
                "expiring": expiring, "expired": expired, "disabled": disabled}
