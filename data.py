# -*- coding: utf-8 -*-
"""
数据层 - 到期项/用户/配置/日志的加载与保存（无 Flask 依赖，daemon 可用）
统一使用 SQLite 存储，支持 Fernet 密码加密
支持环境变量覆盖配置默认值 + .env 文件 + 配置热更新
"""
from __future__ import annotations

import json
import os
import re
import time
import logging
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from cache import LRUCache

logger = logging.getLogger(__name__)

# ── werkzeug（仅 app.py 需要，daemon 不需要）────────────
try:
    from werkzeug.security import generate_password_hash, check_password_hash  # type: ignore[import-untyped]
except ImportError:
    generate_password_hash = None  # type: ignore[assignment]
    check_password_hash = None  # type: ignore[assignment]


# ── 存储模式：统一 SQLite ──────────────────────────────────────
USE_SQLITE: bool = True

# ── 路径常量（必须在 _get_fernet 之前定义）────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
DATA_FILE = os.path.join(DATA_DIR, "certs.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
SECRET_KEY_FILE = os.path.join(DATA_DIR, ".secret_key")

# ── 日志清理配置 ───────────────────────────────────────────
LOG_CLEANUP_MAX_SIZE_MB: int = int(os.environ.get("LOG_CLEANUP_MAX_SIZE_MB", "50"))
LOG_CLEANUP_DIRS: list[str] = [DATA_DIR]  # 可被环境变量扩展

# ── 统一缓存实例 ──────────────────────────────────────────
# certs_cache: 缓存到期项列表（默认 TTL 30s，最大 5 条）
certs_cache = LRUCache(maxsize=5, ttl=30.0)
# users_cache: 缓存用户列表（默认 TTL 30s，最大 5 条）
users_cache = LRUCache(maxsize=5, ttl=30.0)
# config_cache: 缓存配置字典（默认 TTL 60s，最大 5 条）
config_cache = LRUCache(maxsize=5, ttl=60.0)

# ── 旧配置缓存（向后兼容，保留 reload_config 逻辑）───────────
_config_cache: dict[str, Any] = {}
_config_cache_mtime: float = 0

_fernet: Fernet | None = None


#
# ── .env 文件支持 ──────────────────────────────────────────
#


def _load_dotenv() -> None:
    """加载项目根目录下的 .env 文件（如果存在），但不覆盖已有环境变量"""
    dotenv_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # 去除引号
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    # 仅在不冲突时设置（不覆盖已有环境变量）
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as e:
            logger.warning(f"加载 .env 文件失败: {e}")


# 模块加载时自动读取 .env
_load_dotenv()


#
# ── Fernet 加密密钥（用于 SMTP 密码等敏感字段）────────────
#


def _get_fernet() -> Fernet:
    """延迟初始化 Fernet 实例"""
    global _fernet
    if _fernet is not None:
        return _fernet
    key_env = os.environ.get("ENCRYPTION_KEY")
    if key_env:
        _fernet = Fernet(key_env.encode() if isinstance(key_env, str) else key_env)
        return _fernet
    key_file = os.path.join(DATA_DIR, ".encryption_key")
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            _fernet = Fernet(f.read())
    else:
        _fernet = Fernet(Fernet.generate_key())
        with open(key_file, "wb") as f:
            _fernet._key = f.read()
    return _fernet


def encrypt_field(value: str | None) -> str:
    """加密敏感字段（如 SMTP 密码）"""
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """解密敏感字段"""
    if not value:
        return ""
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except Exception:
        return value  # 兼容旧明文数据


def load_config_decrypted() -> dict[str, Any]:
    """加载配置并自动解密敏感字段（供 daemon.py 使用）"""
    cfg = load_config()
    if cfg.get("smtp_pass"):
        cfg["smtp_pass"] = decrypt_field(cfg["smtp_pass"])
    return cfg


#
# ── 日志 ─────────────────────────────────────────────────
#


def load_logs(limit: int = 200) -> list[dict[str, Any]]:
    """加载日志（SQLite）"""
    from db import db_load_logs
    return db_load_logs(limit)


def save_logs(logs: list[dict[str, Any]]) -> None:
    """清空日志（SQLite）"""
    from db import db_clear_logs
    db_clear_logs()


def write_log(username: str, action: str, detail: str = "", target: str = "", ip: str = "") -> None:
    """写操作日志（SQLite）"""
    from db import db_write_log
    db_write_log(username, action, detail, target, ip)


#
# ── 密码与用户管理 ───────────────────────────────────────
#

# 常见弱密码列表（小写比较）
_COMMON_PASSWORDS: frozenset[str] = frozenset({
    "password", "password1", "password123", "password1234", "password12345",
    "admin", "admin123", "admin1234", "admin12345",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "111111", "12345678901234567890",
    "qwerty", "qwerty123", "abc123",
    "letmein", "monkey", "dragon", "master",
    "iloveyou", "sunshine", "princess", "football",
    "welcome", "shadow", "superman", "michael",
    "test", "test123", "root", "toor",
    "changeme", "default", "passw0rd", "p@ssw0rd",
})


def _password_strength_score(password: str) -> int:
    """计算密码强度分数（0-100）"""
    score = 0
    length = len(password)

    # 长度得分（最高 30 分）
    if length >= 8:
        score += 10
    if length >= 12:
        score += 10
    if length >= 16:
        score += 10

    # 字符种类得分（最高 60 分）
    if re.search(r"[a-z]", password):
        score += 10
    if re.search(r"[A-Z]", password):
        score += 15
    if re.search(r"[0-9]", password):
        score += 15
    if re.search(r"[^a-zA-Z0-9]", password):
        score += 20  # 特殊字符加分更多

    # 惩罚：常见密码直接 0 分
    if password.lower() in _COMMON_PASSWORDS:
        return 0

    # 惩罚：纯数字或纯字母
    if password.isdigit():
        score = min(score, 15)
    if password.isalpha():
        score = min(score, 20)

    return min(score, 100)


_STRENGTH_LABELS: dict[tuple[int, int], str] = {
    (0, 20): "极弱",
    (21, 40): "弱",
    (41, 60): "中等",
    (61, 80): "强",
    (81, 100): "极强",
}


def _strength_label(score: int) -> str:
    """将分数映射为标签"""
    for (low, high), label in _STRENGTH_LABELS.items():
        if low <= score <= high:
            return label
    return "未知"


def validate_password(password: str) -> tuple[bool, str, int, str]:
    """验证密码强度：最小12位，禁止常见密码，返回 (valid, message, score, label)

    要求：
    - 最少 12 位
    - 不能是常见弱密码
    - 必须包含大写字母、小写字母、数字
    - 返回强度评分（0-100）和等级标签
    """
    if not password:
        return False, "密码不能为空", 0, "极弱"

    # 长度检查
    if len(password) < 12:
        return False, "密码长度不能少于12位", 0, "极弱"

    # 常见密码检查
    if password.lower() in _COMMON_PASSWORDS:
        return False, "该密码过于常见，请使用更复杂的密码", 0, "极弱"

    score = _password_strength_score(password)

    if score == 0:
        return False, "该密码过于常见，请使用更复杂的密码", 0, "极弱"

    # 字符复杂度
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"[0-9]", password))

    if not has_upper:
        return False, "密码必须包含至少一个大写字母", score, _strength_label(score)
    if not has_lower:
        return False, "密码必须包含至少一个小写字母", score, _strength_label(score)
    if not has_digit:
        return False, "密码必须包含至少一个数字", score, _strength_label(score)

    label = _strength_label(score)
    return True, f"密码强度：{label}（{score}/100）", score, label


def load_users() -> list[dict[str, Any]]:
    """加载用户列表（SQLite），带缓存"""
    cached = users_cache.get("all")
    if cached is not None:
        return cached
    from db import db_load_users
    users = db_load_users()
    # 自动迁移明文密码为哈希
    _migrate_password_sqlite(users)
    users_cache.set("all", users)
    return users


def save_users(users: list[dict[str, Any]]) -> None:
    """保存用户列表（SQLite），清除缓存"""
    from db import db_transaction
    # 唯一性校验，防止重复用户名
    usernames: set[str] = set()
    for u in users:
        uname = u.get("username")
        if not uname:
            continue
        if uname in usernames:
            logger.warning(f"save_users: 跳过重复用户名 '{uname}'")
            continue
        usernames.add(uname)
    # 批量插入/更新
    with db_transaction() as conn:
        for u in users:
            if u["username"] not in usernames:
                continue
            existing = conn.execute("SELECT username FROM users WHERE username=?", (u["username"],)).fetchone()
            if existing:
                conn.execute("""UPDATE users SET name=?, password=?, dingtalk_id=?,
                              role=?, email=?, failed_attempts=?, consecutive_locks=?, lock_until=?, force_change_password=?
                              WHERE username=?""",
                    (u.get("name", u.get("username", "")),
                     u["password"], u.get("dingtalk_id", ""),
                     u.get("role", "user"), u.get("email", ""),
                     u.get("failed_attempts", 0),
                     u.get("consecutive_locks", 0),
                     u.get("lock_until"),
                     int(u.get("force_change_password", 1)),
                     u["username"]))
            else:
                conn.execute("""INSERT INTO users (username, name, password, dingtalk_id,
                           role, email, failed_attempts, consecutive_locks, lock_until, force_change_password)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (u["username"], u.get("name", u.get("username", "")),
                     u["password"], u.get("dingtalk_id", ""),
                     u.get("role", "user"), u.get("email", ""),
                     u.get("failed_attempts", 0),
                     u.get("consecutive_locks", 0),
                     u.get("lock_until"),
                     int(u.get("force_change_password", 1))))
    # 清除用户缓存
    users_cache.clear()


def _migrate_password_sqlite(users: list[dict[str, Any]]) -> None:
    """自动迁移 SQLite 用户明文密码为哈希"""
    changed = False
    for u in users:
        pwd = u.get("password", "")
        if pwd and len(pwd) < 50 and generate_password_hash:
            u["password"] = generate_password_hash(pwd)
            changed = True
    if changed:
        from db import db_save_user
        for u in users:
            u.setdefault("name", u.get("username", ""))
            u.setdefault("dingtalk_id", "")
            u.setdefault("failed_attempts", 0)
            u.setdefault("consecutive_locks", 0)
            u.setdefault("lock_until", None)
            db_save_user(u)


def is_user_locked(username: str) -> bool:
    users = load_users()
    u = next((u for u in users if u["username"] == username), None)
    if not u or not u.get("lock_until"):
        return False
    lock_until = datetime.strptime(u["lock_until"], "%Y-%m-%d %H:%M:%S")
    return datetime.now() < lock_until


def get_lock_seconds(username: str) -> int:
    users = load_users()
    u = next((u for u in users if u["username"] == username), None)
    if not u or not u.get("lock_until"):
        return 0
    lock_until = datetime.strptime(u["lock_until"], "%Y-%m-%d %H:%M:%S")
    return max(0, int((lock_until - datetime.now()).total_seconds()))


def do_lock_user(username: str) -> None:
    """锁定用户，指数递增（10/30/90/270/480min）"""
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["failed_attempts"] = 0
            u["consecutive_locks"] = u.get("consecutive_locks", 0) + 1
            multiplier = 3 ** (u["consecutive_locks"] - 1)
            minutes = min(10 * multiplier, 480)
            u["lock_until"] = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
            break
    save_users(users)


def reset_failed_attempts(username: str) -> None:
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["failed_attempts"] = 0
            u["consecutive_locks"] = 0
            u["lock_until"] = None
            break
    save_users(users)


def verify_user(username: str, password: str) -> bool:
    """使用 werkzeug 哈希验证密码"""
    users = load_users()
    for u in users:
        if u["username"] == username:
            return check_password_hash(u["password"], password)
    return False


#
# ── 到期项数据 ─────────────────────────────────────────────
#


def load_certs() -> list[dict[str, Any]]:
    """加载到期项（SQLite），带缓存"""
    cached = certs_cache.get("all")
    if cached is not None:
        return cached
    from db import db_load_certs
    result = db_load_certs()
    certs_cache.set("all", result)
    return result


def save_certs(certs: list[dict[str, Any]] | dict[str, Any]) -> None:
    """保存到期项（SQLite），清除缓存"""
    from db import db_save_cert, db_transaction
    if isinstance(certs, list):
        with db_transaction() as conn:
            for c in certs:
                if c.get("id") is None:
                    logger.warning(f"save_certs: 跳过 id=None 的记录 {c.get('customer', '?')}")
                    continue
                existing = conn.execute("SELECT id FROM certs WHERE id=?", (c.get("id"),)).fetchone()
                if existing:
                    conn.execute("""UPDATE certs SET customer=?, cert_type=?, domain=?, expire_date=?,
                                   note=?, remind_enabled=?, handled=?, responsible_users=?, updated_at=?
                                   WHERE id=?""",
                        (c.get("customer", ""), c.get("cert_type", ""), c.get("domain", ""),
                         c.get("expire_date", ""), c.get("note", ""),
                         int(c.get("remind_enabled", True)), int(c.get("handled", False)),
                         json.dumps(c.get("responsible_users", []), ensure_ascii=False),
                         datetime.now().strftime("%Y-%m-%d %H:%M"), c.get("id")))
                else:
                    conn.execute("""INSERT INTO certs (id, customer, cert_type, domain, expire_date, note,
                                  remind_enabled, handled, responsible_users, created_by, created_at, updated_at)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (c.get("id"), c.get("customer", ""), c.get("cert_type", ""), c.get("domain", ""),
                         c.get("expire_date", ""), c.get("note", ""), c.get("created_by", ""),
                         int(c.get("remind_enabled", True)), int(c.get("handled", False)),
                         json.dumps(c.get("responsible_users", []), ensure_ascii=False),
                         c.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M")),
                         datetime.now().strftime("%Y-%m-%d %H:%M")))
    else:
        if certs.get("id") is None:
            logger.warning(f"save_certs: 跳过 id=None 的单条记录 {certs.get('customer', '?')}")
            return
        db_save_cert(certs)
    # 清除到期项缓存
    certs_cache.clear()


# ── 配置加载/保存（支持环境变量覆盖 + 热更新）────────────

# 配置默认值（环境变量优先）
_CONFIG_DEFAULTS: dict[str, Any] = {
    "webhook_url": os.environ.get("MONITOR_WEBHOOK_URL", ""),
    "secret": os.environ.get("MONITOR_SECRET", ""),
    "remind_days": os.environ.get("MONITOR_REMIND_DAYS", "[30, 14, 7, 3, 1]"),
    "email_enabled": os.environ.get("MONITOR_EMAIL_ENABLED", "false"),
    "smtp_host": os.environ.get("MONITOR_SMTP_HOST", ""),
    "smtp_port": os.environ.get("MONITOR_SMTP_PORT", "465"),
    "smtp_user": os.environ.get("MONITOR_SMTP_USER", ""),
    "smtp_pass": os.environ.get("MONITOR_SMTP_PASS", ""),
    "smtp_to": os.environ.get("MONITOR_SMTP_TO", ""),
    "smtp_from_name": os.environ.get("MONITOR_SMTP_FROM_NAME", "Item Monitor"),
    "wecom_enabled": os.environ.get("MONITOR_WECOM_ENABLED", "false"),
    "wecom_webhook": os.environ.get("MONITOR_WECOM_WEBHOOK", ""),
}


def _apply_env_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    """用环境变量覆盖配置值（优先级：环境变量 > SQLite > 默认值）"""
    env_prefix = "MONITOR_"

    for key, default_val in _CONFIG_DEFAULTS.items():
        env_var = f"{env_prefix}{key.upper()}"
        env_val = os.environ.get(env_var)
        if env_val is not None:
            # 尝试解析 JSON（如 remind_days 的数组）
            if env_val.startswith("[") or env_val.startswith("{"):
                try:
                    cfg[key] = json.loads(env_val)
                    continue
                except json.JSONDecodeError:
                    pass
            # 布尔值
            if env_val.lower() in ("true", "false"):
                cfg[key] = env_val.lower() == "true"
            else:
                cfg[key] = env_val
        elif key not in cfg:
            # 数据库中不存在且环境变量也没设，用默认值
            cfg[key] = default_val

    return cfg


def load_config() -> dict[str, Any]:
    """加载配置（SQLite），带缓存，支持环境变量覆盖默认值"""
    from db import db_load_config

    cached = config_cache.get("all")
    if cached is not None:
        # 仍然应用环境变量覆盖（环境变量优先级高于缓存）
        cfg = dict(cached)
        cfg = _apply_env_overrides(cfg)
        _resolve_remind_days(cfg)
        return cfg

    cfg = db_load_config()

    # 用环境变量覆盖（优先于 SQLite 中的值）
    cfg = _apply_env_overrides(cfg)

    # 解析 remind_days 为整数列表
    _resolve_remind_days(cfg)

    # 缓存到统一缓存
    config_cache.set("all", cfg)

    return cfg


def _resolve_remind_days(cfg: dict[str, Any]) -> None:
    """将 remind_days 解析为整数列表（内联复用）"""
    rd = cfg.get("remind_days", [30, 14, 7, 3, 1])
    if isinstance(rd, str):
        try:
            rd = json.loads(rd)
        except json.JSONDecodeError:
            rd = [30, 14, 7, 3, 1]
    if isinstance(rd, list):
        rd = [int(x) for x in rd if str(x).strip().isdigit()]
        if not rd:
            rd = [30, 14, 7, 3, 1]
    cfg["remind_days"] = rd


def save_config(cfg: dict[str, Any]) -> None:
    """保存配置（SQLite），清除缓存"""
    from db import db_save_config
    db_save_config(cfg)
    config_cache.clear()


def reload_config() -> dict[str, Any]:
    """热更新配置：重新从 SQLite 加载并应用环境变量覆盖"""
    config_cache.clear()
    return load_config()


def calc_days_left(expire_str: str) -> int:
    try:
        s = expire_str.strip()
        if "T" in s:
            exp = datetime.strptime(s, "%Y-%m-%dT%H:%M")
        elif ":" in s:
            exp = datetime.strptime(s, "%Y-%m-%d %H:%M")
        else:
            exp = datetime.strptime(s, "%Y-%m-%d")
        return int((exp - datetime.now()).total_seconds() / 86400)
    except Exception:
        return -999


def get_cert_status(cert: dict[str, Any], days_left: int | None = None) -> str:
    if days_left is None:
        days_left = calc_days_left(cert.get("expire_date", ""))
    if not cert.get("remind_enabled", True):
        return "disabled"
    if days_left < 0:
        return "expired"
    if days_left <= 7:
        return "expiring"
    return "normal"


def calc_stats(certs: list[dict[str, Any]]) -> dict[str, int]:
    normal = expiring = expired = disabled = 0
    for c in certs:
        days_left = calc_days_left(c["expire_date"])
        status = get_cert_status(c, days_left)
        if status == "normal":
            normal += 1
        elif status == "expiring":
            expiring += 1
        elif status == "expired":
            expired += 1
        elif status == "disabled":
            disabled += 1
    return {"total": len(certs), "normal": normal, "expiring": expiring, "expired": expired, "disabled": disabled}


# ── 辅助函数：供 app.py 直接调用 db.py ──────────────────
def db_delete_cert(cert_id: int) -> None:
    """删除到期项（SQLite 模式）"""
    from db import db_delete_cert as _del
    _del(cert_id)


def db_batch_delete_cert_ids(ids: list[int]) -> int:
    """批量删除到期项（SQLite 模式）"""
    from db import db_batch_delete_cert_ids as _del
    return _del(ids)


# ── JSON 迁移（供 init_data.py 调用）─────────────────
from db import migrate_json_to_sqlite  # noqa: E402
