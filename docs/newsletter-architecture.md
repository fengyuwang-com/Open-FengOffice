# FengOffice — Newsletter 系统 & 内容枢纽架构

> 统一的内容生产→分发→受众管理平台架构文档。

## 总览

FengOffice 正在从"邮件+CRM"扩展为 Fengyu Wang 个人内容体系的运营中枢：

```
创造层         管理层          分发层           受众层
┌──────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│文章   │   │  FengOffice│  │Newsletter│   │ 订阅者   │
│视频   │ → │  内容队列  │ → │社交平台  │ → │ CRM联系人│
│报告   │   │  调度逻辑  │   │网站      │   │ 网站访客 │
└──────┘   └──────────┘   └──────────┘   └──────────┘
```

---

## 1. Newsletter 系统（当前构建中）

### 1.1 架构

```
~/FengOffice/
├── docker-compose.yml        ← Twenty CRM (existing)
├── fengmail.py               ← Email system (existing)
└── newsletter/               ← NEW - Newsletter system
    ├── docker-compose.yml    ← Listmonk + Postgres
    ├── .env                  ← Credentials (gitignored)
    ├── config.toml           ← Listmonk config (auto-generated)
    └── scripts/
        ├── add-subscriber.py      ← Add subscriber via API
        ├── remove-subscriber.py   ← Remove/unsubscribe via API
        ├── send-newsletter.py     ← Create & send campaign
        ├── list-subscribers.py    ← List all subscribers
        └── process-unsubscribes.py ← Process mailto: unsubscribe
```

### 1.2 组件

| 组件 | 角色 | 技术 |
|------|------|------|
| **Listmonk** | 邮件列表管理（订阅/退订/发放） | Go binary + Postgres 17 |
| **Resend** | 发信通道（SMTP/API） | Cloud service |
| **Cloudflare Email Routing** | 收退订邮件（unsub@ → 转发） | Cloudflare |
| **Python scripts** | AI 管理接口 | Python 3 + requests |

### 1.3 数据流：发送

```
AI/用户 (通过脚本或 Web UI)
  → Listmonk API → 创建 campaign
  → Listmonk SMTP → Resend → news.fengyuwang.com (DKIM/SPF)
  → 收件人收件箱
```

### 1.4 数据流：退订

```
收件人点"取消订阅" (Gmail/Outlook 原生按钮)
  → 自动发邮件到 unsub@fengyuwang.com
  → Cloudflare Email Routing → 转发到指定邮箱
  → process-unsubscribes.py (定时扫 IMAP)
  → Listmonk API → 移除订阅者确认
```

### 1.5 外部依赖

| 服务 | 用途 | 费用 | 配置状态 |
|------|------|------|---------|
| Resend | 发信通道 | 前 3000 封/月免费 | ⏳ 待注册 |
| Cloudflare | DNS + Email Routing | 免费 | ⏳ 待用户配 DNS |
| news.fengyuwang.com | 子域名信誉 | 已有域名 | ⏳ 待配 |

---

## 2. 内容枢纽（长期蓝图）

### 2.1 统一的内容生命周期

```
┌──────────────┐
│  CREATE      │
│  FengMedia   │ ← 文章、分析、话题
│  Vids        │ ← 视频资产
│  FengInvest  │ ← 研究报告
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  QUEUE       │
│  内容待发布池│ ← 调度逻辑：什么内容→什么渠道→什么时间
└──────┬───────┘
       │
       ├───────►  Newsletter  ← Listmonk
       ├───────►  社交平台    ← social-auto-upload
       ├───────►  网站        ← fengyuwang.com
       └───────►  邮件签名    ← FengMail
       │
       ▼
┌──────────────┐
│  AUDIENCE    │
│  CRM 联系人  │ ← Twenty (分层管理)
│  订阅者      │ ← Listmonk (邮件列表)
│  网站访客    │ ← 入口页 (待建)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  FEEDBACK    │
│  打开率/点击 │ ← Listmonk analytics
│  CRM 互动    │ ← Twenty timeline
│  内容复盘    │ ← FengMedia /review
└──────────────┘
```

### 2.2 内容类型 × 分发渠道矩阵

| 内容类型 | Newsletter | 网站 | LinkedIn | B站/小红书 | CRM |
|---------|-----------|------|----------|-----------|-----|
| 项目月报 | ✅ 主阵地 | ✅ 同步 | ✅ 切片 | ❌ | ✅ 存档 |
| 分析报告 | ✅ 精华版 | ✅ 完整版 | ✅ 摘要 | ✅ 视频版 | ✅ |
| 技术分享 | ✅ 简讯 | ✅ 全文 | ✅ 英文版 | ⚠️ 可选 | ✅ |
| 随想/观点 | ⚠️ 偶发 | ✅ | ✅ | ❌ | ⚠️ |
| 视频 | ❌ | ✅ 嵌入 | ⚠️ | ✅ 主阵地 | ❌ |

### 2.3 AI 管理接口

所有操作通过 API + Python 脚本完成，不需要人工点击 Web UI：

| 操作 | 脚本/API | 触发方式 |
|------|---------|---------|
| 添加订阅者 | `add-subscriber.py email [name]` | AI 或 CLI |
| 移除订阅者 | `remove-subscriber.py email` | AI 或 CLI |
| 发送 Newsletter | `send-newsletter.py --subject --body-file` | AI |
| 查看订阅者 | `list-subscribers.py [--json]` | AI |
| 处理退订 | `process-unsubscribes.py` | 定时/手动 |
| 从 CRM 导入 | 从 Twenty REST API 导出 → Listmonk API 导入 | AI |
| 网站订阅入口 | 网站表单 POST → Listmonk API | 访客自助 |

---

## 3. DNS 配置清单

用户需要在 Cloudflare 配置：

| 优先级 | 记录 | 值 | 用途 |
|--------|------|-----|------|
| P0 | `news.fengyuwang.com A` | 任意 IP (占位) | 子域名锚点 |
| P1 | Cloudflare Email Routing MX | Cloudflare 提供 | 收 unsub@ 邮件 |
| P1 | unsub@ → 转发规则 | → 用户邮箱 | 退订邮件落地 |
| P2 | `_dmarc.news DMARC` | `v=DMARC1; p=none` | 可选的发送信誉 |
| 待 Resend 步骤 | DKIM TXT | Resend 生成 | 发信认证 |
| 待 Resend 步骤 | SPF TXT | `v=spf1 include:spf.resend.com ~all` | 发信认证 |

---

## 4. 部署步骤（待执行）

- [ ] 用户配置 Cloudflare DNS
- [ ] 注册 Resend + 验证 news.fengyuwang.com
- [ ] 部署 `newsletter/docker-compose.yml`
- [ ] 配置 Listmonk 管理员 + SMTP
- [ ] 实现 Python AI 管理脚本
- [ ] 测试发送 + 退订全链路
- [ ] 网站添加邮箱订阅入口
- [ ] FengMail 签名添加订阅链接
- [ ] Newsletter ↔ social-auto-upload 联动
- [ ] CRM ↔ 订阅者列表同步

---

关联：内容分发策略（团队内部文档，不随本仓发布）
