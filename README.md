# G-Snipers 海外版（Growth Sniper Overseas）

面向中国企业出海的 SaaS。标准版 = **软件 + 专属客户经理**。

本仓库的一期切片只做产品优先级的前两块：

1. **全球洞察中心** — 按目标市场维护机会判断、需求信号、竞品与简报
2. **多语言 SEO 工作台** — 从选题做到大纲 / 正文 / Meta，而不是只做诊断

工单与询盘是支撑工作台运转的细骨干，不是广告投放系统。

## 本切片做了什么

- 多租户工作区（`tenants` + `users`）。JWT 登录（`PyJWT` + `bcrypt`），演示账号可直接用。
- 洞察：目标市场列表与详情、机会分、竞品、需求信号、市场简报。需求信号可一键开成 SEO 选题。
- SEO 工作台：选题列表与编辑器，按语言写大纲 → 正文 → Meta → 提交审核。
- **人工确认门**：`POST /api/seo-pages/{id}/mark-ready` 必须 `confirmed: true`，否则拒绝。本切片不会自动发布到任何站点或广告平台。
- 工单：创建 / 列表 / 筛选 / 领取 / 改状态。类型仅限 `insight` / `seo_outline` / `seo_draft` / `seo_meta` / `other`。
- 询盘：创建 / 列表，可挂到客户市场、选题或工单。
- 中文默认界面，浅色专业后台。

洞察与 SEO 的信息架构参考了公开产品（市场洞察侧：按国家/市场看机会与竞品再出简报；SEO 侧：Surfer / Frase 一类「大纲 → 正文 → Meta → 发布前检查」执行器），但实现全部落在自有 Postgres 表上。

## 本切片明确不做

- Google Ads / Meta 深度管理、OAuth、MCC、广告系列列表、改预算、自动投放
- GEO 监控、Share of Voice、新媒体中心、ROI 总看板
- 关键词研究工具、站点体检、mock 出来的无用模块大盘
- 任何虚构的 Google / SERP API。大纲与正文是**本地模板**，供客户经理改稿；需求信号是工作区内存量（`source=manual`），以后再接真实数据源

## 本地一键启动

需要 Docker。在仓库根目录：

```bash
cp .env.example .env
docker compose up --build
```

- 前端：http://localhost:3000
- 后端：http://localhost:8000 （文档：http://localhost:8000/docs）
- Postgres：localhost:5432（用户/库 `gsnipers` / 密码见 `.env.example`）

演示客户经理（seed 写入，无需注册）：

- 邮箱：`am@demo.gsnipers.com`
- 密码：`demo1234`

登录后首页是洞察 / SEO / 工单 / 询盘数字；侧栏进入「全球洞察中心」与「SEO 工作台」。

### 不用 Docker 时

```bash
# 先自己起 Postgres，并设置 DATABASE_URL
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

前端通过 Next.js rewrite 把浏览器的 `/api/*` 转到 `BACKEND_INTERNAL_URL`（默认 `http://localhost:8000`）。没有 mock-only 服务层。

## 环境变量

见 `.env.example`。必填/常用：

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy 连接串（`postgresql+psycopg://...`） |
| `SECRET_KEY` | JWT 签名 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 登录有效期 |
| `FRONTEND_ORIGIN` | CORS |
| `DEMO_AM_EMAIL` / `DEMO_AM_PASSWORD` | seed 演示账号 |

**不要提交 `.env` 或真实密钥。**

## 数据表（一期）

| 表 | 作用 |
| --- | --- |
| `tenants` | 客户工作区 |
| `users` | 客户经理 / 成员 |
| `markets` | 目标市场（国家、语言、机会分、状态） |
| `competitors` | 市场下的竞品 |
| `demand_signals` | 需求主题（人工录入） |
| `insight_briefs` | 每市场一份简报 |
| `seo_pages` | 多语言选题：大纲 / 正文 / Meta / 状态 |
| `work_orders` | 工单 |
| `inquiries` | 询盘 |
| `publish_confirmations` | 人工确认「可交付」的审计记录 |

迁移：Alembic（`backend/alembic/versions/001_initial.py`）。

## 测试

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

覆盖登录、洞察 CRUD、需求信号开选题、SEO 大纲/正文/Meta、未确认不可标记可交付、工单领取与状态、询盘挂接。

## 技术选择（故意选常见方案）

- 后端：Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Postgres
- 前端：Next.js 14 App Router + TypeScript + Tailwind + 自建 shadcn 风格组件
- 鉴权：JWT Bearer，存在浏览器 `localStorage`（一期足够；生产可再改 HttpOnly Cookie）
