#!/usr/bin/env python3
"""
remove-subscriber.py — 移除/退订订阅者

用法:
  python remove-subscriber.py email@example.com
  python remove-subscriber.py --all          # 全列表查看
  python remove-subscriber.py email --list 1  # 从指定列表移除
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api

def main():
    p = argparse.ArgumentParser()
    p.add_argument("email", nargs="?", default=None)
    p.add_argument("--list", type=int, help="仅从某列表移除 (默认全局)")
    p.add_argument("--all", action="store_true", help="列出所有订阅者")
    args = p.parse_args()

    if args.all:
        resp = api("GET", "/api/subscribers?per_page=all")
        subs = resp.json()["data"]["results"]
        print(f"共 {len(subs)} 个订阅者:")
        for s in subs:
            print(f"  [{s['id']}] {s['email']} ({s.get('name','')}) status={s['status']}")
        return

    if not args.email:
        p.print_help()
        sys.exit(1)

    # 查找订阅者
    resp = api("GET", f"/api/subscribers?per_page=all&query=subscribers.email='{args.email}'")
    subs = resp.json()["data"]["results"]
    if not subs:
        print(f"❌ 未找到: {args.email}")
        sys.exit(1)

    sub = subs[0]
    if args.list:
        api("DELETE", f"/api/subscribers/{sub['id']}")
    else:
        api("PUT", f"/api/subscribers/{sub['id']}/blocklist")

    print(f"✅ 已移除: {args.email} (ID={sub['id']})")

if __name__ == "__main__":
    main()
