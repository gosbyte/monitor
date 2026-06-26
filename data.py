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
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

# ── werkzeug（仅 app.py 需要，daemon 不需要）────────────
try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    generate_password_hash = None
    check_password_hash = None

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
    """加载日志（带文件锁）"""
    with FileLock(LOGS_FILE):
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
    return []

def save_logs(logs):
    """保存日志（带文件锁）"""
    with FileLock(LOGS_FILE):
        logs = logs[-1000:]
        atomic_write_json(LOGS_FILE, logs)

def write_log(username, action, detail="", target="", ip=""):
    """写操作日志（daemon 无 web 请求，ip 传空字符串）"""
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
    """[FIX] P0: 自动迁移明文密码为哈希"""
    changed = False
    for u in users:
        pwd = u.get("password", "")
        if pwd and len(pwd) < 50:
            u["password"] = generate_password_hash(pwd)
            changed = True
    if changed:
        save_users(users)
    return users

# ── 缓存（防止频繁读盘）────────────────────────────────────
# 用户缓存（30s TTL）
_users_cache = {"data": None, "mtime": 0}

# 到期项缓存（5s TTL）
_certs_cache = {"data": None, "mtime": 0}

def load_users():
    """加载用户列表（带文件锁 + mtime 缓存）"""
    global _users_cache
    if not os.path.exists(USERS_FILE):
        _users_cache = {"data": [], "mtime": 0}
        return []
    try:
        mt = os.path.getmtime(USERS_FILE)
    except OSError:
        mt = 0
    if _users_cache["data"] is not None and _users_cache["mtime"] == mt:
        return _users_cache["data"]
    with FileLock(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
            users = json.load(f)
    _users_cache = {"data": users, "mtime": mt}
    _migrate_password(users)
    return users

def save_users(users):
    """保存用户列表（带字段补全）"""
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
    """加载到期项（带文件锁 + 缓存）"""
    global _certs_cache
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
    """保存到期项（带文件锁 + 清除缓存）"""
    global _certs_cache
    with FileLock(DATA_FILE):
        atomic_write_json(DATA_FILE, certs)
    _certs_cache = {"data": None, "mtime": 0}

def load_config():
    """加载配置（带文件锁）"""
    with FileLock(CONFIG_FILE):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
    return {"webhook_url": "", "remind_days": [7, 3, 1]}

def save_config(cfg):
    """保存配置（带文件锁）"""
    with FileLock(CONFIG_FILE):
        atomic_write_json(CONFIG_FILE, cfg)

def calc_days_left(expire_str):
    try:
        s = expire_str.strip()
        if "T" in s:
            exp = datetime.strptime(s, "%Y-%m-%dT%H:%M")
        elif ":" in s:
            exp = datetime.strptime(s, "%Y-%m-%d %H:%M")
        else:
            exp = datetime.strptime(s, "%Y-%m-%d")
        return (exp - datetime.now()).total_seconds() / 86400
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
