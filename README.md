# qa-slpPayTest

SLP / XSG 打赏与支付链路的接口自动化用例。

- **框架**：Python 3.9+、unittest（`discover` 自动收集，不用维护用例清单）
- **依赖**：`requests` / `urllib3` / `PyMySQL` / `redis`，见 `requirements.txt`
- **覆盖**：私聊打赏、房间打赏、跨公会与跨档分成、点唱房（点歌/冠歌）、礼物优惠券、房间守护、人气加速卡、甄选礼盒、账户与房间数据校验
- **部署到云服务器**：见 [DEPLOY.md](DEPLOY.md)

当前基线（SLP 全量 137 条）：**执行 125 / 跳过 12**。跳过的是「依赖前序造数」和「功能已下线」的用例，不是缺陷；通过/失败数请以每轮报告为准（`log/notPassCase.log`、`log/failCase.log`）。

这 12 条是**刻意保留**的，不是懒得清：守护关系、星舰群这些是功能下线而非废弃，后续有恢复可能，恢复后去掉 `@unittest.skip` 就能复用（造数与断言都还在）。代价是「跳过 12」会长期出现在每轮报告里——因此判定标准是：**只要还可能恢复就留，确认永久下线的才删**。删不是禁忌，但需要一句明确的「永久下线」结论，否则等于把一段能复用的验证逻辑凭印象丢掉。

**XSG 用例集当前暂停维护**：`caseXsg/` 下 29 条保留不动，仅作为参考，不作为验收基线；slp 与 xsg 仍指向同一套测试环境（只差 `package` 参数），需要恢复时 `run_all_case.py xsg` 可直接跑。因此日常回归、基线对比只看 SLP 那 137 条。

礼物优惠券另有一个容易踩的坑：**有损 / 无损不是独立开关，而是券商品的 `coupon_type` 决定的**——`gift_discount`（89297）折扣额平台减免、收礼方按实付分成（有损）；`pro_gift_discount`（89370）平台补贴、收礼方按原价分成（无损）。`pro_gift_discount` 目前只接入房间链路，私聊会被拒单，详见 `caseSlp/test_coupon_2.py` 文件头。

---

## 快速开始

```bash
git clone <仓库地址>            # 换成自己可访问的地址
cd qa-slpPayTest
pip3 install -r requirements.txt
mkdir -p log                     # 运行日志目录，首次要手动建

python3 run_all_case.py slp      # SLP 全量
python3 run_all_case.py xsg      # XSG 全量
```

---

## 目录结构

```
qa-slpPayTest/
├── run_all_case.py        # 全量入口：逐条播报 + 未通过清单（日常主入口）
├── run_crontab_case.py    # 定时任务入口：只汇总与播报失败/异常，不拉分支、不列通过用例，结果推企微
├── Robot.py               # 结果通知：企业微信群机器人 webhook
├── autoGitPull.py         # 分支检查 + 记录上次执行时间
├── pre_push_audit.py      # 推送前全仓审查（十一类）
├── deploy.sh              # 云服务器一键部署
├── caseSlp/               # SLP 用例
│   ├── config.py          # 账号、房间、礼物、倍数等测试数据
│   ├── tools.py           # 转发层，实现统一在 common/tools.py
│   └── test_*.py
├── caseXsg/               # XSG 用例（结构与 caseSlp 一致）
├── common/                # 公共能力，两个 App 共用
│   ├── Config.py          # 环境地址、工程路径、分支信息
│   ├── Session.py         # 登录取 token
│   ├── Request.py         # 请求封装：同账号频控、重试回放
│   ├── Assert.py          # 断言：状态码 / 等值 / 响应体 / 区间 / 轮询等值
│   ├── runFailed.py       # Retry 装饰器（只重试断言失败）
│   ├── report.py          # 结果汇总：编号 + 用例名 + des + 失败明细、按场景族统计
│   ├── runflow.py         # 两个入口共用的执行流程：环境体检结论、刷新 token、计数与各类清单落盘
│   ├── case_groups.py     # 用例模块 → 业务场景族（分类统计与推送看的都是这张表）
│   ├── preflight.py       # 执行前环境体检：MySQL / Redis / 接口，不通不跑（退出码 3）
│   ├── selfcheck.py       # 框架自身守卫逻辑的离线自检（不连库）
│   ├── tools.py           # 造数工具：账号、房间、背包礼物、加速卡、优惠券
│   ├── basicSlpXsgData.py # encodeData：拼请求体
│   ├── conSlpXsgMysql.py  # MySQL 操作（每线程独立连接、断线重连）
│   ├── conRedis.py        # Redis 操作（文本连接 + 二进制连接）
│   ├── Logs.py / Consts.py / method.py / getToken.py
└── log/                   # 运行时生成，不入库
```

---

## 运行方式

### 本机只做静态检查（默认）

本机不在测试环境内网（`192.168.1.0/24`），跑真实用例只会得到一屏「连不上库」的假失败——那既不是回归信号，也会把「真的全挂了」这个信号提前用掉。两个入口开跑前都会先探 MySQL / Redis / 支付接口，任一项不通就不执行任何用例、退出码 `3`，并把原因写进 `log/runCode.log`。

所以本机的固定动作是这三条，全都不连服务端、不连库：

```bash
python -m compileall -q caseSlp caseXsg common   # 语法能否解析
python -m common.selfcheck                       # 框架守卫逻辑（频控退避 / 失败现场 / 轮询读值）
python pre_push_audit.py                         # 全仓审查（十一类）
```

真实执行在服务器上：`git pull --ff-only` 之后跑 `run_all_case.py` 或 `run_crontab_case.py`。只想看体检结果：`python -m common.preflight slp`（不可用时退出码同为 `3`）。

### 全量

```bash
python3 run_all_case.py slp
python3 run_all_case.py xsg
```

`run_all_case.py` 会先刷一次 token、检查代码分支，再执行全量；不带参数默认跑 SLP。传了 slp/xsg 以外的值会直接报错退出（退出码 `2`），不会静默跑全量。

### 只跑指定用例（调试主力）

用环境变量 `CASE`，逗号分隔，可以混着写：

```bash
# 整个文件（带不带 test_ 前缀、.py 后缀都行）
CASE=test_check python3 run_all_case.py slp

# 单个用例 / 整个类
CASE=test_naming_song.TestPayCreate.test_003 python3 run_all_case.py slp
CASE=test_naming_song.TestPayCreate python3 run_all_case.py slp

# 多条混搭
CASE=test_check.TestPayCreate.test_002,test_coupon python3 run_all_case.py slp
```

不设 `CASE` 就是全量。写用例名（含 `.`）时按名字加载，找不到会造一条报错用例，**不会静默跳过**。

### 定时任务

服务器上每天 10:00 跑一轮全量，结果推到企业微信群。webhook key 放在**仓库外**的 `~/.slp_env`（权限 600），代码、crontab 里都不出现它。

**① 建凭据文件**（key 从企微群「群机器人」里取）：

```bash
cat > /home/<user>/.slp_env <<'EOF'
export WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<key>'
EOF
chmod 600 /home/<user>/.slp_env
```

**② 装 cron**（可重复执行，会替换掉旧的同名任务）：

```bash
cat > /tmp/slp_cron <<'EOF'
# 每天 10:00 拉最新代码后跑全量并推送到企微；日志按日期落盘，同时清理 30 天前的
0 10 * * * . /home/<user>/.slp_env; cd /home/<user>/qa-slpPayTest && mkdir -p log && { find log -name 'cron_*.log' -mtime +30 -delete; git pull -q --ff-only; PUSH_WX=1 /usr/bin/python3 run_crontab_case.py slp; } >> log/cron_$(date +\%F).log 2>&1
EOF

(crontab -l 2>/dev/null | grep -v 'run_crontab_case.py slp'; cat /tmp/slp_cron) | crontab -
rm -f /tmp/slp_cron; crontab -l
```

为什么 key 单独放一个文件：crontab 内容是明文，能登这台机器的人 `crontab -l` 就看得见；而 webhook key 拿到就能往群里发任意消息。放 600 权限的文件里，至少跟登录权限一个级别，也不会随 crontab 内容被拷来拷去。

`. 文件;` 后面用**分号不用 `&&`**：凭据文件一旦不在了（换机器、误删），`&&` 会让整条命令短路——连用例都不跑，也不报错，看起来就像「今天一切正常」。用分号的话，用例照跑，只是不推送，日志里那行「未设置 WX_BOT_SLP」会说明原因。宁可少一条推送，不能少跑一轮用例。

推送形态：

| 本轮结果 | 群里的消息 |
|---|---|
| 全部通过 | 两行：绿色 `通过 125 / 137` + 灰色尾注 `slp　跳过 12　重试 1　4m52s　lxm@3adcbba` |
| 有失败/异常 | 橙色结论行 `2 失败　1 异常`（附灰色通过数）→ 灰色性质行 `环境 1　造数 1　断言 1`（全是断言时不列）→ 有未通过的场景族 → 编号清单：`1.`　`test_gs_room.py · test_007`、用例描述、一行原因（灰字）；非断言失败在标题后标 `(造数)` / `(异常·环境)`；最多列 10 条，其余指向 `log/notPassCase.log` |
| 0 条用例 | 红色 `本轮 0 条用例被执行`，退出码 2——套件为空或 `CASE` 写错，不算通过 |
| 环境不可用 | 红色 `环境不可用，本轮未执行` + 探测失败的那几项，退出码 3——一条用例都不跑 |
| 执行中断 | 红色 `执行中断`：用例没跑完，退出码 2，堆栈落 `log/runCode.log` |
| 推送本身失败 | 只记日志不打退出码：网络抖动不该把「用例跑完了」说成「执行异常」 |

排版是给「扫一眼」用的：第一行只放结论，应用名/跳过/重试/耗时/版本全部下沉到最后一行灰字，没事的时候固定两行，变红的位置才会被注意到。失败清单靠缩进做层级、不用反引号（等宽字体夹中文很难读）。超过单条上限拆成多条时，第 2 条起标 `(2/3) 清单续`，避免续条在群里认不出属于哪一轮。

跳过的 12 条只计数、不列明细——它们是已确认下线的功能，每天列一遍会把真问题淹掉。

`run_crontab_case.py` 与 `run_all_case.py` 的区别：不拉取代码分支、不逐条播报通过用例，只出汇总和失败清单，适合无人值守。它也认 `CASE`（写法相同），改完汇总/落盘逻辑后不必跑完 137 条就能验证，加 `PUSH_WX=0` 就不会往群里发消息：

```bash
CASE=test_check python3 run_crontab_case.py slp
```

---

## 测试环境

| 用途 | 地址 |
|------|------|
| API | `https://<api-host>/`（`common/Config.py` 的 `appInfo`） |
| MySQL | `<db-host>:3306`，账号密码见 `common/Config.py`，可用 `DB_HOST` 等环境变量覆盖 |
| Redis | `<db-host>:6379`，无密码，可用 `REDIS_HOST` / `REDIS_PORT` 覆盖 |

具体地址不写进文档，统一配在 `common/Config.py` 或上面那几个环境变量里（本文出现的 `<api-host>` / `<db-host>` 均为占位符）。

slp 与 xsg 当前指向同一套测试环境，请求只差 `package` 参数（两个 App 各自的包名，见 `caseSlp/config.py` / `caseXsg/config.py`）。

---

## 环境变量

全部可选，不设就用默认值。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CASE` | 空（全量） | 只跑指定文件/类/用例，逗号分隔 |
| `ROOM_DEBUG` | `0` | 点唱房用例请求前打印房间现场（毫秒时刻 + `Room.Data` 的 `exists/ttl/len/has_factory_type` + `tavern_enable`/`gate_chseq` 两个开关 + 库内行数/类型/`deleted`/房主），排查「房间类型错误」时开。失败时不论此开关都会带上现场 |
| `NAMING_SLEEP` | 空（用各处原值 5s / 8s） | 点唱房用例「改库 → 下单」之间的等待覆盖值。实测设 `0` 只省约 9 秒（52 秒里的其余部分是异步落库必需），所以默认保留原值，此开关仅作评测用 |
| `ASSERT_SLEEP` | `0.3` | 每次状态码断言前的等待秒数（rpc 延迟补偿），设 `0` 关闭。主机名在 `config.linux_node` 里登记的测试机上自动免等待 |
| `ASSERT_SETTLE` | 空 | 设 `1` 强制恢复断言延迟补偿；去掉等待后出现抖动时的回滚开关，不必改代码 |
| `WAIT_TIMEOUT` / `WAIT_INTERVAL` | `3` / `0.2` | `assert_equal_eventually` 的轮询上限与间隔 |
| `RETRY_SLEEP` | `1` | 重试间隔基数，第 n 次重试等 `n × RETRY_SLEEP` 秒，设 `0` 改为立即重试 |
| `REQUEST_INTERVAL` | `1` | 同一 App 两次请求的最小间隔（服务端频控）。2026-10-28 实测 2 秒 → 292s、1 秒 → 201s，两轮均 0 失败且日志里没有一次频控，故默认 1；再往下（`0.5`）只快约 30 秒，但频控风险不是线性的，不建议作默认 |
| `FREQUENT_BACKOFF` | `2` | 命中频控后的退避基数，第 n 次等 `n × 该值`（2s、4s）。**与 `REQUEST_INTERVAL` 解耦**：调小间隔是为提速，不该顺带把退避也调弱 |
| `FREQUENT_RETRY` | `2` | 命中频控/防重文案（「请勿频繁操作」「请求太慢了，请稍后重试」等）后的重试次数 |
| `PUSH_WX` | `0` | 是否推送企业微信群；`run_crontab_case.py` 的 cron 命令里显式写 `PUSH_WX=1`，手工跑不带就不会往群里发消息 |
| `LIST_PASS` | `0` | 推送时额外列出通过用例（需 `PUSH_WX=1`） |
| `PREFLIGHT` | `1` | 执行前的环境体检开关。设 `0` 跳过体检（只用于排查「体检误报」，会在 `log/runCode.log` 里留一行）；cron 里永远不写它 |
| `WX_BOT_SLP` | **必填**（无默认值） | 企微机器人 webhook，只从环境变量读；仓库里不留 key，未设置时推送跳过并在日志里说明 |
| `DB_HOST` / `DB_USER` / `DB_PASS` | 见 `common/Config.py` | 测试库连接信息 |
| `REDIS_HOST` / `REDIS_PORT` | 见 `common/Config.py` | Redis 连接信息 |

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 全部用例通过 |
| `1` | 存在失败或异常（跳过不计） |
| `2` | 没跑完：命令行参数错误（两个入口都只接受 slp / xsg，传错直接退出，不会静默跑一轮覆盖日志）、`CASE` 写错导致 0 条用例被执行，或执行中途抛异常（suite 构造异常、磁盘满等） |
| `3` | 环境不可用：MySQL / Redis / 支付接口至少一项探测失败，一条用例都没执行。与 `1` 严格区分——「没跑」和「跑了但红」的处置完全不同 |

在 `cmd && 下一步`、cron 告警、调度平台里都靠这个退出码判断本轮结果。

---

## 日志与报告

执行结束后控制台输出带编号的完整未通过清单（编号 / FAIL|ERROR|SKIP / 用例名 / des / 失败明细），随后一行「失败性质」把红点归堆（环境 / 造数 / 接口 / 断言 / 其他），同时落到 `log/`：

| 日志 | 内容 |
|------|------|
| `notPassCase.log` | 未通过清单，**排查先看这个** |
| `progress.log` | 逐条实时进度：`[ 37/137] FAIL  12.30s  test_xxx.test_004` |
| `failCase.log` | 失败与异常的完整堆栈 + **失败现场**（入参/响应/账户快照） |
| `retryCase.log` | **重试后才通过**的用例清单：哪一轮、哪个断言先失败 |
| `caseResult.log` | 每轮执行的条数汇总 + **失败性质**归堆 + 场景族统计 + 重试摘要 |
| `getSession.log` | token 获取情况 |
| `updateGitCode.log` / `gitBranchError.log` | 分支检查与上次执行时间 |
| `runCode.log` | 入口异常（如 App 名不认识）；重试摘要（只看这一个文件的人也能判断这轮有没有被重试兜住的问题） |

失败性质由失败文本自动判定（`common/report.py: failure_kind`），五类对应五种处理动作：

| 性质 | 典型文本 | 该做什么 |
|------|------|------|
| `环境` | `Can't connect to MySQL ... (timed out)`、`Max retries exceeded`、`Timeout connecting to server` | 先看环境，代码大概率没问题，修好后重跑 |
| `造数` | `pymysql` 的非连接类报错（表不存在、唯一键冲突） | 看用例前置的造数语句和脏数据 |
| `接口` | `Actual Code: 502, Expected Code: 200` | 服务端异常，找开发看网关/服务日志 |
| `断言` | `实际结果: 3600, 预期结果: 4200`（含轮询超时后缀） | 业务逻辑不符，查分成/结算口径 |
| `其他` | `KeyError`、`TypeError` | 脚本自身 bug |

```bash
tail -n 100 log/notPassCase.log   # 先看未通过清单
tail -f log/progress.log          # 跑到第几条、每条多久（另开一个窗口）
tail -n 200 log/failCase.log      # 需要堆栈与现场时再看
```

三个跟排查直接相关的设计：

- **进度写文件而不是只打控制台**：`python run_all_case.py slp | tail -60` 时 tail 要等 EOF 才输出，整个运行期间看不到任何东西，看着就像卡死；`log/progress.log` 可以边跑边看。每条附带本用例耗时（含重试），顺手能找出慢用例。
- **失败掉落现场**（`common/Scene.py`）：每条用例执行期间缓存最近 5 次请求/响应（入参 + HTTP 状态码 + 响应体），失败时连同打赏者/收礼人的 `xs_user_money`、`xs_user_profile` 快照一起写进 `failCase.log`。原来这些只在控制台滚一次，看不到了就只能重跑一轮。快照只观测不参与断言，自身异常全部吞掉，且只在失败时才读库。
- **重试可见**（`log/retryCase.log`）：`@Retry` 重试成功后用例状态是 PASS，和一次就过的用例长得一模一样。实测一轮全量有 **54 次重试**，也即 54 次真实断言失败被重试掩盖住了，而它们此前唯一的痕迹是控制台里滚过的那行 `[Retry 1/1]`。现在按用例归档成清单（含第几轮、失败明细），`progress.log` 的行尾也会标 `[重试×N]`。**看到「通过」时先问一句：是不是重试才过的**。

---

## 框架自检

```bash
python -m common.selfcheck      # 不连服务端、不连库，12 项检查，全部通过才退出 0
```

频控退避、失败现场、异步读值轮询这三类守护逻辑，真实全量里可能一整轮都触发不到（例如 2026-10-27 那轮 137 条全绿，一次频控都没撞上、一次失败都没有），于是「写了」和「真的按预期工作」之间始终差一步，等到真需要它的时候才发现坏了。自检用假 `requests`/假时钟把这几条分支固定走一遍：频控命中后退避重试、重试耗尽把响应交回用例、四种实测文案都能识别、退避间隔递增、非 json 响应不误判、现场能拼出入参/响应/账号快照且自身异常不影响用例结论，以及轮询版真的会重读、超时会写明等了多久、首轮命中只读一次。

只验证框架行为，不碰任何业务预期值——改框架代码后跑一次，别等到线上红一轮才发现。

---

## 编写用例

约定（unittest 本身就要求这些）：

- 测试文件 `test_*.py`，测试类 `Test*`（不能写 `__init__`），测试方法 `test_*`
- 用例挂在 `caseSlp/` 或 `caseXsg/` 下，公共能力只写 `common/`；两侧 `tools.py` 只做转发，避免同一实现维护两份
- 用例方法第一个参数写 `des='场景,预期'`：报告按方法签名里的 `des` 默认值展示（取不到时退回 docstring），写得具体才能一眼看出挂了什么
- 断言一律带 `reason(des, res)`，失败时报告里能直接看到请求与响应
- 用例末尾的 `case_list_b[des] = result` 是历史写法（报告已改为从 unittest 结果里收集，不再读这几个 dict），新增用例可以只写断言

```python
@Retry(max_n=2, sleep=5)   # 只重试 AssertionError；skip 不重试
class TestPayCreate(unittest.TestCase):
    def test_001(self, des='点唱房-点歌,一首歌'):
        rid = gs_music_rid
        assert_equal(mysql.checkRidFactoryType(rid), 'business-music')  # 先确认环境数据
        prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
        data = encodeData(rid=rid, payType='choose_song', money=money, order_songs=[...])
        res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
        assert_code(res['code'])
        assert_body(res['body'], 'success', 1, reason(des, res))
        assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - money)
```

断言怎么选：

| 断言 | 用途 |
|------|------|
| `assert_code(res['code'])` | HTTP 状态码，默认期望 200 |
| `assert_body(body, 'success' 或 'msg', 预期, reason(des, res))` | 响应字段，多值可传元组当白名单 |
| `assert_equal(actual, expect)` | 等值；数值自动容忍 `1e-4` 误差（覆盖 `Decimal` 与 float 混比） |
| `assert_between(actual, low, high)` | 浮动区间，如分成比例 |
| `assert_equal_eventually(lambda: mysql.xxx, expect)` | **读账户表一律用它**：轮询读值，直到等于预期或超时 |

`assert_equal_eventually` 内部处理了三件容易踩的事：中间轮次的失败原因不会污染报告；超时后拿最后一轮的失败信息报错；失败原因里会注明「已轮询 N 次、等待 X 秒仍未达标」——「结算变慢」和「分账算错」看这一句就能分开。

**为什么读账户表必须走轮询版**：服务端扣款是同步的，收礼方分成却是异步落库。发完请求立刻同步读一次，收礼方那边必然还是 0。2026-10-27 那轮全量的实测：`137` 条用例里 **50 条（36%）是重试一轮才过的**，`log/retryCase.log` 里的失败明细几乎全是同一句 `实际结果: 0, 预期结果: 60/80/420/4620/...`。也就是说报告写着「通过 125」，其中几十条第一轮其实什么都没验到，全靠 `@Retry` 重跑一遍撞对了。现在全仓 567 处余额/统计断言统一改成轮询版：首轮就命中时只读一次（不打赏方扣款那种同步读值拖慢），要等时按 `WAIT_INTERVAL` 最多等 `WAIT_TIMEOUT`。

这条规则由 `pre_push_audit.py` 的第 6 项守着：`assert_equal(mysql.selectUserInfoSql(...))` 会直接审查不通过；把读值提前求好再传给轮询版（`assert_equal_eventually(mysql.xxx(...), expect)`）同样拦——那等于每次白等一轮超时。

重试是怎么跑的（`Retry` + `common/Request.py` 的回放）：

- 只重试 `AssertionError`；`SkipTest`、`TypeError`、`KeyError`、`DbQueryError` 不重试，重跑也不会变好
- 重试轮**不会重复下单**：首轮下单成功后，同参数的 `pay/create` 请求直接复用首轮响应，只重新做读库断言
- 首轮下单**业务失败**时不复用（`success != 1` 的响应不进缓存），重试会真的重发请求 —— 否则偶发失败会被回放固定成“连撞四轮同一个错”
- 数据准备类操作（改金额、插背包礼物）在重试轮跳过，避免把首轮已生效的造数覆盖掉

---

## 排查手册

1. **先单跑，再全量**。全量里随机 1~2 条红、单跑却必绿，基本是环境/缓存/顺序依赖，不是用例逻辑问题。
2. **注意时区差**。测试机是 CST（东八区），**MySQL 是 UTC**：`from_unixtime` 出来的时间会比机器时间差 8 小时。往时间窗口里造数据时不要卡边界（比如插「上周一 00:00」），要放在窗口中间，否则任何时区偏差都会让它掉出区间。
3. **Redis 连接配置的 key 是 `host_slp`**，不是 `host`；`conRedis.get(key)` 走的是 `decode_responses=True` 的连接，读 protobuf 之类的二进制值会抛 `UnicodeDecodeError`，这种场景用 `conRedis.getRawConn()`。
4. **看到「房间类型错误」先看失败现场，不用再复现**。这句文案也不再是孤证：`caseSlp/test_naming_song.py` 的下单一律走 `post_pay()`，命中房间类错误时会把现场写进失败原因（毫秒时刻 + `Room.Data` 的 `exists/ttl/len/has_factory_type` + `tavern_enable`/`gate_chseq` 两个开关 + 库内行数/类型/`deleted`/房主 + **本次请求耗时和后端实例标识**），据此一次就能分开几种情形：**行数≠1 或 `deleted`≠0 → 环境数据坏了**；**库内正确且两个开关与常态一致 → 服务端侧问题**；其中再看两条不需要服务端配合的线索——**耗时明显偏长（几秒 vs 百毫秒）→ 超时/慢查询**，**后端实例集中在同一个 IP → 某台实例异常/版本旧**（8% 这个量级很接近 1/12，一台/十二台）。

   后者实测**是服务端 bug，不是环境噪声**：13 轮命名颂（每轮 10 条）共失败 9 次，约 7%。三条排除性证据：

   - **耗时 27~42ms 就返回**：正常请求也是这个量级，所以不是超时/慢查询——服务端在本地判断里直接拒了，没走到慢 RPC
   - **同一时刻库内配置正常**：`xs_chatroom` 44 个字段里 `type=listensong`、`types=joy`、`room_factory_type=business-music`，与成功请求完全一致
   - **相关缓存全部正常**：`Room.Data`（binlog 刷新后 DEL、请求时回源重建，miss 属正常）、`Room.Desc`（只是房间名）、`slp.tavern.room.enable`（`xs_chatroom` 里根本没有 tavern 字段，它是另一条业务线的开关，`'0'` 对点唱房而言是正确的）、`room.gate.chseq`（常态也是 None）、代码删房间（零调用）

   同一个房间、同一份配置，92% 的请求放行、8% 报「房间类型错误」——这是服务端侧的问题。

   注意口径：同一个失败，单跑命名颂时报告显示 `重试后才通过: 1 条（10.0%）`（分母 10 条），跑全量时显示 `0.7%`（分母 137 条，而这个文件只跑一轮）。**别被全量里的 0.7% 麻痹**——对点歌/冠歌这条链路，每轮 10 条里就有一条会被服务端拒掉，真实失败率 10%。要盯这个 bug 就单跑这个文件，信噪比高得多，看趋势也快。

   **不要用「清缓存」「放宽重试」去消掉它**。那样做能让报告变绿，但 bug 就此查无实据。客户端只负责适配环境、保证用例正确执行；`@Retry(max_n=3, sleep=5)` 兜底只代表这条用例不会红，不代表问题不存在——所以每轮输出固定打印一行 `重试后才通过: N 条（X%）`，这个百分比就是它的存在证明，服务端修好后会掉到 0，恶化会涨。

   （排查记录里的一个坑：前 7 轮恰好每轮 1 条，据此算过「连续 7 轮恰好 1 条的概率只有 0.09%，所以是周期任务」。这是**事后偏差**——「恰好 1 条」是观察完才挑出来的特征；再跑 3 轮就有 2 轮一次没失败，周期性假设直接作废。判断是不是随机，不能只挑一个事后的统计量来算概率。）

   另外没必要主动删 `Room.Data.<rid>`：库数据正确时，缓存刷新交给 binlog 同步任务即可——实测缓存绝大多数时间不存在（`ttl=-2`），但用例照样通过，「缓存不在」本身不是判据。

   （历史坑：重试轮曾复用首轮的业务失败响应，四轮都不重发请求，看起来像服务端持续故障；已由 `common/Request.py` 的 `_is_business_success` 修掉，改回放逻辑时别退回去。）
5. **环境数据先行断言**。用例开头用 `checkRidFactoryType(rid)` / `checkUserBroker(uid)` 这类断言确认房间类型、公会关系，环境被改坏时能一眼看出是“数据不对”而不是“代码坏了”。
6. **改完先编译**：`python3 -m compileall -q caseSlp caseXsg common`，比跑一遍全量快得多。

---

## 常见问题

| 问题 | 处理 |
|------|------|
| 一条用例都没跑 / 大量跳过 | 看 `log/getSession.log` 是否取到 token，再看 `log/caseResult.log` 的条数汇总；跳过信息里会写依赖了哪条前序用例 |
| `pip install` 失败 | 确认 `python3 --version` ≥ 3.9；`requirements.txt` 只保留 4 个真实依赖 |
| 数据库连接失败 | 检查与 `DB_HOST`（默认值见 `common/Config.py`）的连通性 |
| Token 获取失败 | 检查 `<api-host>/test/userToken` 是否可访问 |
| `ModuleNotFoundError` | 重新 `pip3 install -r requirements.txt` |
| 网络/端口要求 | 见 [DEPLOY.md](DEPLOY.md) 的「网络要求」 |

---

## 这个仓库的第一原则

**这些 case 是为了发现服务端支付接口的逻辑问题而存在的，不是为了交一份全绿的报告。**

由此推出两条硬约束：

1. **验证逻辑必须严谨正确**。断言口径只能是「服务端应该做什么」，不能因为跑不通就往回调。
2. **允许增强健壮性，不允许弱化校验**。测试环境复杂、有异步落库、有频控、有慢查询，这些可以靠脚本适配；但适配的对象永远是**环境噪声**，不是**断言标准**。

| 合法适配（环境噪声） | 禁止（弱化校验） |
|---|---|
| 异步落库→ `assert_equal_eventually` 轮询等到达 | 把精确值改成「非空/存在即可」 |
| 频控 → `REQUEST_INTERVAL` 退避重发 | 把断言注释掉 |
| 网络抖动 → `@Retry` 真重发（失败响应不缓存） | 用 `skip` 躲开已知失败 |
| 慢环境 → 调大超时上限、拉长轮询窗口 | 把断言包在 `if` 里，条件不成立就静默跳过 |
| 造数、清场、准备缓存 | 用 `try/except: pass` 吞掉断言失败 |

两者的区别只问一句：**这个改动是让「真实结果」更稳定地读出来，还是让「不真实的结论」显得更好看？** 前者做，后者一律不做。

由 `pre_push_audit.py` 第 7 项守者：条件断言、被 except 吞掉的断言、被注释掉的断言、大于 1 的数值容差都会直接审查不通过；skip 数量偏离基线（装饰器 8 / 运行时 3）会给出提醒。

---

## 提交约定

- **分支：改动都提交在 `lxm`，服务器定时任务也跟 `lxm`**

  ```bash
  git push origin lxm
  ```

  服务器工作副本就停在 `lxm` 上，cron 里的 `git pull` 拉的是当前分支的上游，不需要写分支名。

  `master` 保留一份 fast-forward 快照（直接 clone 时默认分支就是最新的），两条分支永远指向同一个提交：

  ```bash
  git checkout master
  git merge --ff-only lxm
  git push origin master
  git checkout lxm
  ```

  `--ff-only` 不是可选项：它拒掉任何合并提交，两条分支永远是同一条历史线。否则一旦 master 上多出一个 merge commit，同步就变成「两边各自长东西」，以后想合只能手工挑提交

  只推 `lxm` 不影响定时任务，master 忘了同步也只是快照旧一点——把服务器指向开发分支，就是为了避免「代码推上去了但服务器还在另一个分支上等」这种静默偏差

- 提交信息用中文写清「为什么改」，一次提交一件事
- 用 `git add -u`（只暂存已跟踪文件）而不是 `git add -A`，别把临时脚本、日志、`.commit_msg.txt` 带进提交
- 推送前跑一遍 `python pre_push_audit.py`（十一类检查）：解析与 import、重构函数的分支覆盖、悬空调用、未用 import、零引用定义、账户读值写法、**验证强度**、**密钥泄露**、**场景族登记**、**未定义名字**、**调用点实参与签名**。退出码非 0 就不要推
- `compileall` 只查语法：删掉 `import time` 后留着 `time.sleep(...)` 依然编译通过，要等服务器真跑到那行才 NameError；若那行在 skip 用例或异常分支里，可能好几轮都碰不到。审计第 10 类用作用域分析拦住这类名字（包含推导式变量、闭包、解包、`from X import *`）
- 改了公共助手（`common/tools.py` / `common/Assert.py` / `conMysql` 方法）的参数名或位置，漏改调用点不会报错，只在跑到那行时 TypeError。审计第 11 类拿真实函数签名的 `bind_partial` 校验全仓 case 里的 2700+ 处调用（只查 `*args`/`**kwargs` 下定不下来的除外）
- 新增用例文件时在 `common/case_groups.py` 里登记场景族：漏登记不会报错，只会让这一类悄悄归到「未分组」、从按场景族的统计里消失——比没有统计更糟，因为看的人会以为「这类没问题」。审计第 9 类会拦住
- 凭据不进仓库：webhook key、GitHub 令牌、密码一律走环境变量或本机凭据存储。它们一旦进了 git 历史就永久留在那里，删掉文件也回收不了，只能重新生成——审计第 8 类会拦住（GitHub token / 企微 webhook / 私钥 / URL 内嵌密码 / app_secret）
- 代码改动完成、自检通过后直接提交推送，不留半成品
