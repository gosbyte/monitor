# -*- coding: utf-8 -*-
"""
钉钉推送模块
支持自定义机器人（加签模式）和企业微信机器人
"""
from __future__ import annotations

import hashlib
import hmac
import base64
import json
import logging
import time
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger(__name__)


def send_dingtalk_card(
    webhook_url: str,
    title: str,
    content: str,
    secret: str = "",
    at_mobiles: list[str] | None = None,
    at_user_ids: list[str] | None = None,
) -> bool:
    """
    发送钉钉 Markdown 卡片消息

    Args:
        webhook_url: 钉钉机器人 Webhook 地址
        title: 消息标题
        content: Markdown 格式的消息内容
        secret: 加签密钥（如果使用加签模式）
        at_mobiles: 需要 @ 的手机号码列表（自定义机器人最稳妥的 @ 方式）
        at_user_ids: 需要 @ 的钉钉 userid 列表（企业内部机器人）

    Returns:
        bool: 发送是否成功
    """
    try:
        # 构建消息体
        message: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }

        # 如果需要 @ 特定用户（手机号或钉钉 userid，二选一或并存）
        _at: dict[str, Any] = {}
        if at_mobiles:
            _at["atMobiles"] = at_mobiles
        if at_user_ids:
            _at["atUserIds"] = at_user_ids
        if _at:
            _at["isAtAll"] = False
            message["at"] = _at
        
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


def build_remind_card(
    certs: list[dict[str, Any]],
    users_map: dict[str, dict[str, Any]],
) -> tuple[str, str, list[str], list[str]]:
    """
    构建钉钉提醒卡片内容

    Args:
        certs: 到期项列表
        users_map: 用户映射表（username -> user dict，含 dingtalk_id / name）

    Returns:
        tuple: (title, content, at_mobiles, at_user_ids)
        - at_mobiles: 钉钉 @ 用的手机号列表
        - at_user_ids: 钉钉 @ 用的 userid 列表
        消息正文中已嵌入对应的 @ 文本，确保钉钉能正确高亮/提醒。
    """
    import re
    _CN_MOBILE = re.compile(r"^1[3-9]\d{9}$")

    title = "🔔 证书到期提醒"

    at_mobiles: list[str] = []
    at_user_ids: list[str] = []
    mention_texts: list[str] = []  # 正文中用于 @ 的文本（手机号或姓名）

    content_parts: list[str] = [
        f"# {title}\n",
        f"> 本次共 **{len(certs)}** 项需要关注\n",
        "\n---\n",
    ]

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
            status = "⚠️ 今日到期"
            color = "#FF8C00"
        elif days_left <= 7:
            status = f"🔶 还剩 {days_left:.0f} 天"
            color = "#FFA500"
        elif days_left <= 30:
            status = f"🟡 还剩 {days_left:.0f} 天"
            color = "#FFD700"
        else:
            status = f"🟢 还剩 {days_left:.0f} 天"
            color = "#32CD32"

        content_parts.append(f"### {customer} · {cert_type}\n")
        if domain:
            content_parts.append(f"- 域名：{domain}\n")
        content_parts.append(f"- 到期：{expire_date}\n")
        content_parts.append(f"- 状态：<font color='{color}'>{status}</font>\n\n")

        # 收集负责人并映射为钉钉 ID
        responsible_users = cert.get("responsible_users", [])
        for uname in responsible_users:
            u = users_map.get(uname)
            if not u:
                continue
            did = (u.get("dingtalk_id") or "").strip()
            name = (u.get("name") or u.get("username") or "").strip()
            if not did:
                continue
            if _CN_MOBILE.match(did):
                if did not in at_mobiles:
                    at_mobiles.append(did)
                    mention_texts.append(f"@{did}")
            else:
                if did not in at_user_ids:
                    at_user_ids.append(did)
                    # 钉钉要求：atUserIds 必须在正文里写 @<userid> 才能触发 @（写姓名无效）
                    mention_texts.append(f"@{did}")

    if mention_texts:
        content_parts.append("---\n\n")
        content_parts.append("请以下负责人跟进处理：" + " ".join(mention_texts) + "\n")

    content = "".join(content_parts)

    return title, content, at_mobiles, at_user_ids


def send_wecom(webhook_url: str, message: str) -> bool:
    """
    发送企业微信消息
    
    Args:
        webhook_url: 企业微信机器人 Webhook 地址
        message: 消息内容
    
    Returns:
        bool: 发送是否成功
    """
    try:
        payload: dict[str, Any] = {
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
