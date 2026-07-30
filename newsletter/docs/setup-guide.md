# Newsletter 系统 — 秒级启动指南

> 只要 DNS 配好就能启动。这套代码 + 配置已经全部就绪。

## 启动步骤

### ⚡ 第一步：Cloudflare DNS（你去配，5 分钟）

在 Cloudflare 控制面板操作：

**1. Email Routing — 收订阅/退订邮件**

进入 Cloudflare → 你的域名 → Email → Email Routing:

| 设置 | 值 |
|------|-----|
| 开 Email Routing | 点"Get started"，按提示添加 MX 记录 |
| 自定义地址: `subscribe@` | → 转发到你的个人邮箱 (如 you@example.com) |
| 自定义地址: `unsub@` | → 转发到你的个人邮箱 (同上) |

**2. 添加子域名记录**

进入 DNS → 添加记录:

| 类型 | 名称 | 值 |
|------|------|-----|
| A | `news` | `192.0.2.1` (占位IP, 只为了先建好) |

> 这个 A 记录只是占位，让子域名存在。发信用的是 Resend 的 SMTP，不需要服务器响应。

**3. 完成 DNS 后告诉我**，我接着注册 Resend。

---

### 第二步：注册 Resend（我来操作，5 分钟）

1. 打开 https://resend.com → Sign up
2. 添加域名 `news.fengyuwang.com`
3. 按 Resend 提示，在 Cloudflare DNS 添加 DKIM + SPF 记录
4. 获取 API Key → 填入 `.env`

---

### 第三步：启动 Listmonk（我来操作，2 分钟）

```bash
cd ~/FengOffice/newsletter

# 配置
cp .env.template .env
# → 编辑 .env: 填 LISTMONK_ADMIN_PASSWORD + RESEND_API_KEY

# 启动
docker compose up -d

# 访问 http://localhost:9000 → 登录
```

---

### 第四步：首次设置（我来操作，2 分钟）

登录 Listmonk Web UI (http://localhost:9000):
1. Settings → SMTP: 确认 Resend 配置 (会自动从 env 读取)
2. Lists → 创建 "主列表" (或脚本自动创建)
3. Settings → 设置 List-Unsubscribe header 为 `mailto:unsub@fengyuwang.com`

---

### 第五步：功能验证

```bash
# 添加测试订阅者
python scripts/add-subscriber.py test@example.com "测试用户"

# 查看列表
python scripts/list-subscribers.py

# 发测试邮件
python scripts/send-newsletter.py --subject "测试" --body "Hello World" --test test@example.com
```

---

### 第六步：网站嵌入

打开 `~/FengOffice/newsletter/web-embed/subscribe-form.html`，复制代码到你的网站 HTML 中。

---

### 第七步：FengMail 签名更新

在 fengmail.py 或其他邮件发送配置中，签名处添加：

```
---
📬 每月收到我的项目进展 → subscribe@fengyuwang.com (发邮件即订阅)
```

---

## .env 完整示例

```
LISTMONK_ADMIN_USER=admin
LISTMONK_ADMIN_PASSWORD=YourStrongPassword123!
RESEND_API_KEY=re_abc123_def456
NEWSLETTER_FROM_EMAIL=fengyu@news.fengyuwang.com
```

## 首次启动后的维护

```bash
# 每月发更新
python scripts/send-newsletter.py --subject "7月项目更新" --body-file update.md

# 处理退订 (手动)
python scripts/process-unsubscribes.py

# 处理订阅 (手动)
python scripts/process-subscriptions.py

# 查看当前列表
python scripts/list-subscribers.py
```

---

## 订阅/退订体验总结

| 用户操作 | 效果 | 技术实现 |
|---------|------|---------|
| 在网站输入邮箱 | 发邮件到 subscribe@ | mailto: 链接 |
| 回复"取消订阅" | 退订 | List-Unsubscribe: mailto:unsub@ |
| 点击 Gmail 退订按钮 | 退订 | 同上 — Gmail 自动使用 mailto: |
| 发邮件到 subscribe@ | 订阅 | Cloudflare Email → 你的邮箱 → 脚本处理 |
| 发邮件到 unsub@ | 退订 | 同上 |
