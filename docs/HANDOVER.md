# G-Snipers 海外版 · 交接文档

路径（问「交接文档在哪里」就答这个）：**`docs/HANDOVER.md`**

运维数字（IP、证书、容器）以 **`docs/PRODUCTION.md`** 为准。  
机器、仓库、发版步骤有变：先改 `PRODUCTION.md`，再改这份清单。

约定：家里和公司**不会同时改**。换机器前必须把这边 push 完。

最后更新：2026-08-24 14:55（公司。产品 `d619144`。官网首页记成还没有渠道档案。现网当前站 SNIPERS。）。

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

### 4.10 站内短稿与 GEO 办事卡（`c2ea32a`，收口补丁见下）

站内紧急/优先项：问题板与客户说明「这周改三处」用同一套短稿（哪一页 / URL / 请做 / 怎么验），可复制。我们不代改官网。

GEO 默认进「待处理」：一张卡只留结果、改哪页、短稿、登记上线地址、同一问再测。源下拉 /「只测这一源」/ JSON / 空引擎 8 格收到客户经理工具或不再摊开。打开非演示租户时清门锁演示引用材料。

站外仍不进交付清单。

**生产绿联人测（2026-08-24，不跑新抽查、不改官网）**

| 块 | 结果 |
| --- | --- |
| A 待处理卡 | **过**（A1–A7；A8 同一问再测未测） |
| B 运营杂讯 | **过**（源下拉藏起；空 8 格不摊开；门锁稿已清） |
| C 站内短稿 | **初测 C2 不过**，后发 `6025d78`。2026-08-24 公司复看 GEO 黄框末行已有「不代改」。 |
| D 交付口径 | **过** |

A 要点：默认「待处理（办事）」；100W 卡有问句、1/2 提到（Tavily 提到 / 博查未提到）、请改 usa-65585、短稿；按钮仅复制短稿 / 登记已上线 / 同一问再测；无 JSON；空地址登记与再测灰掉；填 usa-65585 后显示「登记≠我们打开核对过」。

### 4.11 短稿卡内必须带「不代改」（`6025d78`）

人测后约定：站内 / GEO **卡片上展示的短稿**末尾都要有「不代改」，不能只写在客户说明总收口或只出现在复制串里。

- 站内：`我们不代改官网。改完告诉我，我再打开该页核对。`
- GEO：`我们不代改官网、不代发。改完告诉我，我再用同一问看一次。不保证这次被提到。`

复测：硬刷新后看 agents.md 黄框末行、100W GEO 短稿末行是否都有「不代改」。

### 4.12 站外一篇稿接到 GEO（`6e09125`）

GEO 待处理卡增加「站外这一条」：一篇英文发帖稿（只引买家原问和官网链接）、复制、打开官方发帖页、发完回填帖子链接。我们不代发、不代登、不群发。记下帖子不会自动变成「客户已上线」。刷新后帖子链接还在。站外仍不进处理清单。

**生产绿联人测（2026-08-24 公司，不跑新抽查、不改官网、不真发）过。** 100W 卡有「站外这一条」、渠道 LinkedIn Company Page、两行英文稿、打开 `https://www.linkedin.com/company/` 后关掉。空链接不能记。记下 `https://www.linkedin.com/feed/update/test-ugreen-100w` 后刷新还在，写「登记≠我们代发」。处理清单未关闭仍 297，没有多出站外交付。角标本来就是「待复查」（这张卡早先已再测过），回填前后没变，也没变成已上线——这是对的，不要为了字面改成待处理。黄框末行有「不代改」。

### 4.13 发给客户的短稿带上站外英文稿

客户经理贴微信 / 邮件的那一条，要把「改哪一页」和「自己发这一条」合成一段。我们不代改官网、不代发 LinkedIn。

- GEO「复制短稿」和客户说明「复制给客户」都会带上：`请在「LinkedIn Company Page」自己发这一条（我们不代发）：` + 两行英文（买家原问 + 官网链接）。
- 黄框仍只写站内改法，不把「站外这一条」再抄一遍（卡上已有那一块）。
- 英文稿不编参数、不写「最好」「官方推荐」。站外仍不进处理清单。

**生产绿联人测（2026-08-24 公司，硬刷新，不抽查、不改官网、不真发）过。** 页头 UGREEN / ugreen.com。

- 客户说明过：短稿第 3 条同时有「请改这一页」`/products/usa-65585`、官网链接、「请在「LinkedIn Company Page」自己发这一条（我们不代发）：」、两行英文（原问 + Official page）、收口「不代改 / 不代发 / 不保证这次被提到」。没有「工作台打勾」，英文没编规格。点「复制给客户」toast「短稿已复制」。这台读不到剪贴板，按页面原文过，不对粘贴字。
- GEO 100W 卡过：黄框末行有「不代改」；黄框里没有整段 `Buyers are asking`（那两行只在「站外这一条」）。点「复制短稿」按钮变「已复制」。按设计复制串应合成改页 + 自己发 + 英文两行；这台读不到剪贴板，不把粘贴当缺口去改。
- 处理清单过：未关闭仍 297，没有多出一条 LinkedIn / 站外交付。

### 4.14 历史网站恢复要写回客户名（`b98325b`）

从「历史网站」恢复时，以前只写回官网和工单，页头客户名可能还停在上一个站（生产上切到 gsnipers 再恢复绿联，官网已是 ugreen.com，名字还是 GSNIPERS）。现在恢复时按域名写回客户名（ugreen.com → UGREEN）。工单仍按站整包切换，不串。

站外工作台已走过 LinkedIn：事实包、英文短稿、记下要发（缺账号受阻）、测试帖回填。处理清单仍 297。不代发。回头人测对着这三块看即可。

### 4.15 站外卡片不说「可发」（`d7f02bf`）

人测前会误会「点一下就发出去」。渠道卡和页头改成：打开官方发帖页、客户自己登号或用自己的接口。不再写「接口可发」「去官网发」。缺账号仍受阻。不代发。

**生产绿联人测（2026-08-24 12:11，硬刷新，不登号、不真发）**

- LinkedIn 卡过：按钮是 AI 写一篇 / 记下要发 / 打开官方发帖页 / 自己的接口说明。没有「去官网发」「接口可发」。打开官方发帖页指向 `https://www.linkedin.com/company/`。卡上仍有标签「可接客户自己的官方接口」（不是按钮）。
- 对外稿过：走查短稿有买家原问和 usa-65585；「LinkedIn Company Page 发布稿」多 Learn more / Keywords，没编 100W 规格。
- 执行记录**初测不过**：预期回填后仍是「缺账号受阻」，实际是「已提交」+ 核验 failed（HTTP 451），渠道写成 directory。回填后不应再说我们提交了，也不该显示 directory。451 对测试链是对的。
- 处理清单过：未关闭 297，没有多出站外交付。

### 4.16 执行记录回填不是「已提交」

回填帖链接 = 登记，不是我们往 LinkedIn 提交。角标「已提交」改成「已回填」。渠道显示平台名（LinkedIn Company Page），不写 `directory`。记下要发且没账号时仍是「缺账号受阻」。核验 451 写「登记≠我们代发」。

**生产绿联人测（2026-08-24 12:36，硬刷新执行记录，不登号、不真发）**

- 角标过：原文「已回填」，旁边「社媒发布计划」。没有「已提交」。
- 渠道过：原文「渠道：LinkedIn Company Page」。标题「在 LinkedIn Company Page 发一篇」。不是 directory。
- 核验**不过（少一句）**：有「核验：failed」和「URL 返回 HTTP 451，暂未通过存活核验。」任务行没有「登记≠我们代发」。页顶通用说明有「我们不代发、不代登」，不在这条任务上。
- 处理清单过：未关闭 297。

### 4.17 旧核验行也写出「登记≠我们代发」

发版前写下的 451 原文不会自己改。列表和任务行在回填/核验失败时补上「登记≠我们代发。」不改库、不重核验、不代发。

**生产绿联人测（2026-08-24 12:54，硬刷新执行记录，不点核验 URL，不登号、不真发）**

- 核验原话过：`URL 返回 HTTP 451，暂未通过存活核验。登记≠我们代发。`
- 处理清单过：未关闭 297。

站外三块（卡片 / 对外稿 / 执行记录）人测收工。

### 4.18 站外页能复制给客户，不代发（`1e91706`）

工作台多四件，都不发出去：

- 对外稿 / 渠道卡「复制给客户」：渠道名 + 已有英文稿 + 官方发帖页 + 我们不代发。空稿不能复制。
- 卡上不再写「可接 / 接口可发」。
- 「接口报文」只展示客户自己调的报文，`sent` 恒为 false。
- 「记下客户已自备接口」只记状态，不收、不存钥匙。多传 token 会被拒。

站外仍不进处理清单。不代发、不代登。

### 4.19 核对公开档案，不登号（`011c912`）

渠道卡可填「公开主页 URL」，点「核对档案」：公开 GET 该页，看打不打得开、页上有没有当前官网域名。发帖入口（如 LinkedIn `/company/`）不能当主页。HTTP 451 写成登录墙/地区限制，不等于没有主页，也不等于代发。不注册、不代登、不进清单。

**生产 SNIPERS 人测（2026-08-24 14:42，硬刷新站外，不登号、不真发）**

- 页头过：当前客户 SNIPERS，主域 `https://www.snipers.com.cn`。不是绿联。
- 没拿网上同名 Sniper 公司页来填。没有 SNIPERS 的 LinkedIn / Facebook 公司页可给。
- LinkedIn 卡贴官网 `https://www.snipers.com.cn/` 后点「核对档案」**不过**：红条原话「这是官方发帖入口或站点首页，不是这家客户的公开主页。先填具体公司页/档案 URL。我们不猜、不注册、不代登。」没有「官网打得开 / 该渠道还没有档案」的结论，字段没存成已核验。
- 原因：空路径被当成发帖入口。官网首页不是 LinkedIn 公司页，但也不该当 400。

### 4.20 官网首页记成「该渠道还没有档案」

发帖入口（LinkedIn `/company/` 这类）仍 400。客户自己的官网首页改为 200：记下「这是客户官网，不是该渠道公司页。官网打得开。该渠道还没有可核的公开档案。不要拿别人的同名页来填。」不把官网存成渠道 `profile_url`，不标已核验。卡上角标「该渠道无公开档案」。我们不猜、不注册、不代登、不代发。

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
| 日期 | 2026-08-24 14:55 |
| 最后一台 | 公司 `E:\G-snipers海外版` |
| 分支 | `main` |
| 提交 | 产品 `d619144`（§4.20 官网首页≠渠道档案）。现网当前站 **SNIPERS**。绿联已归档。 |
| 已 push origin / upstream | 否（推完再改是）。 |
| 已发版生产 | **否。** `d619144` 待 `sync-from-local.ps1 -Rebuild`。`DEMO_LOGIN_ENABLED` 仍关。 |
| 接口实测 | `test_distribution` + `test_onsite` 33 通过。 |
| 未完成 | 真发须客户自己的号。SNIPERS 没有可填的 LinkedIn / Facebook 公司页。要绿联时从历史网站恢复。 |
| 下一台先做 | 家里先 `git pull origin main`。硬刷新站外：LinkedIn 卡再贴 `https://www.snipers.com.cn/`，应记下「官网，不是该公司页，该渠道还没有档案」，不要再出「发帖入口」红条。不要两边同时改。家里 `localtest.db` 不要提交。 |

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
