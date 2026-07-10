import sys, os, tempfile, pathlib
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DATA_DIR"] = str(tmp)

import data
data.BASE_DIR = str(tmp)
data.DATA_DIR = str(tmp)
data.DATA_FILE = str(tmp / "certs.json")
data.CONFIG_FILE = str(tmp / "config.json")
data.USERS_FILE = str(tmp / "users.json")
data.LOGS_FILE = str(tmp / "logs.json")
data.SECRET_KEY_FILE=*** / ".secret_key")

import db
db.DB_PATH = str(tmp / "monitor.db")
db.init_db()

from app import app
app.config["TESTING"] = True

with app.test_request_context("/"):
    from flask import current_app
    print(f"current_app.testing: {current_app.testing}")
    from auth import _check_api_csrf
    result = _check_api_csrf()
    print(f"_check_api_csrf result: {result}")
