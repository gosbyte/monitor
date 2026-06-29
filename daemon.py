# -*- coding: utf-8 -*-
"""
后台常驻脚本 - 精确到分钟的到期项到期提醒
每分钟检查一次，到期时间到了就立即推送
"""
import os
import sys
import json
import time
import logging
import logging.handlers
import smtplib
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)

import signal
import requests
from dingtalk import send_dingtalk_card, send_wecom, build_remind_card

# ── 统一数据层：使用 data.py（支持 JSON/SQLite 双模式）─────────────
from data import (
    load_certs, save_certs,
    load_config, save_config, load_config_decrypted,
    load_users, save_users,
    load_logs, write_log,
    calc_days_left, get_cert_status,
    encrypt_field, decrypt_field,
    USE_SQLITE,
)

# 文件锁相关（仅 JSON 模式需要，daemon 单线程不需要锁）
# SQLite 模式下由 db.py 的事务管理代替文件锁

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            os.path.join(DATA_DIR, "daemon.log"), maxBytes=10_485_760, backupCount=5, encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data():
    """加载到期项数据（兼容旧代码名，实际就是 load_certs）"""
    try:
        return load_certs()
    except Exception:
        return []

def load_state():
    """加载已推送状态（带异常处理和文件句柄管理）"""
    state_file = os.path.join(DATA_DIR, "remind_state.json")
    try:
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8-sig") as f:
                result = json.load(f)
            return result if result is not None else {}
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"加载 remind_state.json 失败: {e}，使用空状态")
    return {}


def save_state(state):
    """保存已推送状态（原子写入 + 异常处理）"""
    state_file = os.path.join(DATA_DIR, "remind_state.json")
    tmp = None  # [FIX] P0-6: 初始化 tmp 防止 open() 失败时 NameError
    try:
        tmp = state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, state_file)
    except IOError as e:
        logger.error(f"保存 remind_state.json 失败: {e}")
        # 清理可能的临时文件
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass

def send_email_remind(subject, content_html, cfg):
    """发送邮件提醒（使用全局收件人），返回 (success, message)"""
    smtp_to = cfg.get("smtp_to", "").strip()
    if not smtp_to:
        return False, "邮件配置不完整"
    recipients = [r.strip() for r in smtp_to.split(",") if r.strip()]
    if not recipients:
        return False, "收件人为空"
    return send_email_remind_to(subject, content_html, cfg, recipients)


def send_email_remind_to(subject, content_html, cfg, recipients):
    """发送邮件提醒到指定收件人，返回 (success, message)"""
    smtp_host = cfg.get("smtp_host", "").strip()
    smtp_port = cfg.get("smtp_port", 465)
    smtp_user = cfg.get("smtp_user", "").strip()
    smtp_pass = cfg.get("smtp_pass", "").strip()

    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "邮件配置不完整"

    if not recipients:
        return False, "收件人为空"

    try:
        port = int(smtp_port)
    except ValueError:
        port = 465

    try:
        msg = f"From: {smtp_user}\r\nTo: {','.join(recipients)}\r\nSubject: {subject}\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{content_html}"
        if port == 465:
            with smtplib.SMTP_SSL(smtp_host, port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipients, msg.encode("utf-8"))
        else:
            with smtplib.SMTP(smtp_host, port, timeout=10) as server:
                server.ehlo()
                if smtp_port == 587:
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipients, msg.encode("utf-8"))
        logger.info(f"邮件发送成功，收件人: {recipients}")
        return True, "发送成功"
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False, str(e)


def build_email_html(to_remind, is_responsible=False):
    """构建邮件 HTML 内容
    is_responsible: 是否为负责人定向推送，用于调整文案
    """
    rows = []
    for c in to_remind:
        days_left = c.get("days_left", 0)
        if days_left < 0:
            badge = '<span style="background:#ef4444;color:white;padding:2px 8px;border-radius:12px;font-size:12px">已过期</span>'
        elif days_left == 0:
            badge = '<span style="background:#f97316;color:white;padding:2px 8px;border-radius:12px;font-size:12px">今日到期</span>'
        else:
            badge = f'<span style="background:#eab308;color:white;padding:2px 8px;border-radius:12px;font-size:12px">剩{days_left}天</span>'
        rows.append(f'<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{c.get("customer","")}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{c.get("cert_type","")}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{c.get("domain","")}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{c.get("expire_date","")}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{badge}</td></tr>')
    rows_html = "".join(rows)
    subtitle = "您负责的以下到期项即将到期" if is_responsible else f"共 {len(to_remind)} 条到期项需要关注"
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;margin:0;padding:20px">
<div style="max-width:700px;margin:0 auto">
<div style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
<div style="background:#2563eb;padding:20px 24px">
<h2 style="color:white;margin:0;font-size:18px">🔔 到期项到期提醒</h2>
<p style="color:#bfdbfe;margin:4px 0 0;font-size:13px">{subtitle}</p>
</div>
<table style="width:100%;border-collapse:collapse;font-size:14px">
<thead><tr style="background:#f9fafb">
<th style="padding:10px 12px;text-align:left;font-weight:600;color:#374151">客户</th>
<th style="padding:10px 12px;text-align:left;font-weight:600;color:#374151">类型</th>
<th style="padding:10px 12px;text-align:left;font-weight:600;color:#374151">域名</th>
<th style="padding:10px 12px;text-align:left;font-weight:600;color:#374151">到期日期</th>
<th style="padding:10px 12px;text-align:center;font-weight:600;color:#374151">状态</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<div style="padding:16px 24px;border-top:1px solid #e5e7eb">
<p style="color:#6b7280;font-size:12px;margin:0">本邮件由到期提醒监控系统自动发送，请勿直接回复。</p>
</div>
</div></div></body></html>'''
    return html

def parse_expire_date(date_str):
    """解析到期时间，返回 datetime 对象"""
    s = date_str.strip()
    if "T" in s:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M")
    elif ":" in s:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    else:
        # 只有日期的，默认当天 23:59
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(hour=23, minute=59, second=59)


def check_and_remind():
    """检查并发送提醒"""
    # [FIX] 解密 SMTP 密码
    cfg = load_config_decrypted()
    has_dingtalk = bool(cfg.get("webhook_url", ""))
    has_wecom = bool(cfg.get("wecom_webhook", "")) and cfg.get("wecom_enabled", False)
    has_email = cfg.get("email_enabled", False)
    if not has_dingtalk and not has_wecom and not has_email:
        return

    certs = load_data()
    state = load_state()
    now = datetime.now()

    # 加载用户（用于@人）
    try:
        users_data = load_users()
        users_map = {u["username"]: u for u in (users_data or [])}
    except Exception:
        users_map = {}
    
    # 首先清理 remind_state 中已不存在的记录
    cert_ids = {c.get("id") for c in certs}
    cleaned_state = {}
    for k, v in state.items():
        # 提取 key 中的 cert_id 部分（格式如 "3_day7" 或 "3_expired"）
        parts = k.split("_", 1)
        if parts and parts[0].isdigit():
            if int(parts[0]) in cert_ids:
                cleaned_state[k] = v
        else:
            cleaned_state[k] = v  # 非标准格式保留
    if len(cleaned_state) != len(state):
        logger.info(f"清理已删除记录的推送状态: {len(state)} -> {len(cleaned_state)}")
        state = cleaned_state

    remind_days = set(cfg.get("remind_days", [7, 3, 1]) + [0])
    to_remind = []
    
    for c in certs:
        # 跳过禁用提醒的
        if not c.get("remind_enabled", True):
            continue
        
        # 解析到期时间
        try:
            expire_dt = parse_expire_date(c["expire_date"])
        except Exception as e:
            logger.warning(f"日期解析失败: {c.get('customer')} - {e}")
            continue
        
        cert_id = c.get("id")
        if cert_id is None:
            continue  # 跳过无 id 的异常记录
        time_left = expire_dt - now
        days_left = time_left.days
        
        # 已过期的，每次启动都提醒一次
        if expire_dt < now:
            key = f"{cert_id}_expired"
            if key not in state or now.strftime("%Y-%m-%d") != state[key]:
                to_remind.append(c)
                state[key] = now.strftime("%Y-%m-%d")
            continue
        
        # 到期提醒逻辑
        should_remind = False
        
        # 到期当天（剩余 0 天）
        if days_left == 0:
            # 到期时间前 1 小时提醒
            if time_left.total_seconds() <= 3600:
                key = f"{cert_id}_day0_1h"
                if key not in state:
                    should_remind = True
                    state[key] = now.isoformat()
        
        # 提前 N 天提醒
        if days_left in remind_days and days_left > 0:
            key = f"{cert_id}_day{days_left}"
            today = now.strftime("%Y-%m-%d")
            if key not in state or state[key] != today:
                should_remind = True
                state[key] = today
        
        # 精确到分钟：到期前 30/10/5/1 分钟提醒
        mins_left = int(time_left.total_seconds() // 60)
        if mins_left in [30, 10, 5, 1]:
            key = f"{cert_id}_min{mins_left}"
            if key not in state:
                should_remind = True
                state[key] = now.isoformat()
        
        if should_remind and not c.get("handled", False):
            to_remind.append(c)
    
    if to_remind:
        logger.info(f"发现 {len(to_remind)} 条需要提醒")
        title, card_content, at_ids = build_remind_card(to_remind, users_map)
        secret = cfg.get("secret", "")
        ding_ok = True
        if has_dingtalk:
            ding_ok = send_dingtalk_card(cfg["webhook_url"], title, card_content, secret, at_user_ids=at_ids if at_ids else None)
        # 企业微信推送
        wecom_webhook = cfg.get("wecom_webhook", "")
        wecom_ok = True  # 未配置视为通过
        if wecom_webhook:
            try:
                parts = []
                for c in to_remind:
                    days = c.get("days_left", 0)
                    parts.append(f"⚠️ {c['customer']} - {c['cert_type']} | 域名: {c['domain']} | 到期: {c['expire_date']} | 剩余 {days} 天")
                msg = "到期提醒通知\n\n" + "\n".join(parts) + "\n\n请及时续签！"
                wecom_ok = send_wecom(wecom_webhook, msg)
                if wecom_ok:
                    logger.info(f"企业微信推送成功: {len(to_remind)} 条")
                else:
                    logger.warning("企业微信推送失败")
            except Exception as e:
                wecom_ok = False
                logger.error(f"企业微信推送异常: {e}")
        # 邮件推送（如果启用）
        email_ok = True  # 未启用视为通过
        if cfg.get("email_enabled", False):
            # [FIX] 使用浅拷贝避免修改原始 cert 对象
            to_remind_copies = [dict(c) for c in to_remind]
            for c in to_remind_copies:
                c["days_left"] = (parse_expire_date(c["expire_date"]) - datetime.now()).days
            
            # 按负责人分组发送邮件
            # 1. 收集所有负责人及其对应的到期项
            responsible_certs = {}  # {username: [certs]}
            certs_without_responsible = []  # 无负责人的到期项
            
            for c in to_remind_copies:
                responsible_users = c.get("responsible_users", [])
                if responsible_users:
                    for uname in responsible_users:
                        if uname not in responsible_certs:
                            responsible_certs[uname] = []
                        responsible_certs[uname].append(c)
                else:
                    certs_without_responsible.append(c)
            
            # 2. 为有邮箱的负责人发送定向邮件
            sent_count = 0
            for uname, certs in responsible_certs.items():
                uinfo = users_map.get(uname, {})
                email = uinfo.get("email", "").strip()
                if email:
                    # 发送给负责人
                    email_html = build_email_html(certs, is_responsible=True)
                    ok, msg = send_email_remind_to(f"🔔 您负责的到期项到期提醒", email_html, cfg, [email])
                    if ok:
                        logger.info(f"邮件已发送给负责人 {uname} ({email})")
                        sent_count += 1
                    else:
                        logger.warning(f"发送给负责人 {uname} 失败: {msg}")
                        # 负责人发送失败，这些到期项归入无负责人列表
                        certs_without_responsible.extend(certs)
                else:
                    # 负责人没有邮箱，这些到期项归入无负责人列表
                    certs_without_responsible.extend(certs)
            
            # 3. 无负责人或负责人无邮箱的到期项，发给全局收件人
            if certs_without_responsible:
                email_html = build_email_html(certs_without_responsible, is_responsible=False)
                email_ok, email_msg = send_email_remind(title, email_html, cfg)
                if email_ok:
                    logger.info(f"邮件推送成功（全局收件人）")
                else:
                    logger.warning(f"邮件推送失败: {email_msg}")
            elif sent_count > 0:
                email_ok = True
        # 只有所有已配置渠道均成功时才保存 state（防止重复推送）
        all_ok = ding_ok and wecom_ok and email_ok
        if all_ok:
            save_state(state)
        else:
            logger.warning("推送未全部成功，state 不保存，下次将继续重试")

def main():
    """主循环"""
    logger.info("=" * 50)
    logger.info("到期项到期后台监控服务启动")
    logger.info("检查频率：每分钟一次")
    logger.info("=" * 50)
    
    _running = True

    def _sigterm_handler(signum, frame):
        global _running
        logger.info("收到到 SIGTERM，停止主命循环...")
        _running = False

    signal.signal(signal.SIGTERM, _sigterm_handler)
    signal.signal(signal.SIGINT, _sigterm_handler)

    while _running:
        try:
            check_and_remind()
        except Exception as e:
            logger.error(f"检查异常: {e}")

        for _ in range(60):
            if not _running:
                break
            time.sleep(1)  # interruptible sleep

if __name__ == "__main__":
    main()
