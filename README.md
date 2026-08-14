# G-Snipers 海外版（Growth Sniper Overseas）

面向中国企业出海的 SaaS。标准版 = **软件 + 专属客户经理**。界面默认中文。

本仓库只做 **三条可操作交付链**。洞察只负责投喂，不另做机会分 / Share of Voice 看板。

## 三条链（产品本身）

### 1. 站内改页 + 人审

骨架对齐公开站内审计工具（清单 → 按严重级别分组 → 改稿 → 确认），**不是** Semrush 克隆，也不是一张裸 URL 表。

1. **crawl-or-seed**：从已登记页的内链扩清单（不请求客户站点，不接 GSC）
2. **分析**：按 critical / high / low 产出问题（TDK、标题、内链、schema、收录 / Canonical）。分析 **不改** 工作区字段
3. **改稿草稿**：另一步，写 `proposed_change`
4. **应用**：低风险写入工作区；critical / high 必须确认，且仍不向线上发 HTTP

没有 GSC：收录 / Canonical 指标显示 **未测**，禁止用 0 页充数。关键词 → SERP 特征提纲是次要区块，SERP 特征未测。

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

- **SEM / Google Ads / MCC / OAuth / GSC：** 不接（负责人暂无广告/GSC 测试账号）。需要这些源的指标显示 **未测**。
- **Ahrefs / Semrush 外链指数：** 不做。
- **真实分发 HTTP：** 适配器已在，Key 后补。未配置时确认也不会发。
- **生产客户库：** 本期 Postgres + Alembic + 演示 seed。
- 旧路由（SEO 选题台、工单、询盘）仍可直接打开，**不在主导航**，避免空壳菜单。

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

可选（留空 = 未配置）：`DISTRIBUTION_DIRECTORY_API_KEY`、`DISTRIBUTION_GUEST_API_KEY`、`DISTRIBUTION_SYNDICATION_API_KEY`。

不要配置 `GOOGLE_ADS_*`。

## 数据与迁移

| 表 | 作用 |
| --- | --- |
| `site_pages` / `onsite_issues` | 站内页、问题、改稿草稿 |
| `geo_prompts` / `geo_observations` / `geo_tickets` | 问句、8 引擎槽、验收工单 |
| `geo_assets` / `geo_checklist_items` | llms.txt 与可引用清单 |
| `backlink_gaps` / `outreach_items` | 外链核验与跟进 |
| `distribution_jobs` / `distribution_attempts` | 分发队列与尝试 |

迁移：`001_initial` → `002_geo` → `003_onsite_offsite_dist` → `004_three_chains` → `005_onsite_severity`。

## 测试

```bash
cd backend && pytest -q
```

覆盖：人审门（站内高风险、GEO 验收、分发确认）、未配置渠道不发送、8 个未测引擎槽、工单验收 / 重开、外链核验状态、洞察投喂三条链。

## 技术选择

Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Postgres；Next.js 14 + TypeScript + Tailwind + shadcn 风格组件；JWT Bearer。
