# -*- coding: utf-8 -*-
"""
钉钉推送模块
支持自定义机器人（加签模式）和企业微信机器人
"""
import hashlib
import hmac
import base64
import json
import logging
import time
import urllib.parse
import requests

logger = logging.getLogger(__name__)


def send_dingtalk_card(webhook_url, title, content, secret="", at_user_ids=None):
    """
    发送钉钉 Markdown 卡片消息
    
    Args:
        webhook_url: 钉钉机器人 Webhook 地址
        title: 消息标题
        content: Markdown 格式的消息内容
        secret: 加签密钥（如果使用加签模式）
        at_user_ids: 需要 @ 的用户 ID 列表
    
    Returns:
        bool: 发送是否成功
    """
    try:
        # 构建消息体
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }
        
        # 如果需要 @ 特定用户
        if at_user_ids:
            message["at"] = {
                "atUserIds": at_user_ids,
                "isAtAll": False
            }
        
        # 如果有 secret，使用加签模式
        if secret:
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            sign_url = urllib.parse.quote_plus(
                base64.b64encode(hmac_code).decode("utf-8")
            )
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign_url}"
        
        # 发送请求
        response = requests.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        result = response.json()
        if result.get("errcode") == 0:
            logger.info("钉钉推送成功")
            return True
        else:
            logger.error(f"钉钉推送失败: {result}")
            return False
            
    except Exception as e:
        logger.error(f"钉钉推送异常: {e}")
        return False


def build_remind_card(certs, users_map):
    """
    构建钉钉提醒卡片内容
    
    Args:
        certs: 证书列表
        users_map: 用户映射表
    
    Returns:
        tuple: (title, content, at_user_ids)
    """
    title = "🔔 证书到期提醒"
    
    # 收集需要 @ 的用户
    at_user_ids = []
    content_parts = [f"## {title}\\n\\n"]
    
    for cert in certs:
        customer = cert.get("customer", "")
        cert_type = cert.get("cert_type", "")
        domain = cert.get("domain", "")
        expire_date = cert.get("expire_date", "")
        days_left = cert.get("days_left", 0)
        
        # 确定状态描述
        if days_left < 0:
            status = f"❌ 已过期 {abs(days_left):.0f} 天"
            color = "#FF0000"
        elif days_left == 0:
            status = f"⚠️ 今日到期"
            color = "#FF8C00"
        elif days_left <= 7:
            status = f"🔶 {days_left:.0f} 天后到期"
            color = "#FFA500"
        elif days_left <= 30:
            status = f"🟡 {days_left:.0f} 天后到期"
            color = "#FFD700"
        else:
            status = f"🟢 {days_left:.0f} 天后到期"
            color = "#32CD32"
        
        content_parts.append(f"> ### {customer}\\n")
        content_parts.append(f"- **类型**: {cert_type}\\n")
        content_parts.append(f"- **域名**: {domain}\\n")
        content_parts.append(f"- **到期**: {expire_date}\\n")
        content_parts.append(f"- **状态**: <font color='{color}'>{status}</font>\\n\\n")
        
        # 收集负责人
        responsible_users = cert.get("responsible_users", [])
        for uname in responsible_users:
            if uname not in at_user_ids and uname in users_map:
                at_user_ids.append(uname)
    
    content = "".join(content_parts)
    
    return title, "".join(content_parts), at_user_ids


def send_wecom(webhook_url, message):
    """
    发送企业微信消息
    
    Args:
        webhook_url: 企业微信机器人 Webhook 地址
        message: 消息内容
    
    Returns:
        bool: 发送是否成功
    """
    try:
        payload = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        result = response.json()
        if result.get("errcode") == 0:
            logger.info("企业微信推送成功")
            return True
        else:
            logger.error(f"企业微信推送失败: {result}")
            return False
            
    except Exception as e:
        logger.error(f"企业微信推送异常: {e}")
        return False
