# FengOffice — 邮件 + CRM + Newsletter

AI 统一邮件与 CRM 平台。一个 CLI 管邮件，一个 Docker 栈跑 Twenty CRM，Listmonk 分发 Newsletter——把内容运营的基础设施收进一条自动化链路。

> **官网**：https://fengyuwang.com/zh-cn/fengoffice.html

---

## 组成

| 模块 | 技术 | 作用 |
|:-----|:-----|:-----|
| 邮件 | `fengmail.py`（IMAP + SMTP） | 多账号收信、读信、发送、回复，全部输出 JSON |
| CRM | Twenty（docker-compose，端口 3002） | 联系人 / 公司 / 机会全生命周期归档 |
| Newsletter | Listmonk + Postgres | 订阅、退订、campaign 全部脚本化 |

## 快速开始

```bash
python fengmail.py list-accounts        # 查看邮箱账号
docker compose up -d                    # 启动 Twenty CRM（localhost:3002）
cd newsletter && docker compose up -d   # 启动 Listmonk + Postgres
python newsletter/scripts/send-newsletter.py   # 发送 Newsletter
```

## 文档

- `docs/ai-operations-guide.md` — 完整操作手册
- `docs/email-classification.md` — 四级邮件分类体系
- `docs/newsletter-architecture.md` — Newsletter 系统与内容枢纽架构
- `docs/requirements.md` — CRM 功能需求
- `docs/deployment-status.md` — 部署状态
