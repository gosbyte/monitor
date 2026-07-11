# -*- coding: utf-8 -*-
"""共享请求工具函数"""
from __future__ import annotations


def get_client_ip(request) -> str:
    """获取客户端真实IP，支持代理场景"""
    # 优先从 X-Forwarded-For 获取（经过反向代理时）
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


def sanitize_filename(filename: str) -> str:
    """安全过滤文件名，防止路径穿越和HTTP响应拆分"""
    import re
    # 只保留字母、数字、下划线、连字符、点
    safe = re.sub(r"[^\w\-_.]", "_", filename)
    # 防止路径穿越
    safe = safe.replace("..", "").replace("/", "").replace("\\", "")
    return safe[:200]  # 限制长度
