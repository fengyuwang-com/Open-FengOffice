#!/usr/bin/env python3
"""
process-subscriptions.py — 处理订阅申请邮件

从 subscribe@ 邮箱扫邮件 → 提取发件人 → 调 Listmonk API 添加

用法:
  python process-subscriptions.py

配置 (同 process-unsubscribes.py，不同邮箱):
  SUB_IMAP_HOST / SUB_IMAP_USER / SUB_IMAP_PASS
"""
import sys, os, email
from imaplib import IMAP4_SSL
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api, get_or_create_list

def get_imap_config():
    host = os.environ.get("SUB_IMAP_HOST") or os.environ.get("UNSUB_IMAP_HOST")
    user = os.environ.get("SUB_IMAP_USER") or os.environ.get("UNSUB_IMAP_USER")
    pwd = os.environ.get("SUB_IMAP_PASS") or os.environ.get("UNSUB_IMAP_PASS")
    folder = os.environ.get("SUB_IMAP_FOLDER", "INBOX")
    if not all([host, user, pwd]):
        print("⚠️  未配置订阅邮箱")
        return None
    return {"host": host, "user": user, "pwd": pwd, "folder": folder}

def process():
    cfg = get_imap_config()
    if not cfg:
        return

    list_id = get_or_create_list("主列表")

    conn = IMAP4_SSL(cfg["host"])
    conn.login(cfg["user"], cfg["pwd"])
    conn.select(cfg["folder"], readonly=False)

    _, ids = conn.search(None, "UNSEEN")
    added = []
    for num in ids[0].split() if ids[0] else []:
        _, data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        msg = email.message_from_bytes(data[0][1])
        sender = msg.get("From", "")
        email_addr = sender.split("<")[-1].split(">")[0].strip() if "<" in sender else sender.split(",")[0].strip()

        if email_addr:
            resp = api("POST", "/api/subscribers", json={
                "email": email_addr, "name": "", "lists": [list_id], "status": "confirmed"
            })
            if resp.status_code == 200:
                added.append(email_addr)
                print(f"  ✅ 已添加订阅者: {email_addr}")
            elif "already exists" in resp.text:
                print(f"  ⚠️  已存在: {email_addr}")
            else:
                print(f"  ❌ 失败: {email_addr} - {resp.status_code}")

        conn.store(num, "+FLAGS", "\\Seen")

    conn.close()
    conn.logout()
    return added

if __name__ == "__main__":
    print("🔍 扫描订阅邮件...")
    process()
