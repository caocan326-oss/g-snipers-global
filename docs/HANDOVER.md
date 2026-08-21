# G-Snipers 海外版 · 交接文档

路径（问「交接文档在哪里」就答这个）：**`docs/HANDOVER.md`**

运维数字（IP、证书、容器）以 **`docs/PRODUCTION.md`** 为准。  
机器、仓库、发版步骤有变：先改 `PRODUCTION.md`，再改这份清单。

约定：家里和公司**不会同时改**。换机器前必须把这边 push 完。

最后更新：2026-08-22 03:00（家里。换站保存已修，准备发版。异地副本见 §4.1。UptimeRobot 已确认。）。

---

## 0. 两台电脑

| 地方 | 本机副本 | 怎么用 |
| --- | --- | --- |
| 公司 | `E:\G-snipers海外版` | 默认就在这里打开 |
| 家里 | `D:\workspace\G-snipers海外版` | 回家在这里打开 |

盘符不同没有关系。Git 只认提交和远端，不认盘符。  
发版脚本也不绑盘符：在**当前仓库根目录**执行即可。

两台电脑都是独立 clone，通过 GitHub `origin` 会合。不要拷目录、不要 U 盘同步、不要互相覆盖。

---

## 1. 第一次在某台电脑下落仓库

只在该目录还不存在、或目录是空的时候做。

1. 打开终端，进入要放仓库的盘（公司 `E:\`，家里先确保有 `D:\workspace`）。
2. 克隆权威源（不要克隆镜像仓当主仓）：

```powershell
git clone https://github.com/caocan326-oss/g-snipers-global.git "E:\G-snipers海外版"
```

家里把路径改成 `D:\workspace\G-snipers海外版`。

3. 进入仓库，加上镜像远端：

```powershell
cd <本机仓库根目录>
git remote add upstream https://github.com/caocan326-oss/g-snipers-overseas.git
git remote -v
```

必须看到：

```
origin     https://github.com/caocan326-oss/g-snipers-global.git
upstream   https://github.com/caocan326-oss/g-snipers-overseas.git
```

4. 确认分支：

```powershell
git checkout main
git pull origin main
git status -sb
```

应是 `## main...origin/main`。

5. 本机 SSH（发版、登服务器才需要）。把 `deploy/ssh-config.example` 里的 `Host g-snipers-server` 拷进本机 `~/.ssh/config`。私钥用本机 `~/.ssh/g_snipers_deploy`，**不要提交私钥**。测一下：

```powershell
ssh g-snipers-server
```

6. 本机跑 Docker 时：`cp .env.example .env`，按需改本地值。`.env` 不进 git。

---

## 2. 每次开工（换机器后、当天开始写之前）

按顺序做，不要跳。

1. 打开**这一台**的仓库目录。
2. 读这份文件：`docs/HANDOVER.md`。
3. 读运维档案：`docs/PRODUCTION.md`（尤其是第 7、9 节）。
4. 看下面「当前状态」一节，确认上一台已经 push。
5. 对齐权威源：

```powershell
cd <本机仓库根目录>
git checkout main
git pull origin main
git status -sb
git log -1 --oneline
```

6. `git status` 必须干净（没有未提交改动）。若有上一台没推上来的本地文件，先停下来查，不要当成新需求继续改。
7. 不要 `git pull upstream`，除非你在修镜像。

做完这 7 步才能改代码。

---

## 3. 日常改代码

1. 只在 `main` 上改（当前没有用功能分支的约定）。
2. 本地验证（需要跑起来时）：

```powershell
docker compose up --build
```

演示登录（只用于演示租户）：`am@demo.gsnipers.com` / `demo1234`。

上第二个客户不要手插库。在仓库 `backend` 目录：

```powershell
python -m app.provision_tenant --name "客户名" --email am@customer.com --password "至少8位" --site https://www.customer.com
```

不要做公开注册页。

3. 改完在本机看 `git status`、`git diff`，确认没有把 `.env`、私钥、密钥加进去。
4. 用户明确要求提交时才 commit。不要主动 commit。
5. 提交后立刻推两个远端（镜像必须跟着权威源）：

```powershell
git push origin main
git push upstream main
```

6. 不要在 `upstream` 上单独 commit。不要 `git push` 到别的远程名。

---

## 4. 发版到生产

生产站点：https://www.weiyids.com  
生产目录：`/opt/g-snipers-overseas`  
SSH：`ssh g-snipers-server`（`root@39.97.52.149`）

**不要在服务器上 `git pull`。** 华北2 轻量访问 GitHub HTTPS 会卡住。  
**不要把 `/opt/g-snipers-global` 当发版目录。**

按顺序：

1. 本机确认在 `main`，工作区干净，且已经：

```powershell
git push origin main
git push upstream main
```

两个远端应是同一提交。

2. 在本机仓库根目录执行：

```powershell
powershell -File deploy/sync-from-local.ps1
```

改了 Dockerfile 或依赖时：

```powershell
powershell -File deploy/sync-from-local.ps1 -Rebuild
```

3. 脚本会：打 `git bundle` → `scp` 到机器 → 服务器 `git fetch` 本地包 → checkout `main` → `docker compose up -d`。线上 `.env` 不在包里，不会被覆盖。
4. 浏览器打开 https://www.weiyids.com 看是否正常。
5. 需要时再 SSH 看容器：

```powershell
ssh g-snipers-server
cd /opt/g-snipers-overseas
docker compose ps
git log -1 --oneline
```

6. Nginx / 证书不在每次发版里动。改反代：先改服务器 `/etc/nginx/sites-available/g-snipers`，`nginx -t`，再 reload；然后把内容回写 `deploy/nginx/g-snipers.live.conf`，并改 `docs/PRODUCTION.md` 日期。

可选备份（发版前，在服务器上）：

```bash
tar -C /opt -czf /opt/g-snipers-backups/pre-$(date +%Y%m%d%H%M%S).tgz g-snipers-overseas --exclude=g-snipers-overseas/.git
```

这是代码 tar，同一块盘，不算客户库，也不算出机器。

---

## 4.1 客户库异地副本

诊断历史、Fact Pack、竞品记录只在生产这一台 Postgres。宿主机 5432 不映射。

| 地方 | 路径 | 说明 |
| --- | --- | --- |
| 生产本机落点 | `/opt/g-snipers-db-exports` | `BACKUP_HOST_DIR`。cron 每天 03:15 UTC 打一份 Postgres 自定义格式 |
| 生产 cron | `/etc/cron.d/g-snipers-backup` | 2026-08-22 已装。日志 `/var/log/g-snipers-backup.log` |
| 生产脚本 | `/opt/g-snipers-overseas/deploy/backup-postgres.sh` | 本机先写 dump，再按 `BACKUP_OFFSITE_*` 抄走 |
| 异地（家里） | `D:\workspace\g-snipers-db-offsite\` | **在仓库外面**，不要进 git |
| 异地（公司，拉过才有） | `E:\g-snipers-db-offsite\` | `pull-db-backup.ps1` 写在 clone 的上一级 |
| 管理员页 | `/ops/backup` | 手导出 JSON.gz 并下载。定时开关只是状态，真正跑的是 cron |

`BACKUP_OFFSITE_KIND` 仍是 `none`。没有第二台可 scp 的云。cron **不会**自动推到机器外面。出机器靠本机拉：

```powershell
powershell -File deploy/pull-db-backup.ps1
```

第一次已核对（2026-08-22，家里）：

| 项 | 值 |
| --- | --- |
| 文件 | `gsnipers-db-20260821-173000.dump` |
| 大小 | 398895 字节（约 390KB） |
| SHA256 | `e1e2e7ead5371a3287f37aa7e194795a7c49b5f0e428616f6ecb551b03c54ff1` |
| 服务器 | `/opt/g-snipers-db-exports/gsnipers-db-20260821-173000.dump` |
| 家里 | `D:\workspace\g-snipers-db-offsite\gsnipers-db-20260821-173000.dump` |

两边哈希一致，才算到了这台机器外面。公司那台如果还没有这份，在公司仓库根目录再跑一次 `pull-db-backup.ps1`。

不要把 dump、`.json.gz` 提交进 git。数字细节也可以看 `docs/PRODUCTION.md` 第 7 节硬性规则第 6 条。

---

## 4.2 探活（UptimeRobot）

不自建。托管盯 `https://www.weiyids.com/api/health`。2026-08-22 用官方 agent 接口提交，**邮箱已确认，监控已在跑**。

| 项 | 值 |
| --- | --- |
| 地址 | `https://www.weiyids.com/api/health` |
| 账号邮箱 / 告警 | `caocan326@gmail.com` |
| 周期 | 免费档约 5 分钟 |
| 微信 | 没有原生通道。手机开 Gmail 推送，或后台加 Telegram |

挂了、恢复都会发这封邮箱。后台：https://uptimerobot.com/

---

## 5. 收工 / 换到另一台电脑之前

必须做完，另一台才能开工。

1. 该提交的已经 commit。
2. 推两个远端：

```powershell
git push origin main
git push upstream main
```

3. 本机再确认干净：

```powershell
git status -sb
git log -1 --oneline
```

4. 改这份文件的「当前状态」：写下日期、哪台机器、最新提交、做了什么、下一台要做什么。
5. 把「当前状态」的改动也 commit，并再 `git push origin main` 和 `git push upstream main`。
6. 不要留下未 push 的本地改动就关机/出门。

---

## 6. 当前状态

换机器前改这里。另一台开工先看这里。

| 项 | 值 |
| --- | --- |
| 日期 | 2026-08-22 03:00 |
| 最后一台 | 家里 `D:\workspace\G-snipers海外版` |
| 分支 | `main` |
| 提交 | 换站保存：页内确认归档、真写入新官网、说「已保存，正在重新抓取」。运维：§4.1 异地副本、§4.2 UptimeRobot。 |
| 已 push origin / upstream | 本轮提交后推。 |
| 已发版生产 | 本轮 `sync-from-local.ps1`。`DEMO_LOGIN_ENABLED` 仍关。Postgres 仍不映射 5432。 |
| 接口实测 | 发完用绿联 `https://www.ugreen.com/` 再摸一遍保存。health 仍是探活目标。 |
| 未完成 | 绿联实走还没在新保存上重跑。UptimeRobot 没有原生微信。自动 scp 到第二台云还没有。Bing / IndexNow 可等。不要公开注册。不要自动群发。 |
| 下一台先做 | 公司先 `git pull origin main`。不要两边同时改。 |

`www` 灰云、A 仍 `39.97.52.149`。`relay.weiyids.com` 橙云，不要 CNAME 回 `workers.dev`。不要开 Google Ads。不要在服务器 `git pull`。

---

## 7. 明确不要做的事

- 不要两边同时改。
- 不要在没 `git pull origin main` 之前开始写。
- 不要把没 push 的改动拷到另一台。
- 不要在服务器上 `git pull`。
- 不要提交 `.env`、`.env.bak-*`、私钥、真实密钥。
- 不要把 `/opt/g-snipers-global` 当发版目录。
- 不要从本机 rsync 整目录覆盖生产。
- 不要用 `git reset --hard` 除非你明确要丢掉那边的临时改动。
- 不要把 Postgres 的 5432 再映射到宿主机。
- 不要配置 Google Ads。
- 不要假设 `weiyids.com`（无 www）已经能开。正式地址是 https://www.weiyids.com 。
- 不要把客户库 dump / `.json.gz` 提交进 git。异地副本在仓库旁边的 `g-snipers-db-offsite\`，见 §4.1。
