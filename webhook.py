# -*- coding: utf-8 -*-
"""
Webhook 回调模块 - 支持第三方系统接入
"""
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


def send_webhook(url, payload, timeout=10):
    """发送 Webhook 回调"""
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        if response.status_code == 200:
            logger.info(f"Webhook 发送成功: {url}")
            return True
        else:
            logger.warning(f"Webhook 返回非 200 状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Webhook 发送失败: {e}")
        return False


def build_item_expiry_payload(cert, days_left):
    """构建到期项到期 Webhook 载荷"""
    return {
        "event": "item_expiry",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "id": cert.get("id"),
            "customer": cert.get("customer", ""),
            "cert_type": cert.get("cert_type", ""),
            "domain": cert.get("domain", ""),
            "expire_date": cert.get("expire_date", ""),
            "days_left": days_left,
            "remind_enabled": cert.get("remind_enabled", True),
            "handled": cert.get("handled", False),
        }
    }


def build_item_added_payload(cert):
    """构建到期项新增 Webhook 载荷"""
    return {
        "event": "item_added",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "id": cert.get("id"),
            "customer": cert.get("customer", ""),
            "cert_type": cert.get("cert_type", ""),
            "domain": cert.get("domain", ""),
            "expire_date": cert.get("expire_date", ""),
            "created_by": cert.get("created_by", ""),
        }
    }


def build_item_deleted_payload(cert_id, customer):
    """构建到期项删除 Webhook 载荷"""
    return {
        "event": "item_deleted",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "id": cert_id,
            "customer": customer,
        }
    }
