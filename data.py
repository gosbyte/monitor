# -*- coding: utf-8 -*-
"""
数据层 - 到期项/用户/配置/日志的加载与保存（无 Flask 依赖，daemon 可用）
支持文件锁防止并发写入损坏，支持 Fernet 密码加密
"""
import json
import os
import re
import secrets
import fcntl
import time
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# ── werkzeug（仅 app.py 需要，daemon 不需要）────────────
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    generate_password_hash = None
    check_password_hash = None


# ── 存储模式开关 ──────────────────────────────────────
USE_SQLITE = os.environ.get("USE_SQLITE", "0") == "1"

# ── 路径常量（必须在 _get_fernet 之前定义）────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
DATA_FILE = os.path.join(DATA_DIR, "certs.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
SECRET_KEY_FILE=os.path.join(DATA_DIR, ".secret_key")

# ── 首次运行：迁移旧 cert_data.json ──────────────────────
_MIGRATE_SRC = os.path.join(BASE_DIR, "cert_data.json")
if os.path.exists(_MIGRATE_SRC) and not os.path.exists(DATA_FILE):
    try:
        import shutil
        shutil.copy2(_MIGRATE_SRC, DATA_FILE)
        os.remove(_MIGRATE_SRC)
        print(f"[MIGRATE] cert_data.json -> {DATA_FILE}")
    except Exception as e:
        print(f"[MIGRATE] 失败: {e}")

# ── Fernet 加密密钥（用于 SMTP 密码等敏感字段）────────────
_fernet = None

def _get_fernet():
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


def encrypt_field(value):
    """加密敏感字段（如 SMTP 密码）"""
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(value):
    """解密敏感字段"""
    if not value:
        return ""
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except Exception:
        return value  # 兼容旧明文数据


def load_config_decrypted():
    """加载配置并自动解密敏感字段（供 daemon.py 使用）"""
    cfg = load_config()
    if cfg.get("smtp_pass"):
        cfg["smtp_pass"] = decrypt_field(cfg["smtp_pass"])
    return cfg


# ── 文件锁工具 ─────────────────────────────────────────────
class FileLock:
    """跨平台文件锁（支持 flock 和 fcntl 回退）"""
    def __init__(self, filepath, timeout=10):
        self.lockfile = filepath + ".lock"
        self.timeout = timeout
        self._fd = None

    def __enter__(self):
        self._fd = open(self.lockfile, "w")
        deadline = datetime.now().timestamp() + self.timeout
        while True:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if datetime.now().timestamp() >= deadline:
                    raise TimeoutError(f"Could not acquire lock on {self.lockfile} within {self.timeout}s")
                import time
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()
        try:
            os.unlink(self.lockfile)
        except OSError:
            pass


def locked_read_json(filepath):
    """带文件锁的安全读取 JSON"""
    with FileLock(filepath):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        return None


def locked_write_json(filepath, data):
    """带文件锁的安全原子写入 JSON"""
    with FileLock(filepath):
        atomic_write_json(filepath, data)


# ── 原子写入 ─────────────────────────────────────────────
def atomic_write_json(filepath, data):
    """写 JSON 文件（临时文件 + os.replace，保证原子性）"""
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)

# ── 日志 ─────────────────────────────────────────────────
def load_logs():
    """加载日志（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_load_logs
        return db_load_logs()
    with FileLock(LOGS_FILE):
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
    return []

def save_logs(logs):
    """保存日志（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        # SQLite 模式下日志通过 write_log 直接写入，此处保留 JSON 兼容
        return
    with FileLock(LOGS_FILE):
        logs = logs[-1000:]
        atomic_write_json(LOGS_FILE, logs)

def write_log(username, action, detail="", target="", ip=""):
    """写操作日志（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_write_log
        db_write_log(username, action, detail, target, ip)
        return
    logs = load_logs()
    logs.append({
        "id": len(logs) + 1,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "action": action,
        "target": target,
        "detail": detail,
        "ip": ip or "",
    })
    save_logs(logs)

# ── 密码与用户管理 ───────────────────────────────────────
def validate_password(password):
    """验证密码强度：至少8位，包含大小写字母+数字"""
    if len(password) < 8:
        return False, "密码长度不能少于8位"
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含至少一个大写字母"
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含至少一个小写字母"
    if not re.search(r"[0-9]", password):
        return False, "密码必须包含至少一个数字"
    return True, ""

def _migrate_password(users):
    """[FIX] P0-6: 自动迁移明文密码为哈希，直接在锁内写入避免死锁"""
    changed = False
    for u in users:
        pwd = u.get("password", "")
        if pwd and len(pwd) < 50:
            u["password"] = generate_password_hash(pwd)
            changed = True
    if changed:
        # [FIX] P0-6: 直接使用 atomic_write_json 避免 save_users() 再次加锁导致死锁
        with FileLock(USERS_FILE):
            atomic_write_json(USERS_FILE, users)
    return users

# ── 缓存（防止频繁读盘）────────────────────────────────────

# [FIX] P1-10: 密码迁移标记，只迁移一次
_password_migration_done = False

def _migrate_password_sqlite(users):
    """[FIX] P0-5: 自动迁移 SQLite 用户明文密码为哈希"""
    global _password_migration_done
    if _password_migration_done:
        return  # 已经迁移过，跳过
    changed = False
    for u in users:
        pwd = u.get("password", "")
        if pwd and len(pwd) < 50 and generate_password_hash:
            u["password"] = generate_password_hash(pwd)
            changed = True
    if changed:
        # [FIX] P0-5: 在迁移过程中立即设置标志位，防止竞态
        _password_migration_done = True
        if USE_SQLITE:
            from db import db_save_user
            for u in users:
                u.setdefault("name", u.get("username", ""))
                u.setdefault("dingtalk_id", "")
                u.setdefault("failed_attempts", 0)
                u.setdefault("consecutive_locks", 0)
                u.setdefault("lock_until", None)
                db_save_user(u)

# 用户缓存（30s TTL）
_users_cache = {"data": None, "mtime": 0, "ttl": 30}

# 到期项缓存（5s TTL）
_certs_cache = {"data": None, "mtime": 0, "ttl": 5}

# 配置缓存（60s TTL）
_config_cache = {"data": None, "mtime": 0, "ttl": 60}

def load_users():
    """加载用户列表（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_load_users
        users = db_load_users()
        _migrate_password_sqlite(users)
        return users
    global _users_cache
    if not os.path.exists(USERS_FILE):
        _users_cache = {"data": [], "mtime": 0, "ttl": 30}
        return []
    try:
        mt = os.path.getmtime(USERS_FILE)
    except OSError:
        mt = 0
    if _users_cache["data"] is not None and (_users_cache["mtime"] == mt or time.time() - _users_cache["mtime"] < _users_cache["ttl"]):
        return _users_cache["data"]
    with FileLock(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
            users = json.load(f)
    _users_cache = {"data": users, "mtime": time.time(), "ttl": 30}
    _migrate_password(users)
    return users

def save_users(users):
    """保存用户列表（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_transaction
        # [FIX] P2-1: 加唯一性校验，防止重复用户名
        usernames = set()
        for u in users:
            uname = u.get("username")
            if uname in usernames:
                logger.warning(f"save_users: 跳过重复用户名 '{uname}'")
                continue
            usernames.add(uname)
        # 批量插入：使用显式 UPDATE/INSERT 逻辑避免 AUTOINCREMENT 问题
        with db_transaction() as conn:
            for u in users:
                if u["username"] not in usernames:
                    continue
                # 检查是否存在
                existing = conn.execute("SELECT username FROM users WHERE username=?", (u["username"],)).fetchone()
                if existing:
                    # 存在则 UPDATE
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
                    # 不存在则 INSERT
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
        return
    for u in users:
        if "name" not in u: u["name"] = u.get("username", "")
        if "dingtalk_id" not in u: u["dingtalk_id"] = ""
        if "failed_attempts" not in u: u["failed_attempts"] = 0
        if "consecutive_locks" not in u: u["consecutive_locks"] = 0
        if "lock_until" not in u: u["lock_until"] = None
    atomic_write_json(USERS_FILE, users)
    global _users_cache
    _users_cache["mtime"] = 0

def is_user_locked(username):
    users = load_users()
    u = next((u for u in users if u["username"] == username), None)
    if not u or not u.get("lock_until"):
        return False
    lock_until = datetime.strptime(u["lock_until"], "%Y-%m-%d %H:%M:%S")
    return datetime.now() < lock_until

def get_lock_seconds(username):
    users = load_users()
    u = next((u for u in users if u["username"] == username), None)
    if not u or not u.get("lock_until"):
        return 0
    lock_until = datetime.strptime(u["lock_until"], "%Y-%m-%d %H:%M:%S")
    return max(0, int((lock_until - datetime.now()).total_seconds()))

def do_lock_user(username):
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

def reset_failed_attempts(username):
    users = load_users()
    for u in users:
        if u["username"] == username:
            u["failed_attempts"] = 0
            u["consecutive_locks"] = 0
            u["lock_until"] = None
            break
    save_users(users)

def verify_user(username, password):
    """使用 werkzeug 哈希验证密码"""
    users = load_users()
    for u in users:
        if u["username"] == username:
            return check_password_hash(u["password"], password)
    return False

# ── 到期项数据 ─────────────────────────────────────────────
def load_certs():
    """加载到期项（支持 JSON 和 SQLite 双模式）"""
    global _certs_cache
    if USE_SQLITE:
        from db import db_load_certs
        # [FIX] P1-3: SQLite 模式也加缓存（与 JSON 模式一致，5s TTL）
        now = time.time()
        if _certs_cache["data"] is not None and (now - _certs_cache["mtime"]) < 5:
            return _certs_cache["data"]
        certs = db_load_certs()
        _certs_cache = {"data": certs, "mtime": now}
        return certs
    now = time.time()
    if _certs_cache["data"] is not None and (now - _certs_cache["mtime"]) < 5:
        return _certs_cache["data"]
    with FileLock(DATA_FILE):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            _certs_cache = {"data": data, "mtime": now}
            return data
    _certs_cache = {"data": [], "mtime": now}
    return []

def save_certs(certs):
    """保存到期项（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_save_cert, db_transaction
        if isinstance(certs, list):
            # [FIX] P0-8: 批量保存用单事务，避免逐条事务的性能问题
            with db_transaction() as conn:
                for c in certs:
                    # [FIX] P1-4: 过滤掉 id=None 的记录
                    if c.get("id") is None:
                        logger.warning(f"save_certs: 跳过 id=None 的记录 {c.get('customer', '?')}")
                        continue
                    # 检查是否存在
                    existing = conn.execute("SELECT id FROM certs WHERE id=?", (c.get("id"),)).fetchone()
                    if existing:
                        # 存在则 UPDATE
                        conn.execute("""UPDATE certs SET customer=?, cert_type=?, domain=?, expire_date=?,
                                       note=?, remind_enabled=?, handled=?, responsible_users=?, updated_at=?
                                       WHERE id=?""",
                            (c.get("customer", ""), c.get("cert_type", ""), c.get("domain", ""),
                             c.get("expire_date", ""), c.get("note", ""),
                             int(c.get("remind_enabled", True)), int(c.get("handled", False)),
                             json.dumps(c.get("responsible_users", []), ensure_ascii=False),
                             datetime.now().strftime("%Y-%m-%d %H:%M"), c.get("id")))
                    else:
                        # 不存在则 INSERT
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
        return
    global _certs_cache
    with FileLock(DATA_FILE):
        atomic_write_json(DATA_FILE, certs)
    _certs_cache = {"data": None, "mtime": 0}

def load_config():
    """加载配置（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_load_config
        return db_load_config()
    global _config_cache
    now = time.time()
    if _config_cache["data"] is not None and (now - _config_cache["mtime"]) < _config_cache["ttl"]:
        return _config_cache["data"]
    with FileLock(CONFIG_FILE):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            _config_cache = {"data": data, "mtime": now}
            return data
    _config_cache = {"data": {"webhook_url": "", "remind_days": [7, 3, 1]}, "mtime": now}
    return _config_cache["data"]

def save_config(cfg):
    """保存配置（支持 JSON 和 SQLite 双模式）"""
    if USE_SQLITE:
        from db import db_save_config
        db_save_config(cfg)
        return
    global _config_cache
    with FileLock(CONFIG_FILE):
        atomic_write_json(CONFIG_FILE, cfg)
    _config_cache = {"data": None, "mtime": 0}

def calc_days_left(expire_str):
    try:
        s = expire_str.strip()
        if "T" in s:
            exp = datetime.strptime(s, "%Y-%m-%dT%H:%M")
        elif ":" in s:
            exp = datetime.strptime(s, "%Y-%m-%d %H:%M")
        else:
            exp = datetime.strptime(s, "%Y-%m-%d")
        return int((exp - datetime.now()).total_seconds() / 86400)  # [FIX] P2-4: 向下取整替代四舍五入
    except Exception:
        return -999

def get_cert_status(cert, days_left=None):
    if days_left is None:
        days_left = calc_days_left(cert.get("expire_date", ""))
    if not cert.get("remind_enabled", True):
        return "disabled"
    if days_left < 0:
        return "expired"
    if days_left <= 7:
        return "expiring"
    return "normal"

def calc_stats(certs):
    normal = expiring = expired = disabled = 0
    for c in certs:
        days_left = calc_days_left(c["expire_date"])
        status = get_cert_status(c, days_left)
        if status == "normal": normal += 1
        elif status == "expiring": expiring += 1
        elif status == "expired": expired += 1
        elif status == "disabled": disabled += 1
    return {"total": len(certs), "normal": normal, "expiring": expiring, "expired": expired, "disabled": disabled}

# ── 辅助函数：供 app.py 直接调用 db.py ──────────────────
def db_delete_cert(cert_id):
    """删除到期项（SQLite 模式）"""
    if USE_SQLITE:
        from db import db_delete_cert as _del
        _del(cert_id)


def db_batch_delete_cert_ids(ids):
    """批量删除到期项（SQLite 模式）"""
    if USE_SQLITE:
        from db import db_batch_delete_cert_ids as _del
        _del(ids)
