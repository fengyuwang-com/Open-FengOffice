# Newsletter

```
newsletter/
├── docker-compose.yml     ← Listmonk + Postgres 17
├── .env                   ← 凭据 (gitignored)
├── .env.template          ← 配置模板
├── scripts/
│   ├── _listmonk.py       ← API 通用模块
│   ├── add-subscriber.py  ← 添加订阅者
│   ├── remove-subscriber.py  ← 移除/退订
│   ├── list-subscribers.py   ← 查看列表
│   ├── send-newsletter.py    ← 创建并发送 campaign
│   ├── process-unsubscribes.py  ← 处理退订邮件
│   └── process-subscriptions.py ← 处理订阅邮件
├── web-embed/
│   ├── subscribe-form.html    ← 网站订阅组件
│   └── cloudflare-worker.js   ← (可选) 高级订阅代理
├── docs/
│   └── setup-guide.md     ← 启动指南
└── uploads/               ← Listmonk 上传目录
```

### 快速启动

```bash
cp .env.template .env  # 填凭据
docker compose up -d   # 启动
python scripts/send-newsletter.py --subject "测试" --body "Hello"
```

完整步骤见 `docs/setup-guide.md`。
