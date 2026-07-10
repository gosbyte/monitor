# -*- coding: utf-8 -*-
"""页面路由 - add_batch 等额外页面"""
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

from data import load_users
from auth import admin_required


logger = logging.getLogger(__name__)


def register_page_routes(app: Flask):
    """注册页面路由"""

    @app.route("/add_batch")
    @admin_required
    def add_batch_page():
        users = load_users()
        current_username = session.get("username", "")
        current_user = next((u for u in users if u["username"] == current_username), None)
        is_admin = current_user.get("role") == "admin" if current_user else False
        return render_template("add_batch.html", is_admin=is_admin)
