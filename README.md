# G-Snipers 海外版（Growth Sniper Overseas）

面向中国企业出海的 SaaS。标准版 = **软件 + 专属客户经理**。

本仓库一期切片：

1. **全球洞察中心** — 目标市场、机会分、需求信号、竞品、简报；信号喂给 SEO 选题（也可加入 GEO 监测）
2. **多语言 SEO 工作台** — 选题 → 大纲 → 正文 → Meta → 审核 → 人工确认可交付
3. **GEO 监测 + 资产** — 问句抽查、llms.txt 草稿、可引用清单。挂在 SEO 旁边，**不是英雄模块，也不是验收 KPI**

工单与询盘是细骨干。本地 **seed 演示数据**即可登录验收；你们之后会接真实数据库。

## 明确延期

**SEM / Google Ads：** 不实现 OAuth、MCC、广告账户连接、广告系列同步（包括死按钮）。没有 Ads 测试账号前不做。启动**不需要** `GOOGLE_ADS_*`。

**真实生产库：** 本期用 Postgres + Alembic + seed。上线后由你们提供/切换数据库再测。

## GEO 怎么读（避免误售）

- 问句按引擎建观测槽，默认 **未测**。客户经理抽查后才改成「出现 / 未出现 / 被引用」。
- **不计算、不展示引用率或 Share of Voice。** 算不出来就显示未测，**禁止用 0% 冒充没被引用**。
- 不是「已让 ChatGPT 引用你们」的交付。llms.txt 只是草稿，确认后也不自动挂到客户域名。

## 本切片做了什么

- 多租户 + JWT 登录；演示账号可直接用
- 洞察 → SEO 选题；洞察 → GEO 监测问句
- SEO 执行器（大纲 / 正文 / Meta）+ 人工确认门
- GEO：监测、llms.txt、可引用清单（均从 未测 起）
- 工单类型含 `geo_monitor` / `geo_asset`
- 中文浅色后台

## 本切片不做

- Google Ads / Meta 深度管理
- 虚构的 Google / SERP / 模型引用 API
- 新媒体中心、ROI 总看板、关键词研究大盘
- 把 GEO 做成「引用率仪表盘」

## 本地一键启动

```bash
cp .env.example .env
docker compose up --build
```

- 前端 http://localhost:3000
- 后端 http://localhost:8000/docs
- 演示：`am@demo.gsnipers.com` / `demo1234`

无 Docker 时：起 Postgres → `alembic upgrade head` → `python -m app.seed` → uvicorn + `npm run dev`。

前端 `/api/*` rewrite 到后端，没有 mock-only 服务层。

## 环境变量

见 `.env.example`。`DATABASE_URL`、`SECRET_KEY`、演示账号即可。不要提交 `.env`。

## 数据表

洞察 / SEO：`tenants` `users` `markets` `competitors` `demand_signals` `insight_briefs` `seo_pages` `work_orders` `inquiries` `publish_confirmations`

GEO：`geo_prompts` `geo_observations` `geo_assets` `geo_checklist_items`

迁移：`001_initial.py`、`002_geo.py`。

## 测试

```bash
cd backend && pytest -q
```

含登录、洞察、SEO 确认门、GEO 未测槽位 / 禁止假引用率、llms.txt 确认门、清单默认未测。

## 技术选择

Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Postgres；Next.js 14 + TypeScript + Tailwind + shadcn 风格组件；JWT Bearer。
