# G-Snipers 海外版（Growth Sniper Overseas）

面向中国企业出海的 SaaS。标准版 = **软件 + 专属客户经理**。

一期切片（同一产品，不是第二套系统）：

1. **全球洞察中心** — 市场 / 需求信号 / 竞品 / 简报，喂给 SEO（也可加入 GEO 监测）
2. **多语言 SEO 工作台** — 大纲 → 正文 → Meta → 人工确认可交付
3. **站内优化** — TDK、标题、内链、结构化数据、收录/抓取任务
4. **站外优化** — 竞品外链 / 引荐域缺口 + 外联跟进
5. **外链分发台** — 多渠道适配器；未配 Key 显示未配置
6. **GEO** — 旁路监测与资产，不是英雄模块，也不是验收 KPI

工单与询盘是细骨干。**seed 演示数据即可点开验收**；真实数据库由你们之后提供。

## 监测 → 执行分级

公开资料里，国内 G-Snipers 把工作分成监测（发现问题）和执行（落地），并按风险分级：低风险优化可自动/半自动推进，高风险页面改动先出方案、**人工确认后再上线**（例如批量 noindex）。海外版沿用同一纪律，不抄任何专有代码：

| 风险 | 本切片怎么做 |
| --- | --- |
| 低风险（补 TDK 草稿、记内链） | 可在工作区「落草稿」，不碰线上站点 |
| 高风险（结构化数据上线、收录/抓取处置、分发外发） | 必须 `confirmed: true`，且本切片仍不自动改客户线上站 |

没有 GSC / Ahrefs / Semrush 时，指标显示 **未测**，不用 0 或 0% 充数。

## 明确延期

- **SEM / Google Ads：** 无 OAuth、MCC、广告连接（含死按钮）。启动不需要 `GOOGLE_ADS_*`。
- **真实生产库：** 本期 Postgres + Alembic + seed。
- **分发渠道真实调用：** 适配器已在，Key 由你们后补。未配置时确认也不会发、不会刷成功数。

## GEO

问句默认未测；不算引用率 / Share of Voice；不是「已让 ChatGPT 引用」交付。

## 本地启动

```bash
cp .env.example .env
docker compose up --build
```

- 前端 http://localhost:3000
- 演示 `am@demo.gsnipers.com` / `demo1234`

无 Docker：Postgres → `alembic upgrade head` → `python -m app.seed` → uvicorn + `npm run dev`。

## 环境变量

`.env.example`：`DATABASE_URL`、`SECRET_KEY`、演示账号即可。

可选（留空 = 未配置）：`DISTRIBUTION_DIRECTORY_API_KEY`、`DISTRIBUTION_GUEST_API_KEY`、`DISTRIBUTION_SYNDICATION_API_KEY`。

## 主要数据表

原有洞察 / SEO / GEO 表之外：

| 表 | 作用 |
| --- | --- |
| `site_pages` / `onsite_issues` | 站内页与监测任务 |
| `backlink_gaps` / `outreach_items` | 站外缺口与外联 |
| `distribution_jobs` / `distribution_attempts` | 分发队列与尝试记录 |

迁移：`001_initial`、`002_geo`、`003_onsite_offsite_dist`。

## 测试

```bash
cd backend && pytest -q
```

覆盖站内列表/创建与风险门、站外缺口/外联、分发未配置不发送、以及原有洞察 / SEO / GEO。

## 技术选择

Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Postgres；Next.js 14 + TypeScript + Tailwind + shadcn 风格组件；JWT Bearer。
