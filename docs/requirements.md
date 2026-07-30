# FengCRM 需求文档

> 基于 harperreed/crm (Go, MCP 底座) 二次开发
> 目标：一个 AI 原生、邮件驱动的个人 CRM，轻量单二进制

---

## 1. 核心原则

- **单二进制交付** — 一个 .exe 搞定，Go 编译，压缩后 ~10MB 以内
- **零外部依赖** — 不需要装数据库、不需要 Node.js/PHP/Python 运行时、不需要 Docker
- **完全开源免费** — 不自托管 SaaS，没有付费墙
- **AI 原生** — 所有操作通过 MCP 让 Claude 说话完成，Web UI 是辅助

## 2. 功能需求

### 2.1 联系人管理 (Contacts)

| 功能 | 说明 |
|------|------|
| 增删改查联系人 | 姓名、邮箱、电话、公司、备注 |
| 标签分类 | 自定义标签（求职、客户、朋友、面试官等）|
| 公司关联 | 联系人与公司关联（works_at / founder_of）|
| 搜索 | 全文搜索姓名、邮箱、备注 |
| 最后联系时间 | 每次记录交互时自动更新 |
| 下次联系提醒 | 设定提醒日期，"张三 7 天没联系了" |

### 2.2 公司管理 (Companies)

| 功能 | 说明 |
|------|------|
| 增删改查公司 | 名称、域名、行业、备注 |
| 人员关联 | 谁在这家公司 |

### 2.3 提醒/跟进

| 功能 | 说明 |
|------|------|
| 自动计算"过期未联系" | 超过 N 天未联系的自动标记 |
| 提醒列表 | "张三(12天) 李四(8天)" |
| Claude 主动提醒 | 通过 MCP 工具，Claude 在对话中主动说"有 X 人好久没联系了" |
| Web UI 提醒看板 | 网页上能看到提醒列表 |

### 2.4 Web UI

| 功能 | 说明 |
|------|------|
| 联系人列表 | 表格视图，类似电子表格 |
| 个人信息弹窗 | 点击查看联系人详情、历史交互、关联公司 |
| 提醒/过期看板 | 侧边栏展示 "X 人过期未联系" |
| 基础 CRUD | 增删改查在 Web 上也可操作 |
| 搜索/筛选 | 按标签、公司搜索 |

### 2.5 MCP 工具（Claude 说话操作）

| 工具 | 作用 |
|------|------|
| 现有 12 工具 | 联系人/公司 CRUD + 关系链（保留原能力）|
| **新增: list_stale_contacts** | 查超过 N 天没联系的人 |
| **新增: log_interaction** | 记录和某人的交互（自动更新 LastContactedAt）|
| **新增: get_follow_ups** | 获取待提醒列表 |
| **新增: suggest_contact** | 给当前上下文推荐应联系的人 |

### 2.6 FengMail 联动

| 方向 | 方式 |
|------|------|
| **邮件 → CRM** | 收到某人邮件 → 自动更新该联系人的 LastContactedAt |
| **CRM → 邮件** | 提醒"该联系张三了" → 可触发写邮件 |
| **数据共享** | CRM 和 FengMail 共用同一个 SQLite 文件？或通过 CLI 互相调用 |

## 3. 非功能需求

| 需求 | 目标 |
|------|------|
| 单二进制大小 | **< 10MB**（Go 编译，静态嵌入前端资源）|
| 数据库 | **SQLite** 内嵌，零配置 |
| 启动速度 | 瞬间启动 |
| Web UI 加载 | 嵌入 HTML，无需外部 CDN |
| 内存占用 | < 50MB |
| 平台 | Windows 优先（用户目前 Windows 11）|

## 4. 架构设计思路

```
┌──────────────────────────────────────────────────┐
│                   fengcrm.exe                      │
│  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  Web UI      │  │  MCP Server│  │  CLI     │  │
│  │  (net/http)  │  │  (stdio)   │  │  (cobra) │  │
│  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  │
│         │                │              │         │
│         └────────┬───────┘──────────────┘         │
│                  │                                │
│            ┌─────┴──────┐                         │
│            │  Storage   │                         │
│            │  (SQLite)  │                         │
│            └─────┬──────┘                         │
└──────────────────┼────────────────────────────────┘
                   │
          ┌────────┴────────┐
          │  fengcrm.db     │
          │  (SQLite 文件)   │
          └────────┬────────┘
                   │
          ┌────────┴────────┐
          │  FengMail       │
          │  (同 DB 读/写)   │
          └─────────────────┘
```

### 轻量 + 全功能 怎么做

**关键选择：**

1. **Web UI 前端 → 纯原生 HTML/CSS/JS**
   - 不引入 React/Vue/Svelte，零 npm 依赖
   - Go embed 直接打包到二进制
   - 参考给了 `crm-table-live.html` 的风格，只取 Grid 视图 + 侧边栏
   - 用 `fetch()` 调后端的 REST API

2. **REST API → Go 标准库 net/http**
   - Go 自带的 `net/http` 就够了，不需要 gin/chi 等框架
   - 路由用 `http.ServeMux`（Go 1.22+ 支持路径参数）
   - 返回 JSON，前端直接消费

3. **提醒机制 → 字段 + MCP + Web UI**
   - Contact 加 `LastContactedAt` + `NextFollowUpAt` 字段
   - 不需要跑定时任务，MCP 工具实时查
   - Web UI 打开时 fetch 一次获取所有过期联系人

4. **FengMail 联动 → 共享 SQLite**
   - 最简单：CRM 和 FengMail 读写同一个 SQLite 文件
   - Python 的 sqlite3 模块可以直接查/写
   - 不需要网络 IPC，性能最好

### 文件结构

```
~/FengCRM/
├── main.go              # 入口（CLI + Web + MCP 合一）
├── cmd/
│   ├── root.go          # cobra 根命令
│   ├── mcp.go           # MCP server 子命令
│   ├── web.go           # Web UI 子命令
│   ├── contacts.go      # 联系人 CLI
│   ├── companies.go     # 公司 CLI
│   └── relationships.go # 关系 CLI
├── internal/
│   ├── models/          # Contact + Company + Relationship
│   ├── storage/         # SQLite 存储
│   ├── mcp/             # MCP 工具（新增 stale/followup 工具）
│   ├── web/             # Web UI（HTTP server + embed HTML）
│   └── config/          # 配置
├── web/
│   ├── index.html       # 主页面（嵌入 Go 二进制）
│   ├── style.css        # 样式
│   └── app.js           # 前端逻辑（fetch API + 渲染）
├── go.mod
└── Makefile
```
