# G-Snipers 海外版 · 生产档案

最后更新：2026-08-22。  
这份文件是**唯一权威运维记录**。机器、仓库、域名有变动时，先改这里再动手。

换机器开工、日常动作清单：先读 **`docs/HANDOVER.md`**（问「交接文档在哪里」就指这个文件）。

---

## 1. 权威源（不要弄混）

| 角色 | 是什么 | 怎么用 |
| --- | --- | --- |
| **代码权威** | GitHub `origin`：https://github.com/caocan326-oss/g-snipers-global.git | 开发、PR、发版只认这个 |
| **镜像远端** | GitHub `upstream`：https://github.com/caocan326-oss/g-snipers-overseas.git | 只做同步，不在这里开新分支当主仓 |
| **本机工作副本** | 公司 `E:\G-snipers海外版`；家里 `D:\workspace\G-snipers海外版` | 两台不同时改；`main` 跟踪 `origin/main` |
| **生产工作副本** | 服务器 `/opt/g-snipers-overseas` | `main` 跟踪 `origin/main`，用 git 拉代码 |
| **空目录（不要当代码）** | 服务器 `/opt/g-snipers-global` | 只剩旧 `.env`，不是在跑的应用 |

2026-08-20 之前的混乱：

- `g-snipers-overseas` 停在 `Initial commit`（2026-08-14），比 `g-snipers-global` 少 28 个提交。
- 生产目录**不是 git 仓库**，只能整包覆盖，对不上提交号。
- 本机同时挂了两个远端，容易拉错。

2026-08-20 已改成：两个远端都指向同一条 `main`，生产目录变成 git checkout。

本机 `.git/config` 约定：

```
origin    = g-snipers-global     （主）
upstream  = g-snipers-overseas   （镜像）
```

---

## 2. 服务器

| 项 | 值 |
| --- | --- |
| 云厂商 | 阿里云轻量应用服务器 |
| 控制台名 | 网站 |
| 地域 | 华北2（北京） |
| 实例 ID | `1c3a1380f07441189248138b500f6652` |
| 公网 IP | `39.97.52.149` |
| 内网 IP | `172.24.17.112` |
| 系统 | Ubuntu 24.04 |
| 规格 | 2 vCPU / 4 GiB / 50 GiB ESSD |
| 到期 | 2027-03-18 |
| 主机名 | `iZ2zed9w1py6es9eo815idZ` |

### SSH

- 用户：`root`
- 本机配置名：`g-snipers-server`（模板见 `deploy/ssh-config.example`）
- **实际能登录的私钥**：本机 `~/.ssh/g_snipers_deploy`（ed25519）
- 阿里云密钥对 `skp-2zehd3z48xts55v24kzm` / 本机 `Downloads\C0.pem`：**未绑定到这台机**，不要用它登录。不要把私钥提交进仓库。

```bash
ssh g-snipers-server
```

### 阿里云防火墙（控制台，不是机器 UFW）

机器 UFW 关闭，iptables INPUT 默认 ACCEPT。拦端口的是轻量控制台防火墙。

需要放行：`22`（SSH）、`80`（HTTP / 证书续期）、`443`（HTTPS）。  
2026-08-20 已确认 443 对公网开放。控制台里还能看到 `11603`、`1337` 等旧规则，与本应用无关。

---

## 3. 域名与证书

| 项 | 值 |
| --- | --- |
| 正式地址 | https://www.weiyids.com |
| `www.weiyids.com` | A → `39.97.52.149` |
| `weiyids.com`（不带 www） | **没有 A 记录**，证书也没签这个名字 |
| 证书 | Let's Encrypt，`/etc/letsencrypt/live/www.weiyids.com/` |
| 证书到期 | 2026-11-17 |
| 续期 | `certbot.timer` 已 enabled |
| Nginx 站点 | `/etc/nginx/sites-available/g-snipers` → `sites-enabled/g-snipers` |
| 档案副本 | `deploy/nginx/g-snipers.live.conf` |

反代：

- `/` → `127.0.0.1:3000`（前端容器）
- `/api/` → `127.0.0.1:8000`（后端容器）
- `http://www.weiyids.com` → 301 → HTTPS

以后要让裸域也能开：先给 `weiyids.com` 加 A 记录，再：

```bash
certbot --nginx -d www.weiyids.com -d weiyids.com
```

---

## 4. 生产目录与进程

| 路径 | 作用 |
| --- | --- |
| `/opt/g-snipers-overseas` | **正在跑的应用**（git checkout） |
| `/opt/g-snipers-overseas/.env` | 线上密钥，**不进 git** |
| `/opt/g-snipers-backups` | 旧的发版前代码 tar，仍在同一块盘上，不算异地 |
| `/opt/g-snipers-db-exports` | 客户库导出落点（compose `BACKUP_HOST_DIR`）。cron 每天 03:15 UTC 打一份 |
| `/opt/g-snipers-overseas-backup-*.tgz` | 历史代码包（8 月中旬密集备份，可日后清理） |
| `/opt/g-snipers-global` | 空壳，不要当发版目标 |
| `/root/strapi-news.tar.gz` | 与本项目无关 |

Docker Compose 项目名：`g-snipers-overseas`  
配置文件：`/opt/g-snipers-overseas/docker-compose.yml`

| 容器 | 端口 | 说明 |
| --- | --- | --- |
| `g-snipers-overseas-frontend-1` | 3000 | Next.js |
| `g-snipers-overseas-backend-1` | 8000 | FastAPI（启动时 alembic + seed） |
| `…-postgres-1` | 无宿主机端口 | Postgres 16。只在 compose 网络里给 backend 用，不映射 5432。本机查库：`docker compose exec postgres psql -U gsnipers` |

`FRONTEND_ORIGIN` 必须从 `.env` 读。生产应为 `https://www.weiyids.com`。compose 里不要再写死 `http://localhost:3000`。

---

## 5. 环境变量（只记名字，不记密钥）

线上 `.env` 在服务器上，已被 `.gitignore` 排除。  
`.env.bak-*` 也忽略，不要提交。

必填：`SECRET_KEY`、`DATABASE_URL`、`FRONTEND_ORIGIN`  
演示：`DEMO_AM_EMAIL`、`DEMO_AM_PASSWORD`、`DEMO_LOGIN_ENABLED`  
管理员：`ADMIN_EMAIL`、`ADMIN_PASSWORD`、`ADMIN_NAME`（密码只写服务器 `.env`）

compose 会覆盖数据库地址为容器内：

`postgresql+psycopg://gsnipers:gsnipers@postgres:5432/gsnipers`

可选（空 = 未配置）：`LLM_*`、`PAGESPEED_API_KEY`、`GSC_*`、`GOOGLE_RELAY_URL`、`GOOGLE_RELAY_KEY`、`BING_*`、`INDEXNOW_*`、`BRIGHTDATA_*`、`DISTRIBUTION_*`、`PERPLEXITY_API_KEY`、`YOU_API_KEY`、`EXA_API_KEY`、`TAVILY_API_KEY`、`BOCHA_*`、`DASHSCOPE_*`

北京访问不了 Google。GSC 换 token / 同步、以及 Google PageSpeed，必须走 Cloudflare Worker（`deploy/google-relay-worker/`）。生产中转地址是橙云 `https://relay.weiyids.com`，不要再用 `workers.dev`。`GOOGLE_RELAY_KEY` 只写服务器 `.env` 和 Cloudflare Secret。中转配上后测速不再走 17CE。

排名走 Bright Data **SERP API 区**（生产 `BRIGHTDATA_SERP_ZONE=serp_api1`，`BRIGHTDATA_SERP_ENDPOINT=https://api.brightdata.com/request`）。不要用浏览器区 `scraping_browser1`，不要再用 Dataset scrape。`BING_*`、`INDEXNOW_*` 可空，不挡交付。

禁止：`GOOGLE_ADS_*`。  
禁止：把真实 Key、连接串、密码写进仓库或这份档案。

---

## 6. 日常开发

```bash
# 本机（公司 E:\G-snipers海外版，家里 D:\workspace\G-snipers海外版）
cd <本机仓库根目录>
git checkout main
git pull origin main
# 改代码、测
git push origin main
git push upstream main    # 保持镜像同步，避免有人 clone 到旧仓
```

逐步动作见 `docs/HANDOVER.md`。

不要在 `upstream` 上单独提交。不要 `git pull upstream` 除非你在修镜像。

本地 Docker：`cp .env.example .env` 后 `docker compose up --build`。  
演示登录：`am@demo.gsnipers.com` / `demo1234`（只用于演示租户）。

---

## 7. 发版到生产

**不要在服务器上 `git pull origin`。** 华北2 轻量访问 GitHub HTTPS 会一直卡住（2026-08-20 已踩过，`git-remote-https` 无响应）。

正确顺序：

1. 本机：`git push origin main` 且 `git push upstream main`（两个远端保持同一提交）
2. 本机执行：

```powershell
powershell -File deploy/sync-from-local.ps1
```

改了 Dockerfile / 依赖时加 `-Rebuild`。

脚本会：打 `git bundle` → `scp` 到机器 → `git fetch` 本地包 → checkout `main` → `docker compose up -d`。  
`.env` 不在包里，不会被覆盖。

硬性规则：

1. **只拉 `origin/main`。** 不要从本机 rsync 整目录覆盖（会把 `.env`、证书思路打乱）。
2. **不要提交或覆盖线上 `.env`。**
3. **不要用 `git reset --hard` 除非你明确要丢掉服务器上的临时改动。**
4. Nginx / 证书不在每次发版里动。改反代先改 `/etc/nginx/sites-available/g-snipers`，`nginx -t` 再 reload，并回写 `deploy/nginx/g-snipers.live.conf` 与本档案日期。
5. 发版前可打一份代码 tar：`tar -C /opt -czf /opt/g-snipers-backups/pre-$(date +%Y%m%d%H%M%S).tgz g-snipers-overseas --exclude=g-snipers-overseas/.git`。这不是数据库，也不在机器外。
6. 客户库副本：管理员页 `/ops/backup` 可导出并下载。宿主机落点 `BACKUP_HOST_DIR=/opt/g-snipers-db-exports`。`deploy/backup-postgres.sh` 打 Postgres 自定义格式。**2026-08-22 已装** `/etc/cron.d/g-snipers-backup`（每天 03:15 UTC）。cron 只写本机落点，不自动推到第二台云。出机器：在家里/公司跑 `powershell -File deploy/pull-db-backup.ps1`，落到仓库旁边的 `g-snipers-db-offsite/`（不进 git）。第一次已通：`gsnipers-db-20260821-173000.dump`（390KB，SHA256 `e1e2e7ea…c54ff1`）已拉到家里 `D:\workspace\g-snipers-db-offsite\`。`BACKUP_OFFSITE_KIND` 仍是 `none`（没有第二台可 scp 的机器）。
7. 探活：UptimeRobot（托管，不自建）盯 `https://www.weiyids.com/api/health`。2026-08-22 已提交，**邮箱已确认，监控已在跑**。告警到 `caocan326@gmail.com`。没有原生微信；手机开 Gmail 推送，或后台加 Telegram。

---

## 8. 变更记录

| 日期 | 谁 | 做了什么 |
| --- | --- | --- |
| 2026-08-14 | 仓库 | `g-snipers-overseas` 只有 Initial commit |
| 2026-08-15～17 | 生产 | 多次整包备份到 `/opt/*.tgz`；Docker 跑海外版 |
| 2026-08-18 01:31 | 本机/origin | `ebcc4dd` chore: use regional mirrors for docker builds（当时生产文件与此版对齐，但目录不是 git） |
| 2026-08-20 | 运维 | `www.weiyids.com` 申请 Let's Encrypt；HTTP→HTTPS；Nginx `server_name` 写入该域名 |
| 2026-08-20 | 运维 | 确立 `g-snipers-global` 为权威源；镜像同步 `g-snipers-overseas`；生产目录改为 git；本档案入库 |
| 2026-08-20 | 代码 | compose 的 `FRONTEND_ORIGIN` 改为读环境变量；`.gitignore` 忽略 `.env.*` |
| 2026-08-20 | 运维 | 生产目录已是 `57df684` 的 git checkout；`FRONTEND_ORIGIN=https://www.weiyids.com`；发现服务器无法 `git pull` GitHub，发版改走 `deploy/sync-from-local.ps1` |
| 2026-08-20 | 文档 | 增加换机交接清单 `docs/HANDOVER.md`；本机路径写明公司 E: / 家里 D: |
| 2026-08-20 | 产品 | 站内链增加当前步骤与一句说明；客户说明/清单改成清楚克制的用词；未发版 |
| 2026-08-20 | 产品 | GEO 工作台与总览改成同一套话；客户说明页合成「本周说明」预览；未发版 |
| 2026-08-20 | 产品 | 总览不再重复计算紧急问题；买家问题与检查条数分开写；演示数据与步骤条对齐；未发版 |
| 2026-08-20 | 运维 | 生产发到 `9dbf4d0`（`sync-from-local.ps1 -Rebuild`）。公司机补了 SSH Host `g-snipers-server`，私钥用本机 `~/.ssh/g_snipers_deploy` |
| 2026-08-20 | 产品 | 增加管理员账号（`ADMIN_EMAIL` / `ADMIN_PASSWORD`）；登录页不再预填演示密码；生产可关 `DEMO_LOGIN_ENABLED` |
| 2026-08-20 | 产品/运维 | 北京出不去 Google PageSpeed。测速改 17CE 海外 HTTP（`CE17_USER` / `CE17_API_PWD` 只在服务器 `.env`）。工作台不再让人填。排名仍 Bright Data。 |
| 2026-08-20 | 代码 | GSC 服务端调用改走 Cloudflare Worker 中转。浏览器授权仍直连 Google。不配 Google Ads。 |
| 2026-08-20 | 代码 | 中转配上后，测速改走 Google PageSpeed（经 Worker）。未配中转时仍用 17CE。PageSpeed 可能超过 Nginx 默认 60s，发版时要把 `/api/` `proxy_read_timeout` 调到 180s。 |
| 2026-08-21 | 运维 | `relay.weiyids.com` 橙云已通。生产 `.env` 的 `GOOGLE_RELAY_URL` 改为该地址（密钥未动）。`sync-from-local.ps1 -Rebuild` 发到 `6dad00d`。线上 Nginx `/api/` 超时已 180s。 |
| 2026-08-21 | 运维 | 排名改走 Bright Data SERP API 区 `serp_api1`（`/request`）。不要用浏览器区 `scraping_browser1` 或 Dataset scrape。密钥未动。发到 `bacb349`，`excavator` 实测有自然结果。 |
| 2026-08-21 | 产品 | 测速、GSC、SERP 区均已生产实测。Bing Webmaster / IndexNow 暂不配，可等。 |
| 2026-08-21 | 产品/运维 | 老板进门体验发到 `9b3ef2c`（`sync-from-local.ps1 -Rebuild`）。登录落到客户说明；清单用人话标题；门锁租户「收录未测」启动时标「本轮不改」。GEO 16 条尚未联网抽查。 |
| 2026-08-21 | 产品/运维 | GEO 与分发发到 `4cf902c`（`sync-from-local.ps1 -Rebuild`）。客户说明按最近一次抽查看「有没有被提到」；分发默认渠道卡片；LinkedIn/X/Facebook 等官方接口只给客户跳转或自己发，不代登、不群发。 |
| 2026-08-21 | 产品/运维 | 诊断目标发到 `b0c4b70`（`sync-from-local.ps1 -Rebuild`）。不再填 `美国 \| 北美 \| US \| en-US`；点选美英德日阿联酋澳。日文搜索词跟日本，英文跟美英德澳。 |
| 2026-08-21 | 运维 | 收掉 Postgres 宿主机 5432 映射，发到 `29cd68a`。库只在 compose 网络给 backend 用。宿主机已无 5432；租户/账号数据仍在。 |
| 2026-08-21 | 产品/运维 | 点选国家与登录加固发到 `f57e6b5`（`sync-from-local.ps1 -Rebuild`）。GEO/SEO/市场不再填 `en-US`；总览列表对齐 OPENISH；登录 5 次失败锁 15 分钟；分发 providers 需登录；开户用 `python -m app.provision_tenant`，无公开注册。 |
| 2026-08-21 | 产品/运维 | GEO 闭环发到 `fa68996`，线上对齐 `7327aef`（`sync-from-local.ps1 -Rebuild`）。待处理项写明补哪页/发哪张卡；完成标准是页已上线、帖已发出、同一问再测；复测只记有没有变化，不要求这次必须提到。同一问再测不用展开 Set，否则 Next 构建失败。 |
| 2026-08-21 | 代码 | 客户库可导出：管理员 `/ops/backup`、落点 `BACKUP_HOST_DIR`、可选异地 dir/SCP、`deploy/backup-postgres.sh`。定时默认关，未装 cron。 |
| 2026-08-21 | 产品 | 外部接口按客户按天限次。管理员 `/ops/usage` 设每天上限，看已用/还剩。默认：排名 15、博查 24、百炼 24、大模型 60、测速 8。GEO/SERP/测速用完返回 429。 |
| 2026-08-21 | 产品 | 客户说明、站内诊断、GEO 抽查可下 PDF（Markdown → HTML → WeasyPrint）。发版必须 `-Rebuild`。 |
| 2026-08-21 | 产品/运维 | 家里发到 `3a287c2`（`sync-from-local.ps1 -Rebuild`）。接口按天限次、客户 PDF、库副本页（定时关）。health 200；providers 未登录 401。 |
| 2026-08-22 | 运维 | UptimeRobot 提交盯 `/api/health`，等 `caocan326@gmail.com` 点确认。库 dump 已拉到家里盘（与服务器 SHA256 一致）。已装 `/etc/cron.d/g-snipers-backup`。未配第二台 scp。 |
| 2026-08-22 | 运维 | UptimeRobot 邮箱已确认，监控已在跑。交接写入 `HANDOVER.md` §4.1 / §4.2。 |
| 2026-08-22 | 产品 | 换站保存不再静默失败：页内确认归档，写入新官网后自动抓取，灰字区分已保存/未保存。 |
| 2026-08-22 | 产品/运维 | 家里发到 `57dd516`（`sync-from-local.ps1 -Rebuild`）。换站保存、交接 §4.1 / §4.2。 |
| 2026-08-22 | 产品 | 百炼仍可单测，不进默认「都测」。去掉 `search_strategy=agent`。交接 §4.3。 |
| 2026-08-22 | 产品/运维 | 家里发到 `d51b54b`（`sync-from-local.ps1 -Rebuild`）。百炼默认不进都测。 |
| 2026-08-22 | 修复 | seed 重复插入 `cite_checklist` 会让 backend 起不来。缺问句再 seed 时跳过已有资产。 |
| 2026-08-22 | 产品/运维 | 家里发到 `9d2781c`（`sync-from-local.ps1 -Rebuild`）。百炼默认不进都测；seed 修复 502。 |
| 2026-08-22 | 产品/运维 | 家里发到 `038c770`（`sync-from-local.ps1 -Rebuild`）。绿联实走：客户名跟官网、登录进首页、用量成功后再记账；写出改法有进度。`ddd1f34` 曾因删门锁问句碰到 `geo_sample_results` 外键 502，随即修好。 |
| 2026-08-22 | 产品/运维 | 家里发到 `8a6e0d8`（`sync-from-local.ps1 -Rebuild`）。PDF 渲染失败改 503；GEO 下 PDF/CSV 失败写在页面上。 |
| 2026-08-22 | 产品/运维 | 公司发到 `46ac4e7`（`sync-from-local.ps1 -Rebuild`）。同一买家问题在 GEO / 清单 / 客户说明写全；标题按这一轮抽查改；博查+Tavily 算一轮并分源写提到/未提到。 |
| 2026-08-22 | 产品/运维 | 公司发到 `a6eebaf`（`sync-from-local.ps1 -Rebuild`）。清单写这一轮 `1 / 2`；源名用 Tavily / 博查，不用引擎键。 |
| 2026-08-22 | 产品/运维 | 公司发到 `0efc59a`（`sync-from-local.ps1 -Rebuild`）。GEO 待处理项写出页和官网链接；进度分已写/已发/已上线，未上线不能验收。 |
| 2026-08-22 | 产品/运维 | 公司发到 `5e10164`（`sync-from-local.ps1 -Rebuild`）。客户说明「这周改三处」至少留一格给 GEO 改法；改回已写改法时清单角标回到待处理。 |
| 2026-08-22 | 产品/运维 | 公司发到 `6fb37e2`（`sync-from-local.ps1 -Rebuild`）。打开清单 / GEO / 客户说明按进度对齐角标；清单 `verify` 从「待核对」改成「待复查」。 |
| 2026-08-22 | 产品/运维 | 公司发到 `cb78ec8`（`sync-from-local.ps1 -Rebuild`）。客户说明增加可复制短稿；GEO 待处理项可复制单条。短稿不写工作台内部用语。 |
| 2026-08-23 | 产品/运维 | 家里发到 `e93dbf6`（`sync-from-local.ps1 -Rebuild`）。连不上与后端 500 拆开；控制台挂了留横幅不踢登录；GEO 购物页不算官网。 |
| 2026-08-23 | 产品/运维 | 家里发到 `e1d2435`（`sync-from-local.ps1 -Rebuild`）。GEO「没给出官网」只跟海外源；复测不跟博查店链。 |
| 2026-08-23 | 产品/运维 | 家里发到 `363b37b`（`sync-from-local.ps1 -Rebuild`）。GEO 官网核验收口：只能对着客户官网链接勾通过。 |
| 2026-08-23 | 产品/运维 | 家里发到 `d905cbf`（`sync-from-local.ps1 -Rebuild`）。没给出官网短稿写实；无客户官网链接时说明为何没有核对按钮。 |
| 2026-08-24 | 产品/运维 | 公司发到 `6e09125`（`sync-from-local.ps1 -Rebuild`）。GEO 待处理卡接站外一篇英文稿、官方发帖页和帖子链接回填。不代发。记下帖子不会自动上线。 |
| 2026-08-24 | 产品/运维 | 公司发到 `9006ec6`（`sync-from-local.ps1 -Rebuild`）。发给客户的短稿带上「自己发这一条」和两行英文。黄框不重复。不代发。站外仍不进清单。 |
| 2026-08-24 | 产品/运维 | 公司发到 `b98325b`（`sync-from-local.ps1 -Rebuild`）。从历史网站恢复时按域名写回客户名。工单仍按站整包切换。 |
| 2026-08-24 | 产品/运维 | 公司发到 `d7f02bf`（`sync-from-local.ps1 -Rebuild`）。站外卡片改为「打开官方发帖页」，不再写「接口可发」。不代发。 |
| 2026-08-24 | 产品/运维 | 公司发到 `f5bdd92`（`sync-from-local.ps1 -Rebuild`）。执行记录回填帖链接写成「已回填」，渠道显示平台名，不写 directory。登记≠代发。 |
| 2026-08-24 | 产品/运维 | 公司发到 `e00f8d6`（`sync-from-local.ps1 -Rebuild`）。旧 451 核验行也带出「登记≠我们代发」。不改库、不重核验。 |
| 2026-08-24 | 产品/运维 | 公司发到 `1e91706`（`sync-from-local.ps1 -Rebuild`）。站外可复制给客户、可看接口报文、可记自备接口。不代发、不存钥匙。 |
| 2026-08-24 | 产品/运维 | 公司发到 `011c912`（`sync-from-local.ps1 -Rebuild`）。站外可核对公开主页：打不打得开、有没有官网链。不注册、不代登。 |
| 2026-08-27 | 产品/运维 | 公司发到 `bbcbed9`（`sync-from-local.ps1 -Rebuild`）。GEO 短稿带 Fact Pack 英文 FAQ；没有可核渠道不写 LinkedIn；待处理可登记上线、同一问再测、复测后关掉。不代改、不代发。 |
| 2026-08-27 | 产品/运维 | 公司发到 `b2c9bc1`（`sync-from-local.ps1 -Rebuild`）。总览第一步补 Fact Pack；打开工作台清门锁演示询盘。不编规格、不代改。 |
| 2026-08-27 | 产品/运维 | 公司发到 `526ed99`（`sync-from-local.ps1 -Rebuild`）。总览只看这周项。生产走查七条都过。不编问句、不代改。 |
| 2026-08-27 | 产品/运维 | 公司发到 `c84d173`（`sync-from-local.ps1 -Rebuild`）。客户资料收成 Fact Pack 草稿，批准前不出对外稿。不编规格、不打开官网。 |
| 2026-08-27 | 产品/运维 | 公司 Rebuild：从资料收草稿时先认门锁再认太短。 |

---

## 9. 明确不要做的事

- 不要把 `C0.pem`、`g_snipers_deploy`、线上 `.env` 提交进 git。
- 不要把 `/opt/g-snipers-global` 当成发版目录。
- 不要在没读这份档案时再「重新部署一套」。
- 不要把 Postgres 的 5432 再映射到宿主机或公网。库只给 compose 网络里的 backend 用。
- 不要配置 Google Ads。
- 不要假设 `weiyids.com`（无 www）已经能开。
