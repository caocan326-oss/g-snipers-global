# Google API 中转（Cloudflare Worker）

北京机访问不了 `googleapis.com`。浏览器授权仍直连 Google；**换 token、同步 Search Console 必须走这个 Worker**。不要买香港机。不要做开放代理。

密钥只放 Cloudflare Secret 和服务器 `.env`，不要写进仓库。

---

## 1. 建 Worker

1. 注册 [Cloudflare](https://dash.cloudflare.com/sign-up)，进入 **Workers & Pages**。
2. **Create** → 用 HTTP 模板即可，再把本目录 `src/index.js` 贴进去。或本机：

```powershell
cd deploy/google-relay-worker
npx wrangler@4 login
npx wrangler@4 secret put RELAY_KEY
# 粘贴一条自己生成的长随机串，和服务器 GOOGLE_RELAY_KEY 同一条
npx wrangler@4 deploy
```

3. 记下地址，形如 `https://g-snipers-google-relay.xxx.workers.dev`。
4. 可选：在 Worker 设置里加变量 `RELAY_ALLOW_IPS=39.97.52.149`，只让北京公网 IP 进来。

没有 `x-relay-key` 或密钥不对 → **401**。目标不是 Google 允许的主机 → **403**。

允许转发的主机：`oauth2.googleapis.com`、`www.googleapis.com`、`searchconsole.googleapis.com`、`pagespeedonline.googleapis.com`。

先测 GSC（换 token / 同步，几秒内）。通了再测 PageSpeed。PageSpeed 常要 20–60 秒；Cloudflare 免费 Worker 墙钟大约 30 秒，可能超时。若超时：Worker 换成付费，或暂时仍走 17CE。GSC 不受影响。

---

## 2. 在 Google 开接口（只做 GSC）

1. [Google Cloud Console](https://console.cloud.google.com/) 新建项目。
2. 启用 **Search Console API**。不要现在开 Google Ads（SEM 延期，审核也慢）。
3. **凭据** → 创建 OAuth 客户端 ID → 应用类型 **Web 应用**。
4. 授权重定向 URI 必须和工作台现有回调一致：
   - 生产：`https://www.weiyids.com/onsite`
   - 本机：`http://localhost:3000/onsite`
5. 把 Client ID / Secret 写进服务器 `.env` 的 `GSC_OAUTH_*`，或工作台「数据源」里。不要提交进 git。
6. OAuth 同意屏幕：外部用户至少加上测试用户邮箱，否则客户点授权会被拒。

---

## 3. 北京只调中转

服务器 `.env`（不进 git）：

```
GOOGLE_RELAY_URL=https://g-snipers-google-relay.xxx.workers.dev
GOOGLE_RELAY_KEY=与 Worker RELAY_KEY 相同
GSC_OAUTH_CLIENT_ID=...
GSC_OAUTH_CLIENT_SECRET=...
GSC_OAUTH_REDIRECT_URI=https://www.weiyids.com/onsite
```

改 `.env` 后 `docker compose up -d` 重启 backend。不要 `git pull`。

用户点「打开授权页」：浏览器去 `accounts.google.com`（不经过北京）。  
回跳带 `code` 后，后端换 token、刷新 token、同步 28 天：只请求 `GOOGLE_RELAY_URL`，头里带 `x-relay-key` 和 `x-relay-target`。

未配中转时，本机开发仍可直连 Google（方便 pytest）。**生产必须配中转**，否则北京同步会继续失败。
