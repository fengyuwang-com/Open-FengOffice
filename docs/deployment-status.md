# FengOffice 部署状态 & 启动清单

> 最后一次更新: 2026-07-29 11:58

## 总体进度

| 阶段 | 状态 | 备注 |
|------|------|------|
| 1. 基础设施 (Podman) | ✅ 完成 | WSL2 Fedora 44, rootless, 镜像加速 |
| 2. Twenty CRM | ✅ 完成 | 4 容器运行, 端口 3002 |
| 3. Newsletter (Listmonk) | ✅ 完成 | 2 容器运行, 端口 9000 |
| 4. SMTP (Resend) | ❌ DNS 待配置 | 需验证域名 + API Key |
| 5. 邮件路由 | ❌ 待配置 | subscribe@ / unsub@ |

## 容器清单

### Twenty CRM（全部在 twenty-net）
| 容器名 | 镜像 | 端口 | 状态 | 备注 |
|--------|------|------|------|------|
| twenty-db | postgres:16 | — | ✅ running (healthy) | 数据卷 twenty-db-data |
| twenty-redis | redis:latest | — | ✅ running | — |
| twenty-server | twentycrm/twenty:latest | 3002→3000 | ✅ running | bypass entrypoint |
| twenty-worker | twentycrm/twenty:latest | — | ✅ running | dist/queue-worker/queue-worker.js |

### Newsletter（全部在 listmonk）
| 容器名 | 镜像 | 端口 | 状态 | 备注 |
|--------|------|------|------|------|
| listmonk-db | postgres:16 | 5433→5432 | ✅ running (healthy) | 数据卷 listmonk-db-data |
| listmonk-app | listmonk/listmonk:latest | 9000→9000 | ✅ running | SMTP 占位, 待配置 |

## → 当前所处位置：阶段 4 — Resend SMTP 配置

---

## To Do List

### 阶段 1～3 — 基础设施（✅ 已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1.1 | 安装 Podman (WSL2) | ✅ | v5.8.5, Fedora 44, rootless |
| 1.2 | 配置镜像加速 docker.1panel.live | ✅ | 香港可用 |
| 1.3 | 拉取所有镜像 | ✅ | twentycrm, postgres:16, redis, listmonk/listmonk |
| 2.1 | 创建 twenty-net 自定义网络 | ✅ | — |
| 2.2 | 启动 twenty-db (Postgres) | ✅ | 含数据卷, pg_dump 恢复 |
| 2.3 | 启动 twenty-redis | ✅ | — |
| 2.4 | 运行 schema upgrade | ✅ | v2.22.0 → v2.25.0, 3 workspace 成功 |
| 2.5 | 启动 twenty-server | ✅ | bypass entrypoint, 端口 3002 |
| 2.6 | 启动 twenty-worker | ✅ | dist/queue-worker/queue-worker.js |
| 2.7 | 验证 Twenty CRM | ✅ | healthz 200, client-config 200, GraphQL 响应 |
| 3.1 | 创建 listmonk 网络和数据卷 | ✅ | — |
| 3.2 | 初始化 Listmonk schema | ✅ | ./listmonk --install --idempotent --yes |
| 3.3 | 启动 listmonk-app | ✅ | 端口 9000, SMTP 占位 |
| 3.4 | 验证 Listmonk UI | ✅ | HTTP 200, http://localhost:9000 |

### 阶段 4 — Resend SMTP 🔵（当前步骤）

| # | 任务 | 状态 | 指引 |
|---|------|------|------|
| **4.1** | **打开 Resend → Add Domain** | ⏳ **你在这里** | 访问 https://resend.com → Add Domain → 输入 news.fengyuwang.com |
| 4.2 | 添加 DKIM CNAME 到 Cloudflare | ⬜ | Resend 会给一条 `resend._domainkey.news` CNAME → 去 Cloudflare DNS 添加 |
| 4.3 | 添加 SPF TXT 到 Cloudflare | ⬜ | Resend 会给一条 TXT 记录（SPF 允许 Resend 代发）→ 去 Cloudflare DNS 添加 |
| 4.4 | 在 Resend 点 Verify Domain | ⬜ | DNS 记录生效后（几分钟）点验证 |
| 4.5 | 创建 Resend API Key | ⬜ | Resend → API Keys → Create API Key → 选 Sending |
| 4.6 | 配置 Cloudflare Email Routing | ⬜ | 设置 subscribe@ → Python 脚本, unsub@ → Python 脚本 (Opt-out) |
| 4.7 | 注入 API Key 并重启 listmonk-app | ⬜ | `podman stop listmonk-app && podman rm listmonk-app` → 用真实 Key 重新 `podman run` |

### 阶段 5 — 验证（最终）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 5.1 | 测试发送测试邮件 | ⬜ | Listmonk UI → Campaigns → Send Test |
| 5.2 | 确认收到 | ⬜ | 检查你的收件箱 |
| 5.3 | 创建第一个 Newsletter 模板 | ⬜ | Listmonk UI → Templates |

---

## 快速参考命令

### Listmonk 重启（注入真实 SMTP）
```bash
podman stop listmonk-app && podman rm listmonk-app
podman run -d --name listmonk-app --network listmonk -p 9000:9000 \
  -e LISTMONK_app__address=0.0.0.0:9000 \
  -e LISTMONK_db__host=listmonk-db \
  -e LISTMONK_db__port=5432 \
  -e LISTMONK_db__user=listmonk \
  -e LISTMONK_db__password=listmonk \
  -e LISTMONK_db__database=listmonk \
  -e LISTMONK_db__ssl_mode=disable \
  -e LISTMONK_smtp__host=smtp.resend.com \
  -e LISTMONK_smtp__port=587 \
  -e LISTMONK_smtp__username=resend \
  -e LISTMONK_smtp__password="<你的真实API Key>" \
  -e LISTMONK_smtp__from_email=fengyu@news.fengyuwang.com \
  -e LISTMONK_smtp__tls_type=starttls \
  -e TZ=Asia/Hong_Kong \
  docker.1panel.live/listmonk/listmonk:latest
```

### 验证 DNS 记录
```bash
nslookup -type=CNAME resend._domainkey.news.fengyuwang.com
nslookup -type=TXT news.fengyuwang.com
```
