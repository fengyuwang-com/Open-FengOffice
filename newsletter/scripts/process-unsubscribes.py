#!/usr/bin/env python3
"""
process-unsubscribes.py — 处理退订邮件

从退订邮箱扫邮件 → 提取发件人 → 调 Listmonk API 退订
可定时运行 (cron/systemd timer) 或手动触发。

用法:
  python process-unsubscribes.py                    # 处理所有未读退订
  python process-unsubscribes.py --mark-read        # 处理完标已读
  python process-unsubscribes.py --imap-config cfg  # 指定 IMAP 配置

配置:
  在 FengOffice 根目录的 .env 中添加:
  UNSUB_IMAP_HOST=imap.example.com
  UNSUB_IMAP_USER=your@email.com
  UNSUB_IMAP_PASS=xxxx
  UNSUB_IMAP_FOLDER=INBOX
"""
import sys, os, argparse, email, json
from imaplib import IMAP4_SSL
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api, LISTMONK_URL

def get_imap_config():
    """从环境变量读取 IMAP 配置"""
    host = os.environ.get("UNSUB_IMAP_HOST")
    user = os.environ.get("UNSUB_IMAP_USER")
    pwd = os.environ.get("UNSUB_IMAP_PASS")
    folder = os.environ.get("UNSUB_IMAP_FOLDER", "INBOX")
    if not all([host, user, pwd]):
        print("⚠️  未配置 UNSUB_IMAP_HOST/USER/PASS, 跳过 IMAP 检查")
        return None
    return {"host": host, "user": user, "pwd": pwd, "folder": folder}

def process_imap(cfg):
    """连接 IMAP 并处理退订邮件"""
    conn = IMAP4_SSL(cfg["host"])
    conn.login(cfg["user"], cfg["pwd"])
    conn.select(cfg["folder"], readonly=False)

    _, ids = conn.search(None, "UNSEEN")
    unsubscribed = []
    for num in ids[0].split() if ids[0] else []:
        _, data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        msg = email.message_from_bytes(data[0][1])
        sender = msg.get("From", "")
        subject = msg.get("Subject", "")

        # 自动退订: 任何发到 unsub@ 地址的邮件
        email_addr = sender.split("<")[-1].split(">")[0].strip() if "<" in sender else sender.split(",")[0].strip()
        if email_addr:
            try:
                # 通过 Listmonk API 搜索并退订
                resp = api("GET", f"/api/subscribers?per_page=all")
                subs = resp.json()["data"].get("results", [])
                for s in subs:
                    if s["email"].lower() == email_addr.lower():
                        api("PUT", f"/api/subscribers/{s['id']}/blocklist")
                        unsubscribed.append(email_addr)
                        print(f"  ✅ 已退订: {email_addr}")
                        break
            except Exception as e:
                print(f"  ⚠️  处理失败: {email_addr} - {e}")

        # 标记已读
        conn.store(num, "+FLAGS", "\\Seen")

    conn.close()
    conn.logout()
    return unsubscribed

def main():
    p = argparse.ArgumentParser(description="处理退订邮件")
    p.add_argument("--mark-read", action="store_true", help="处理后标记已读")
    args = p.parse_args()

    cfg = get_imap_config()
    if not cfg:
        print("📭 未配置退订邮箱 — 退订功能通过 List-Unsubscribe mailto: 头自动工作")
        print("   配置方法: 在 .env 设置 UNSUB_IMAP_HOST/USER/PASS")
        return

    print(f"🔍 扫描 {cfg['host']}/{cfg['folder']} 的未读退订邮件...")
    unsubscribed = process_imap(cfg)

    if unsubscribed:
        print(f"\n📋 本次处理退订: {len(unsubscribed)} 人")
        for e in unsubscribed:
            print(f"  - {e}")
    else:
        print("📭 没有新的退订请求")

if __name__ == "__main__":
    main()
