# G-Snipers 海外版（Growth Sniper Overseas）

面向中国企业出海的 SaaS。标准版 = **软件 + 专属客户经理**。界面默认中文。

本仓库只做 **三条可操作交付链**。洞察只负责投喂，不另做机会分 / Share of Voice 看板。

**AI 是引擎，不是旁边的「生成草稿」按钮。** 分析 / 内容 / 审核 / 论证都走同一套 OpenAI 兼容网关（`LLM_API_KEY`）。人确认只用于：改线上、分发外发、标记可交付。低风险 AI 稿只落工作区。Key 未配时应用照常启动，AI 步骤返回 **未配置**，不编造分析。

## 三条链（产品本身）

### 1. 站内改页 + 人审

骨架对齐公开站内审计工具（清单 → 按严重级别分组 → 改稿 → 确认），**不是** Semrush 克隆，也不是一张裸 URL 表。

1. **抓这一站**（`POST /api/onsite/fetch-registered`）：只对已登记 URL（站点根 + `SitePage.path`）做 HTTP GET。认 robots.txt，跟随同主机跳转，抽出 TDK / H1 / canonical / hreflang / JSON-LD 到**观察层**。疑似 JS 空壳页会标「需要 JS」；若配置 Bright Data Browser API，则只对这类页面做浏览器渲染复查。
2. **分析**：按当前观察出 critical / high / low（TDK、标题、内链、schema、收录 / Canonical）。观察已满足的工单标 **已验收**。分析不改改稿，也不改线上。
3. **改稿草稿**：另一步，写在工单 `proposed_change`。**不准**写进 title / canonical / description 观察字段。
4. **确认上线**：人确认后回抓该页做验收。系统不向客户站 POST/PUT。

没有 GSC：收录显示 **未测**，禁止从 HTML 编收录数。关键词 → SERP 特征提纲是次要区块，SERP 特征未测。

### 2. GEO：中西引擎采样 → 工单 → 验收

骨架对齐公开 GeoLook 流程（问句集 → 采样槽 → 诊断层 → 带验收标准的工单 → 验收 / 复测重开），**不抄代码**。

- 西方：ChatGPT / Perplexity / Gemini / Claude
- 中国：DeepSeek / 豆包 / Kimi / 通义（手填或未配置均可，默认未测）
- **引用 ≠ 吸收**。brand.com 引用率在有人记录抽查前一律 **未测**。
- llms.txt、可引用性清单是本链资产，不是 SoV 仪表盘。
- 禁止把「已让 ChatGPT 引用」当交付物。

### 3. 外链核验 + 分发台

国内 G-Snipers 公开逻辑：一条一条核验 + 跟进，**不是**一键打到十几个平台。

- 断链式核验：我方 inbound / 待核验链接；状态 **未核验 / 有效 / 失效 / 垃圾**；跟进。不是 Ahrefs 外链指数，没有 DR。
- 分发：适配器接口 + 若干未配置占位。确认后若 Key 未配 → **未配置**，`sent: false`，不发 HTTP、不刷成功。
- 禁止代买、禁止静默外发。

## 洞察投喂

选市场 / 信号 → 开 **站内任务** / **GEO 工单** / **外链跟进**。机会分已停用，不再当工作台主角。

## 明确延期

- **SEM / Google Ads / MCC：** 延后。不用广告账户数据补齐看板。
- **Ahrefs / Semrush 外链指数：** 不做。
- **真实分发 HTTP：** 适配器已在，Key 后补。未配置时确认也不会发。
- **生产客户库：** 本期 Postgres + Alembic + 演示 seed。
- 旧路由（SEO 选题台、工单、询盘）仍可直接打开，**不在主导航**，避免空壳菜单。

## 权威源与生产档案

日常开发、提交、发版只认 **`origin` = [g-snipers-global](https://github.com/caocan326-oss/g-snipers-global.git)**。  
`upstream`（`g-snipers-overseas`）只做镜像，不要当主仓库。

生产机器、域名、SSH、发版步骤见 **[docs/PRODUCTION.md](docs/PRODUCTION.md)**。改线上之前先读这份档案，避免对错仓库或盖掉 `.env`。  
往 `www.weiyids.com` 发版用 **`deploy/sync-from-local.ps1`**，不要在服务器上 `git pull`。

## 本地启动

```bash
cp .env.example .env
docker compose up --build
```

- 前端 http://localhost:3000
- 演示登录 `am@demo.gsnipers.com` / `demo1234`

无 Docker：Postgres → `alembic upgrade head` → `python -m app.seed` → uvicorn + `npm run dev`。

## 环境变量

必填：`DATABASE_URL`、`SECRET_KEY`、演示账号。

可选（留空 = 未配置）：`LLM_API_KEY`（及 `LLM_BASE_URL` / `LLM_MODEL`）、`GSC_OAUTH_CLIENT_ID` / `GSC_OAUTH_CLIENT_SECRET` / `GSC_OAUTH_REDIRECT_URI`、`PAGESPEED_API_KEY`、`BING_WEBMASTER_API_KEY`、`INDEXNOW_KEY`、`DISTRIBUTION_*_API_KEY`。

Bright Data Browser API 用于 JS 空壳页的二次渲染复查，可选配置：`BRIGHTDATA_BROWSER_WS`、`ONSITE_RENDER_JS_ENABLED`、`ONSITE_RENDER_TIMEOUT_MS`。

Bright Data Dataset SERP API 用于目标国家/关键词下的 Google 搜索结果观察，使用「Google SERP - 100 Results - collect by URL」端点。可选配置：`BRIGHTDATA_DATASET_API_KEY`、`BRIGHTDATA_SERP_DATASET_ID`、`BRIGHTDATA_SERP_ENDPOINT`。Browser API 和 Dataset SERP API 是两条通道，不要混填。不要把真实连接串、Bearer Key 或密码提交进仓库。

GEO provider 层已区分非联网分析和联网 AI 搜索：`LLM_API_KEY` / DeepSeek 只做回答、分析和建议，`web_grounded=false`，不计入真实 citation。`PERPLEXITY_API_KEY`、`YOU_API_KEY`、`EXA_API_KEY`、`TAVILY_API_KEY` 是后续联网 AI 搜索 adapter 的预留配置位。

不要配置 `GOOGLE_ADS_*`。

## 数据与迁移

| 表 | 作用 |
| --- | --- |
| `site_pages` / `onsite_issues` | 站内页、问题、改稿草稿 |
| `geo_prompts` / `geo_observations` / `geo_tickets` | 问句、8 引擎槽、验收工单 |
| `geo_assets` / `geo_checklist_items` | llms.txt 与可引用清单 |
| `backlink_gaps` / `outreach_items` | 外链核验与跟进 |
| `distribution_jobs` / `distribution_attempts` | 分发队列与尝试 |

迁移：`001` … `006_ai_engine` → `007_onsite_live_fetch`。

## 测试

```bash
cd backend && pytest -q
```

覆盖：人审门（站内高风险、GEO 验收、分发确认）、未配置渠道不发送、8 个未测引擎槽、工单验收 / 重开、外链核验状态、洞察投喂三条链。

## 技术选择

Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Postgres；Next.js 14 + TypeScript + Tailwind + shadcn 风格组件；JWT Bearer。
