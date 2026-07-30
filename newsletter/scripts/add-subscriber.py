#!/usr/bin/env python3
"""
add-subscriber.py — 添加订阅者到 Listmonk

用法:
  python add-subscriber.py email@example.com "姓名" [--list 1]

不传 --list 则加到 ID=1 的列表 (第一个列表)。
"""
import sys, os, argparse, json
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api, get_or_create_list

def main():
    p = argparse.ArgumentParser()
    p.add_argument("email")
    p.add_argument("name", nargs="?", default="")
    p.add_argument("--list", type=int, default=None)
    args = p.parse_args()

    list_id = args.list
    if list_id is None:
        list_id = get_or_create_list("主列表")
        print(f"  → 使用列表 ID={list_id}")

    resp = api("POST", "/api/subscribers", json={
        "email": args.email,
        "name": args.name or args.email.split("@")[0],
        "lists": [list_id],
        "status": "confirmed",
    })
    if resp.status_code == 200:
        d = resp.json()["data"]
        print(f"✅ 已添加: {d['email']} (ID={d['id']})")
    elif resp.status_code == 400 and "already exists" in resp.text:
        print(f"⚠️  已存在: {args.email}")
    else:
        print(f"❌ 失败 ({resp.status_code}): {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
