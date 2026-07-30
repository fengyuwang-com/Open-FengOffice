#!/usr/bin/env python3
"""
list-subscribers.py — 查看订阅者列表

用法:
  python list-subscribers.py           # 全部
  python list-subscribers.py --list 1  # 指定列表
  python list-subscribers.py --json    # JSON 输出 (AI 友好)
  python list-subscribers.py --count   # 只显示数量
"""
import sys, os, argparse, json
sys.path.insert(0, os.path.dirname(__file__))
from _listmonk import api

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--list", type=int, help="列表 ID")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.add_argument("--count", action="store_true", help="只显示数量")
    args = p.parse_args()

    params = "per_page=all"
    if args.list:
        params += f"&list_id={args.list}"

    resp = api("GET", f"/api/subscribers?{params}")
    subs = resp.json()["data"]["results"]

    if args.count:
        print(len(subs))
        return

    if args.json:
        print(json.dumps([{"id": s["id"], "email": s["email"], "name": s.get("name",""),
                           "status": s["status"], "created_at": s["created_at"]} for s in subs],
                         indent=2, ensure_ascii=False))
        return

    if not subs:
        print("📭 没有订阅者")
        return

    print(f"📋 共 {len(subs)} 个订阅者:\n")
    for s in subs:
        status_icon = {"enabled": "✅", "blocklisted": "🚫", "unsubscribed": "❌"}.get(s["status"], "❓")
        print(f"  {status_icon} [{s['id']:4d}] {s['email']:<35s} {s.get('name',''):<20s} {s['status']}")

if __name__ == "__main__":
    main()
