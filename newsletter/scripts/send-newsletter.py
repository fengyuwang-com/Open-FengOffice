#!/usr/bin/env python3
"""
send-newsletter.py — 创建并发送 Newsletter campaign

用法:
  python send-newsletter.py --subject "7月项目更新" --body-file content.md
  python send-newsletter.py --subject "标题" --body "直接正文"
  python send-newsletter.py --subject "测试" --body "hello" --list 1 --test test@example.com

选项:
  --list L        发到指定列表 ID (默认: 1)
  --test EMAIL    只发送测试邮件到指定地址 (不正式发送)
  --type plain    纯文本 (默认 html)
"""
import sys, os, argparse, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--body", default=None)
    p.add_argument("--body-file", default=None)
    p.add_argument("--list", type=int, default=None)
    p.add_argument("--test", default=None, help="只发测试邮件到指定邮箱")
    p.add_argument("--type", default="html", choices=["html", "plain"])
    args = p.parse_args()

    # 获取正文
    body = args.body
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()
    if not body:
        print("❌ 需要 --body 或 --body-file")
        sys.exit(1)

    # 获取列表 ID
    list_id = args.list
    if not list_id:
        resp = api("GET", "/api/lists")
        lists = resp.json()["data"].get("results", [])
        if not lists:
            print("❌ 没有可用列表，先创建列表")
            sys.exit(1)
        list_id = lists[0]["id"]
        print(f"  → 使用列表: {lists[0]['name']} (ID={list_id})")

    # 如果只是测试
    if args.test:
        resp = api("POST", "/api/campaigns", json={
            "name": f"[TEST] {args.subject}",
            "subject": args.subject,
            "lists": [list_id],
            "content": {
                "content_type": args.type,
                "body": body,
            },
            "send_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        })
        camp = resp.json()["data"]
        camp_id = camp["id"]
        # 发测试
        api("POST", f"/api/campaigns/{camp_id}/test", json={
            "emails": [args.test]
        })
        print(f"✅ 测试邮件已发送到 {args.test} (campaign ID={camp_id})")
        # 删除测试 campaign
        api("DELETE", f"/api/campaigns/{camp_id}")
        return

    # 正式创建 campaign
    resp = api("POST", "/api/campaigns", json={
        "name": args.subject,
        "subject": args.subject,
        "lists": [list_id],
        "content": {
            "content_type": args.type,
            "body": body,
        },
        "type": "regular",
        "send_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    })

    if resp.status_code != 200:
        print(f"❌ 创建失败 ({resp.status_code}): {resp.text}")
        sys.exit(1)

    camp = resp.json()["data"]
    camp_id = camp["id"]
    print(f"📝 已创建 campaign ID={camp_id}: {args.subject}")

    # 立即发送
    resp = api("PUT", f"/api/campaigns/{camp_id}/status", json={"status": "scheduled"})

    if resp.status_code == 200:
        print(f"✅ 已发送! Campaign ID={camp_id}")
    else:
        print(f"⚠️  状态: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    main()
