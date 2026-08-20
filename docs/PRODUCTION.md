# G-Snipers 海外版 · 生产档案

最后更新：2026-08-20。  
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
| `/opt/g-snipers-backups` | 备份目录 |
| `/opt/g-snipers-overseas-backup-*.tgz` | 历史代码包（8 月中旬密集备份，可日后清理） |
| `/opt/g-snipers-global` | 空壳，不要当发版目标 |
| `/root/strapi-news.tar.gz` | 与本项目无关 |

Docker Compose 项目名：`g-snipers-overseas`  
配置文件：`/opt/g-snipers-overseas/docker-compose.yml`

| 容器 | 端口 | 说明 |
| --- | --- | --- |
| `g-snipers-overseas-frontend-1` | 3000 | Next.js |
| `g-snipers-overseas-backend-1` | 8000 | FastAPI（启动时 alembic + seed） |
| `…-postgres-1` | 5432 | Postgres 16。**5432 对公网暴露**，只靠弱口令，后续应收掉端口映射 |

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

北京访问不了 Google。GSC 换 token / 同步、以及 Google PageSpeed，必须走 Cloudflare Worker（`deploy/google-relay-worker/`）。`GOOGLE_RELAY_KEY` 只写服务器 `.env` 和 Cloudflare Secret。中转配上后测速不再走 17CE。

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
5. 发版前可打一份备份：`tar -C /opt -czf /opt/g-snipers-backups/pre-$(date +%Y%m%d%H%M%S).tgz g-snipers-overseas --exclude=g-snipers-overseas/.git`

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

---

## 9. 明确不要做的事

- 不要把 `C0.pem`、`g_snipers_deploy`、线上 `.env` 提交进 git。
- 不要把 `/opt/g-snipers-global` 当成发版目录。
- 不要在没读这份档案时再「重新部署一套」。
- 不要配置 Google Ads。
- 不要假设 `weiyids.com`（无 www）已经能开。
