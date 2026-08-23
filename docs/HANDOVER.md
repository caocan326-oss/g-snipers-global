# G-Snipers 海外版 · 交接文档

路径（问「交接文档在哪里」就答这个）：**`docs/HANDOVER.md`**

运维数字（IP、证书、容器）以 **`docs/PRODUCTION.md`** 为准。  
机器、仓库、发版步骤有变：先改 `PRODUCTION.md`，再改这份清单。

约定：家里和公司**不会同时改**。换机器前必须把这边 push 完。

最后更新：2026-08-23 13:29（家里。产品 `d905cbf`。没给出官网短稿写实见 §4.9。官网核验 `363b37b`。工单只跟海外源 `e1d2435`。）。

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

官网已经不是 snipers 时，容器启动 seed **不会**再灌门锁演示。它会把客户名改成跟域名走（`www.ugreen.com` → `UGREEN`），并清掉门锁问句/示例。有抽查记录时必须先删 `geo_sample_results`，否则 backend 起不来（502）。

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

改了 Dockerfile、依赖，或前后端业务代码时（镜像里 `COPY` 源码，不 Rebuild 容器仍跑旧包）：

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

## 4.3 联网抽查源（百炼）

密钥 `DASHSCOPE_API_KEY` 仍在生产 `.env`，可以「只测这一源」。

「已配置的联网源都测」默认只跑 **博查 + Tavily**。百炼能带回网址，但海外问句经常给到国内论坛/站，不当默认证据。单测时不要再加 `search_strategy=agent`（非流式会 400）。

DeepSeek 仍只做分析，不算联网引用。

启动 seed 必须可重复跑。缺问句时不能再插第二条 `cite_checklist`，否则 backend 起不来（502）。

---

## 4.4 绿联实走后的身份

生产当前官网是 `https://www.ugreen.com`。`038c770` 起：

- 登录和 `/` 进 `/home`，不再进分发。
- 换站或 seed 会把演示门锁客户名改成跟域名走。
- 用量：博查/改法等外部调用**成功后再记账并立刻提交**，超时不会把已用滚回 0。顶栏写「今天已用：0/24」。
- 写出改法按钮旁有「已写 / 还剩」。
- GEO 来源卡不再印 `BOCHA_API_KEY` 这类键名。
- PDF 渲染失败返回 503 和原因，不再是无说明的 500。GEO 下 PDF / 检查记录失败会写在页面上。

IndexNow / GSC 同步灰着是没配钥匙和授权，不要当故障改。

---

## 4.5 同一问三处对齐

绿联实走后断在文案，不在按钮。同一条问：

`Which brand makes the best 100W USB-C charger for laptops?`

GEO 写全了；清单和客户说明曾截成「Which brand makes the best…」，标题停在「没提到我们」，摘要/复测已经写成「提到了」。Tavily 提到、博查未提到时，汇总曾写成「1 / 1 抽查里被提到」。卡片「被提到 尚未检查」看的是 8 个引擎空位，不是这一轮联网记录。

`46ac4e7` 起：

- 清单、客户说明、执行清单写完整问句，不再 28 字截断。
- 打开这三处时，未关闭项的标题按**这一轮**抽查改。有的源提到、都没官网 → 「提到了品牌，但没给出官网」。
- 同一点击里的博查 + Tavily 算一轮：`1 / 2`，并写明谁提到、谁没有。
- 卡片「被提到」按联网记录算。没手工打开的引擎空位仍是尚未检查。
- 外来网址仍不能算官网。工作台「人工上线」仍不是客户官网已经改完。

`a6eebaf` 起清单也写这一轮 `1 / 2` 和源名。源名用 **Tavily** / **博查**，不用小写 `tavily` / `bocha`。标题原文是「提到了品牌，但没给出官网」，不是五个字的缩写。官网来源已核对仍是尚未检查，直到有人打开网址。

博查常给中文电商、没有 ugreen.com，是源质量，不要当成按钮坏了。

---

## 4.6 客户能改的一页

`0efc59a` 起：待处理项写出改哪一页、官网地址、买家原问、站外发哪张卡。进度分三档：已写改法 / 已发给客户 / 客户已上线。第三档才允许验收和再测。「客户已上线」是客户经理登记，不是官网已改的证明。英文问里博查加一句：按中文网页看，不写成海外 AI 结论。

绿联实走（admin 进 ugreen.com 工作台）：100W 问已指到 `/products/usa-65585`，不是首页。客户说明「这周改三处」曾被两条 agents.md 和 500W schema 占满。`5e10164` 起至少留一格给这条 GEO 改法；改回「已写改法」时角标回到待处理。

`6fb37e2` 起：打开清单 / GEO / 客户说明就会按进度改角标，不必再点一遍按钮。进度「已写改法」而库里还留着上次 `verify` 时，刚进页也会回到待处理。清单和 GEO 同一状态用同一套词：待处理 / 进行中 / 待复查。不要把清单的「待核对」再当成这条工单的角标。

`cb78ec8` 起：客户说明有「发给客户的短稿」和「复制给客户」。GEO 待处理项也能复制单条。短稿只写客户要改的页、链接和站外卡，不写「工作台打勾」。PDF 和工作台三处仍留给客户经理看。

`01d8b3b` 起：第三档必须先填客户页或帖的 http(s) 地址。GEO、处理清单、客户说明会显示这条链接。没有地址不能记「客户已上线」，也不能验收。登记地址仍不是我们打开核对过的证明。换到真实官网时，seed 会清掉 `old-blog.example`、`smarthome-weekly.example` 和门锁竞品（August Home / Level Lock / Qrio / Nuki）等演示站外示例，并去掉挂在这些缺口上的跟进。`.gitignore` 忽略 `backend/localtest.db`，本机 SQLite 顶替库不要提交。

---

## 4.7 人工复测后的修补

绿联实走后，老板单独走「老外能不能搜到 100W USB-C charger」会断在：生成买家问题 0 条、博查/Tavily 约 40 秒后 0 条且用量仍 0、排名绿钮空词空等、总览数字对不上、长操作无等待、客户说明漏 `GEO-ENT-002` / `schema`。

`432fd6a` 起：

- GEO 博查 / Tavily / 百炼和改法记账改为显式传租户，缺租户不调厂商。成功才记账。
- 买家问题 0 条用红字，提示先在总览保存关键词。空抽查也写清没有可检查的问题。
- 换站占位符跟当前站（绿联 `100W USB-C charger`）。空词排名先检查有没有词，绿钮只表示源已配置。
- 「生成处理建议 / 生成改法」和「载入常用渠道」有进行中文案；成功提示在页顶。
- 总览三块数字口径不同：左边只算网站紧急/优先，右边是三处未关闭加总。不强行合成一个数。
- 新检查不再写入内部编号。客户说明和工作台把旧 `GEO-ENT-*` / `schema` 转成白话。空登录提示中文。

Tavily 国家过滤和空结果说明公司已先发（`cb78ec8` 一带），这次没改。IndexNow / GSC 灰着仍是没配钥匙。博查给中文电商仍是源质量。数字三套口径加了说明，不合成一个数。

---

## 4.8 意外失败用中文兜底

有人用本机 SQLite 顶替 Postgres 全站点过一遍。SQLite `database is locked`、进程崩，是顶替方案的代价，生产 Postgres 没有这个单写锁，不当产品缺陷。

真问题是：换站自动抓取失败、登录页在后端出问题时，界面原样显示英文 `Internal Server Error`。`api.ts` 把 `detail` / `statusText` 塞进页面，home / 登录都是 `setError(e.message)`。测速/排名有 `explainServiceError`，换站和登录没有。生产上任意一次 500 都会在这两个核心动作上甩技术黑话。

`526c158` 起：

- 后端未捕获异常记日志，接口只回「这次没办成，请再试一次。系统没有悄悄做完。」
- 前端 `api()` / 下载对 5xx、`Internal Server Error`、`database is locked`、连不上也收成这句。
- 已经写好的中文 4xx（空登录、缺关键词、上线缺地址）仍原样显示。

`e93dbf6` 补完尾巴：

- 完全连不上（没有 HTTP 状态）用「现在连不上服务，不是你的网络问题，请稍后再试。」后端 500 仍是「这次没办成…」。已经译过的中文不再包一层。
- 换站自动抓取失败只留「已保存。自动抓取没跑成…」，不再同时甩原始错误。
- `/api/auth/me` 未登录 / 登录已失效 / 用户不存在才去登录。服务挂了或连不上时页顶横幅「服务暂时不可用，请刷新页面重试。」，不清 token。

本地 SQLite 顶替不要当生产复现环境。人测里占位符、买家问题 0 条说明、绿钮空等、用量，以 `432fd6a` 和 www.weiyids.com 上的再走为准。

---

## 4.9 购物页不算官网；工单跟海外源

博查常给京东 / 天猫 / Amazon 等店链。以前只分「客户域名 / 其它」，店链进外来网址，页面上看不出为什么这次本来就不会给出官网。

`e93dbf6` 起：每条链接按规则分成官网、购物页、其它。购物页永不算「给出官网」。客户如果把店登记成官网，仍认官网。旧抽查不用重跑，读出来时按同一套规则拆。批次卡拆成：疑似官网 / 购物页（不算官网） / 其它外来网址。

`e1d2435` 起工单和复测吃进这套判断：

- 「提到了品牌，但没给出官网」只在 **海外联网源**（当前排除博查）提到、且没有客户官网时开。只有博查提到、全是店链 → 不开这张单。
- 待处理项理由写清分源（如 Tavily 提到 / 博查 未提到），不再写「回答里出现了外来网址」让人去对付店链。
- 复测只比海外源有没有提到、有没有客户官网。博查店链条数变多，不写成「这次提到了」。

`363b37b` 起「给出了官网」要人对着 **客户官网链接** 打开核对：

- 批次卡上疑似官网可点「打开过，核对通过」或「打不开 / 不是客户页」。只能选 owned URL；购物页勾会失败。
- 页头写明：默认抽查是 Tavily / 博查，不是 ChatGPT 本人。
- 客户说明：未核对应写「还要人工打开核对，不能写成已经确认」；有已核对比例才写出比例。

人工验收（生产绿联）：英文 100W 问跑一轮 → **只有本轮链接里出现 ugreen.com 时**才能测「核对通过」；没有客户官网链接时按钮不出现算正确，不要当成坏了 → 有购物页时京东勾应失败 → 客户说明未核对应诚实 → 待处理项只跟海外源 → 上线 URL 后再测只记变化。登记的上线地址 ≠ 抽查给出了官网。

`d905cbf` 起：没给出官网的短稿写清「搜索提到了品牌但没给官网链接 → 页上补英文事实和可点官网链 → 改完同一问再测，不保证这次给出官网」。批次卡在提到了但没有客户官网时，写明没有核对按钮是正常的。

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
| 日期 | 2026-08-23 13:29 |
| 最后一台 | 家里 `D:\workspace\G-snipers海外版` |
| 分支 | `main` |
| 提交 | 产品 `d905cbf`（没给出官网短稿写实；无官网链接时说明为何没有核对按钮，见 §4.9）。核验 `363b37b`。工单只跟海外源 `e1d2435`。上线地址 `01d8b3b`。运维：§4.1 / §4.2。 |
| 已 push origin / upstream | 是。 |
| 已发版生产 | **是。** `d905cbf` 已 `sync-from-local.ps1 -Rebuild`。`DEMO_LOGIN_ENABLED` 仍关。Postgres 仍不映射 5432。 |
| 接口实测 | `test_customer_note_is_short_and_skips_workbench_jargon` 通过。 |
| 未完成 | 绿联产品页仍须**客户改站**：英文事实 + 可点官网链，再同一问再测。IndexNow / GSC 仍要配钥匙。不要公开注册。不要自动群发。 |
| 下一台先做 | 公司 `git pull origin main`。人测短稿与批次卡说明。下一刀人侧：按短稿改 `/products/usa-65585` 后再测。不要两边同时改。 |

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
