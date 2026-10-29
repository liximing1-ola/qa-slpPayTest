# qa-slpPayTest 云服务器部署指南

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码仓库地址 | `<仓库地址>` |
| 服务器部署路径 | `/home/<user>/qa-slpPayTest` |
| Python 版本要求 | 3.9+（当前服务器 3.11） |
| 测试应用 | SLP / XSG |

> 本文所有地址、路径、账号均为占位符（`<api-host>` / `<db-host>` / `<user>` 等），
> 真实环境信息只配在 `common/env_local.py`（已在 .gitignore 里）或环境变量里，
> 不写进文档、也不硬编码进代码。

---

## 快速开始（4 步完成部署）

### 第 1 步：登录服务器，拉取代码

```bash
cd /home/<user>
git clone <仓库地址>
cd qa-slpPayTest
```

### 第 2 步：安装依赖

```bash
pip3 install -r requirements.txt
mkdir -p log
```

### 第 3 步：配置环境信息（不做这步连不上任何服务）

数据库地址、账号、接口域名、执行机标识都**不在仓库里**，两条途径任选一条：

```bash
# 方式 A：本机配置文件（建一次，手工执行也能用）
cp common/env_local.example.py common/env_local.py
vi common/env_local.py     # 填 DB_* / REDIS_HOST / APP_HOST / NODE_*

# 方式 B：环境变量（crontab 走 . ~/.slp_env 时最省事，见下方定时任务一节）
export DB_HOST=<db-host> DB_USER=<user> DB_PASS=<pass> \
       REDIS_HOST=<redis-host> APP_HOST=https://<api-host> \
       NODE_ALI_SLP=$(hostname)
```

验证是否配齐：

```bash
python3 -m common.preflight slp
```

四项全 `OK` 才能开跑。缺项会直接点名，不会拿 `127.0.0.1` 去连、再吐一屏超时：

```
[环境] FAIL  配置    缺少 DB_PASS；复制 common/env_local.example.py 为 common/env_local.py 后填值，或直接设同名环境变量
```

> `NODE_ALI_SLP` 填 `$(hostname)` 即可：它只用来判断「执行机是否与被测服务同机房」，
> 同机房则状态码断言前免等待。不配也能跑，只是每轮白等约 50 秒。

### 第 4 步：执行测试

```bash
# 执行 SLP 测试
python3 run_all_case.py slp

# 执行 XSG 测试
python3 run_all_case.py xsg
```

---

## 服务器环境准备（首次部署需执行）

```bash
# CentOS / RHEL
yum install -y python3 python3-pip git gcc python3-devel

# Ubuntu / Debian
apt update && apt install -y python3 python3-pip git gcc python3-dev
```

验证：
```bash
python3 --version   # 需要 3.9+
pip3 --version
git --version
```

---

## 后续更新代码

```bash
cd /home/<user>/qa-slpPayTest
git pull                 # 拉当前分支（lxm）的上游，不用写分支名
pip3 install -r requirements.txt    # 依赖有变更时执行
```

---

## 环境被清理或重置后的恢复

### 1. 先确认是环境坏了，不是代码坏了

```bash
python -m common.preflight slp
```

只要看到 `FAIL 数据 …`，就是种子数据没了（账号/房间/礼物/工会被删），**不是服务端引入的 bug**，
不要去查代码。退出码 3 同样表示「本轮没跑」，与用例失败（1）区分。

### 2. 有快照：直接恢复

```bash
python backup_seed.py list                                    # 看有哪些快照
python backup_seed.py restore ~/.slp_backup/seed-<最新>.sql --yes
python -m common.preflight slp                                # 再验一遍，必须全部 OK
```

恢复覆盖的是 `xianshi` 与 `config` 两个库的种子表，不会动流水和余额。

### 3. 没快照：只能找后端/运维重建

账号要过注册与实名，房间要绑 uid，工会要建关系，礼物要配价格——这些都不是本仓库能造的，
**造数工具只负责把已有账号的余额/背包/等级改到想要的状态，不负责凭空创建账号**。

找他们时把这些信息一次给全（都在 `caseSlp/config.py` 里）：

- 账号：`payUid`、`payUid_subsidiary`、`payUid_subsidiary2`、`gs_A_ceo_uid`、`gs_B_ceo_uid`、
  `gs_A_uid`、`gs_B_uid`、`business_room_uid`、`normal_uid`（手机号尾号 15008520xxx）
- 房间：`gs_A_rid_1`、`gs_A_ceo_rid`、`business_room_rid`（需绑定到对应 uid）
- 工会：`gs_A_bid`、`gs_B_bid` 及成员关系
- 礼物：`xs_gift` 的 69 号（椰子水，100 钻）及它对应的商品 `xs_commodity.cid=329`

修好后先 `python -m common.preflight slp` 确认种子齐全，再跑一轮全量。

### 4. 恢复后怎么快速确认环境真的好了

```bash
python3 run_all_case.py slp          # 全量，预期 0 未通过（十几条既定 skip 不算）
python3 run_stress_case.py slp       # 并发 5 条，确认余额与订单没被残数据带歪
```

两个入口都会先把体检结论打在最前面，体检不过就不执行用例、退出码 3——所以「跑完但没有环境行」
本身就是个 bug，值得查。

### 5. 防止下次再被清：定期导快照

```bash
# 建议每周一次，可加进 crontab（与日常回归错开时间）
30 3 * * 1 cd /home/<user>/qa-slpPayTest && python3 backup_seed.py dump --keep 4
```

快照存在 `~/.slp_backup`（仓库外，权限 600），默认保留最近 4 份。
**只有环境好的时候导出来的快照才有用**，别等到坏了才想起来导。

---

## 网络要求

服务器必须能访问以下地址：

| 地址 | 端口 | 用途 |
|------|------|------|
| `<api-host>` | 443 | API 服务器 |
| `<db-host>` | 3306 | MySQL 数据库 |
| `<db-host>` | 6379 | Redis |
| `<legacy-db-host>` | 3306 | MySQL（旧版） |
| `hooks.slack.com` | 443 | 结果通知（需外网） |
| `qyapi.weixin.qq.com` | 443 | 企业微信通知（需外网） |

---

## 需要修改的配置（如果服务器环境不同）

优先用环境变量，不改代码：

| 环境变量 | 默认值 | 用途 |
|---------|--------|------|
| `DB_HOST` / `DB_USER` / `DB_PASS` | 见 `common/Config.py` | MySQL 连接 |
| `WX_BOT_SLP` | **无默认值** | 企微机器人 webhook，必填（只能走环境变量，仓库里不留 key） |
| `ASSERT_SLEEP` | `0.3` | 断言前等待秒数，设 `0` 可提速 |
| `REQUEST_INTERVAL` | `2` | 同账号请求最小间隔（频控） |
| `PUSH_WX` | `0` | 是否推送到企业微信群；cron 命令里显式写 `PUSH_WX=1`，手工跑默认不推 |
| `LIST_PASS` | `0` | 推送时列出通过用例（需 `PUSH_WX=1`） |

```bash
export DB_HOST=<db-host>
export WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<key>'
```

| 配置文件 | 配置项 | 填什么 |
|---------|--------|--------|
| `common/Config.py` | API 地址 | `https://<api-host>/` |
| `common/conRedis.py` | Redis | `<db-host>:6379`，无密码 |

---

## 凭据

服务器上只放两样凭据，都不进仓库、不进 crontab 明文：

| 凭据 | 放哪里 | 为什么 |
|------|--------|--------|
| 企微 webhook key | `~/.slp_env`（600） | 拿到就能往群里发任意消息 |
| GitHub 访问令牌 | `~/.git-credentials`（600） | 只用于 `git pull`，给读权限就够 |

**GitHub 令牌不要写进 remote URL**。`git remote set-url origin https://<user>:<token>@github.com/...` 会把令牌存进 `.git/config`，任何人 `git remote -v` 都能看到，截图、报错日志也会原样带出来：

```bash
git remote set-url origin https://github.com/<owner>/<repo>.git
git config credential.helper store     # 下一次 pull 输一次，之后存在 ~/.git-credentials
```

**一旦泄露（截图、日志、聊天记录里出现过）就只能换新的**。令牌进了 git 历史或聊天记录就收不回来，删当前文件也没用；有效处置只有去 GitHub 撤销并重新生成。服务器只负责部署，新令牌只勾 `repo` 读权限，不要给写——一台被改坏的执行机能 push 代码，等于把发布权交了出去

---

## 注意事项

1. **测试用例范围**：`run_all_case.py` 的 `all_case()` 里 `pattern` 现为 `test_*.py`（全量），只调试单个文件时把这一行改成对应文件名
2. **查看执行结果**：执行结束会在控制台输出带编号的完整未通过清单（编号 / FAIL|ERROR|SKIP / 用例名 / des / 失败明细），
   同时写入 `log/notPassCase.log`；失败与异常的完整堆栈只写 `log/failCase.log`，不在控制台刷屏。
   云服务器上可直接：
   ```bash
   tail -n 100 log/notPassCase.log   # 未通过清单（先看这个）
   tail -n 200 log/failCase.log      # 需要看堆栈时
   ```
   企业微信推送默认关闭。需要推送时要同时给两个变量：`PUSH_WX=1`（开开关）和 `WX_BOT_SLP`（webhook 地址，无默认值）：

   ```bash
   PUSH_WX=1 WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<key>' \
       python3 run_crontab_case.py slp
   ```
3. **定时任务**：

   先确认 python3 的绝对路径——cron 的 PATH 很精简，只写 `python3` 在 cron 里经常找不到：

   ```bash
   which python3      # 例如 /usr/bin/python3
   crontab -e
   ```

   ```cron
   # 每天 10:00 拉最新代码后跑全量并推送到企微；日志按日期落盘，同时清理 30 天前的
   0 10 * * * . /home/<user>/.slp_env; cd /home/<user>/qa-slpPayTest && mkdir -p log && { find log -name 'cron_*.log' -mtime +30 -delete; git pull -q --ff-only; PUSH_WX=1 /usr/bin/python3 run_crontab_case.py slp; } >> log/cron_$(date +\%F).log 2>&1
   ```

   `~/.slp_env` 里放 webhook 和环境信息（`chmod 600`）：

   ```bash
   cat > /home/<user>/.slp_env <<'EOF'
   export WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<key>'
   export DB_HOST=<db-host> DB_USER=<user> DB_PASS=<pass>
   export REDIS_HOST=<redis-host> APP_HOST=https://<api-host>
   export NODE_ALI_SLP=$(hostname)
   EOF
   chmod 600 /home/<user>/.slp_env
   ```

   > 数据库与接口地址也放这里，cron 行开头 `. ~/.slp_env` 一引，连 `common/env_local.py`
   > 都不用建。手工执行时没有这一行，所以两者至少配一处（见第 3 步）。

   几处不是随手写的：

   - **用 `run_crontab_case.py` 不用 `run_all_case.py`**：前者专为定时任务，不逐条播报通过用例，只打汇总 + 未通过清单；137 条全量下来后者几千行，日志没法看
   - **每天先 `git pull --ff-only`**：不拉的话定时任务跑的永远是部署那天的代码，改过的用例根本不会生效。`--ff-only` 避免在服务器上产生合并提交；用 `;` 不用 `&&`，pull 失败也继续用现有代码跑，不把整条链断掉
   - **服务器工作副本停在 `lxm`**：开发提交都在 lxm 上，cron 的 `git pull` 拉的是当前分支的上游，所以先把分支切过去：

     ```bash
     git fetch origin
     git checkout -B lxm origin/lxm
     git branch --set-upstream-to=origin/lxm lxm
     git rev-parse --abbrev-ref HEAD      # 应为 lxm
     ```

     停在 master 上也能跑，但一旦某次只推了 lxm（master 忘了同步），服务器拉到的就是旧代码——这种偏差不会报错，只会安静地跑上一版
   - **日志按日期分文件**：`cron.log` 会无限增长，`$(date +\%F)` 一天一个（cron 里 `%` 必须转义成 `\%`）
   - **清理日志要放在最前面**：`{ }` 的退出码取块内最后一条命令，把 `find` 放在末尾会把 python 的退出码盖掉，cron 就永远收不到失败信号（MAILTO / 调度平台告警全失效）
   - **`find ... -mtime +30 -delete`**：只删 30 天前的，不会动当天正在写的文件
   - **`mkdir -p log` 必须在重定向之前**：`>> log/cron_x.log` 是 shell 在开始执行前打开的文件，目录不存在就直接报错，整条命令连 python 都不会起动
   - **`PUSH_WX=1` 写在 cron 行里，不写进代码默认值**：定时任务要推送，本地手工跑一轮不该往群里发测试消息；群里一个上午出现三四条「总数137，通过137」会让人很快就不看它了
   - **webhook key 放 `~/.slp_env` 而不是写进 cron 行**：crontab 是明文，能登这台机器的人 `crontab -l` 就看得见；key 拿到就能往群里发任意消息。600 权限的文件至少跟登录权限一个级别
   - **数据库口令同理**：cron 的 shell 不带登录环境，`export` 在别处的变量它看不见；写进 crontab 行又等于把库口令贴在 `crontab -l` 里。两者都是把 `.slp_env` 引进来就解决了
   - **`. 文件;` 后面用分号不用 `&&`**：文件不在时 `&&` 会短路整条命令，连用例都不跑且不报错；分号则照常跑用例，只是不推送，日志里会写「未设置 WX_BOT_SLP」。宁可少一条推送，不能少跑一轮用例
   - **时间选 10:00**：全量约 5 分钟、会造数扣费，这个点有人在场，推出来的失败当天就能跟进；凌晨跑则等于把问题压到第二天
   - **服务器上不要手工改代码**：`git pull --ff-only` 遇到本地修改会直接拒绝，日志里会一直报 pull 失败，而用例跑的还是旧代码

   需要改推送开关时，不用重新整条配置，直接把这一行里的 `PUSH_WX=1` 换成 `PUSH_WX=0` 重新执行即可（crontab 里可以直接 `crontab -l | sed 's/PUSH_WX=1/PUSH_WX=0/' | crontab -`）。

4. **看结果、追趋势**：

   ```bash
   tail -30 log/cron_$(date +%F).log                    # 当天结果
   grep -h '重试后才通过' log/cron_*.log | sort | uniq -c   # 每天一行，这就是趋势
   ```

   第二行值得每天看一眼：`重试后才通过: N 条（X%）` 统计的是「被 @Retry 兜住、但确实失败过一次」的请求。
   当前它稳定指向 naming_song 的「房间类型错误」（服务端约 8% 拒绝，证据见 README 排查手册第 4 条），
   服务端修好后这行会变成「无」。全量口径只有 0.7%（分母 137，而这个文件只跑一轮），
   想看清这个 bug 就单跑它（分子分母都是 10 条，信噪比高 14 倍）：

   ```bash
   CASE=test_naming_song python3 run_all_case.py slp 2>&1 | grep '重试后才通过'
   ```

5. **退出码**：`run_all_case.py` / `run_crontab_case.py` 执行结束后会按结果返回退出码，
   可直接被 cron 告警、调度平台或 `cmd && 下一步` 识别：

   | 退出码 | 含义 |
   |--------|------|
   | `0` | 全部用例通过 |
   | `1` | 存在失败或异常（跳过不计） |
   | `2` | 命令行参数错误（如 `run_crontab_case.py slpp`） |

   **注意：被 `@Retry` 救回来的用例不算失败，退出码仍是 0。** 只靠退出码会漏掉「稳定存在但被重试掩盖」的问题，
   必须配合上面那行重试率一起看。失败时让 cron 发邮件：在 crontab 顶部加 `MAILTO="你的邮箱"`（前提就是非 0 退出码）。

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| pip install 报错 | 先确认 `python3 --version` ≥ 3.9；`requirements.txt` 已精简为 requests / urllib3 / PyMySQL / redis 四个实际依赖 |
| 数据库连接失败 | 检查服务器与 `<db-host>` 的网络连通性 |
| Token 获取失败 | 检查 `<api-host>` 的 `/test/userToken` 接口是否可访问 |
| ModuleNotFoundError | 重新执行 `pip3 install -r requirements.txt` |
