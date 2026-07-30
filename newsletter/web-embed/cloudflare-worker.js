// Cloudflare Worker — Newsletter 订阅代理
// 部署到 Cloudflare Workers Dashboard 或通过 wrangler CLI
//
// 使用场景: 如果想让网站表单直接提交 (不通过 mailto:)
// Listmonk 运行在 localhost 时不可公开访问, 此 Worker
// 通过环境变量接收 Resend API Key, 将订阅请求直接发到 Resend。
//
// 设置环境变量:
//   RESEND_API_KEY = re_xxx
//   LISTMONK_URL   = https://你的-tunnel-url (如果暴露了 Listmonk)

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    const { email, name } = await request.json();
    if (!email) {
      return new Response(JSON.stringify({ error: "email required" }), {
        status: 400, headers: { "Content-Type": "application/json" }
      });
    }

    // 方案 A: 如果有可访问的 Listmonk 实例
    if (env.LISTMONK_URL) {
      const resp = await fetch(`${env.LISTMONK_URL}/api/public/subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email, name: name || "",
          list_uuids: [env.LIST_UUID || ""],
        }),
      });
      return new Response(await resp.text(), {
        status: resp.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    // 方案 B: 通过 Resend Contacts API
    if (env.RESEND_API_KEY && env.RESEND_AUDIENCE_ID) {
      const resp = await fetch("https://api.resend.com/audiences/${env.RESEND_AUDIENCE_ID}/contacts", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, first_name: name || "" }),
      });
      return new Response(await resp.text(), {
        status: resp.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "not configured" }), { status: 500 });
  }
}
