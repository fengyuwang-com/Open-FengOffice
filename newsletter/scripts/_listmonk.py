#!/usr/bin/env python3
"""
_listmonk.py — Listmonk API 通用模块

所有脚本共用此文件。环境变量:
  LISTMONK_URL       (默认 http://localhost:9000)
  LISTMONK_USERNAME  (默认 admin)
  LISTMONK_PASSWORD  (必须设置)
"""
import os, json, requests
from urllib.parse import urljoin

LISTMONK_URL = os.environ.get("LISTMONK_URL", "http://localhost:9000")
LISTMONK_USER = os.environ.get("LISTMONK_USERNAME", "admin")
LISTMONK_PASS = os.environ.get("LISTMONK_PASSWORD") or os.environ.get("LISTMONK_API_PASSWORD", "")

_session = requests.Session()
_session.auth = (LISTMONK_USER, LISTMONK_PASS)
_session.headers.update({"Content-Type": "application/json"})

_cached_lists = {}

def api(method, path, **kwargs):
    url = urljoin(LISTMONK_URL, path)
    return _session.request(method, url, timeout=30, **kwargs)

def get_or_create_list(name):
    """按名称查找列表，不存在则创建"""
    global _cached_lists
    if name in _cached_lists:
        return _cached_lists[name]

    resp = api("GET", "/api/lists")
    for lst in resp.json()["data"].get("results", []):
        _cached_lists[lst["name"]] = lst["id"]
        if lst["name"] == name:
            return lst["id"]

    # 创建新列表
    resp = api("POST", "/api/lists", json={"name": name, "type": "public"})
    if resp.status_code == 200:
        lst_id = resp.json()["data"]["id"]
        _cached_lists[name] = lst_id
        print(f"  → 已创建列表: {name} (ID={lst_id})")
        return lst_id

    raise RuntimeError(f"无法创建列表: {resp.status_code} {resp.text}")
