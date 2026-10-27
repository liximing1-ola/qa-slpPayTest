# qa-slpPayTest

不夜星球（SLP）/ 小拾光（XSG）打赏与支付链路的接口自动化用例。

- **框架**：Python 3.9+、unittest（`discover` 自动收集，不用维护用例清单）
- **依赖**：`requests` / `urllib3` / `PyMySQL` / `redis`，见 `requirements.txt`
- **覆盖**：私聊打赏、房间打赏、跨公会与跨档分成、点唱房（点歌/冠歌）、礼物优惠券、房间守护、人气加速卡、甄选礼盒、账户与房间数据校验
- **部署到云服务器**：见 [DEPLOY.md](DEPLOY.md)

当前基线（SLP 全量 136 条）：**通过 120 / 失败 0 / 跳过 16**。跳过的是「依赖前序造数」的用例，不是缺陷。

---

## 快速开始

```bash
git clone https://github.com/liximing1-ola/qa-slpPayTest.git
cd qa-slpPayTest
pip3 install -r requirements.txt
mkdir -p log                     # 运行日志目录，首次要手动建

python3 run_all_case.py slp      # 不夜星球全量
python3 run_all_case.py xsg      # 小拾光全量
```

---

## 目录结构

```
qa-slpPayTest/
├── run_all_case.py        # 全量入口：逐条播报 + 未通过清单（日常主入口）
├── run_crontab_case.py    # 定时任务入口：只汇总与播报失败/异常，不拉分支、不列通过用例
├── Robot.py               # 结果通知：企业微信群机器人 / slack webhook
├── autoGitPull.py         # 分支检查 + 记录上次执行时间
├── deploy.sh              # 云服务器一键部署
├── caseSlp/               # 不夜星球用例
│   ├── config.py          # 账号、房间、礼物、倍数等测试数据
│   ├── tools.py           # 转发层，实现统一在 common/tools.py
│   └── test_*.py
├── caseXsg/               # 小拾光用例（结构与 caseSlp 一致）
├── common/                # 公共能力，两个 App 共用
│   ├── Config.py          # 环境地址、工程路径、分支信息
│   ├── Session.py         # 登录取 token
│   ├── Request.py         # 请求封装：同账号频控、重试回放
│   ├── Assert.py          # 断言：状态码 / 等值 / 响应体 / 区间 / 轮询等值
│   ├── runFailed.py       # Retry 装饰器（只重试断言失败）
│   ├── report.py          # 结果汇总：编号 + 用例名 + des + 失败明细
│   ├── tools.py           # 造数工具：账号、房间、背包礼物、加速卡、优惠券
│   ├── basicSlpXsgData.py # encodeData：拼请求体
│   ├── conSlpXsgMysql.py  # MySQL 操作（每线程独立连接、断线重连）
│   ├── conRedis.py        # Redis 操作（文本连接 + 二进制连接）
│   ├── Logs.py / Consts.py / method.py / getToken.py
└── log/                   # 运行时生成，不入库
```

---

## 运行方式

### 全量

```bash
python3 run_all_case.py slp
python3 run_all_case.py xsg
```

`run_all_case.py` 会先刷一次 token、检查代码分支，再执行全量；不带参数默认跑 SLP。

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

```bash
crontab -e
# 每天凌晨 2 点跑 SLP，结果追加到 log/cron.log
0 2 * * * cd /home/ecs-user/qa-slpPayTest && python3 run_crontab_case.py slp >> log/cron.log 2>&1
```

`run_crontab_case.py` 与 `run_all_case.py` 的区别：不拉取代码分支、不逐条播报通过用例，只出汇总和失败清单，适合无人值守。

---

## 测试环境

| 用途 | 地址 |
|------|------|
| API | `https://192.168.1.23/`（`common/Config.py` 的 `appInfo`） |
| MySQL | `192.168.1.24:3306`，默认 `root` / `root`，可用 `DB_HOST` 等环境变量覆盖 |
| Redis | `192.168.1.24:6379`，无密码（`common/conRedis.py`） |

slp 与 xsg 当前指向同一套测试环境，请求只差 `package` 参数（`com.yhl.sleepless.android` / `com.im.shiguang.android`）。

---

## 环境变量

全部可选，不设就用默认值。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CASE` | 空（全量） | 只跑指定文件/类/用例，逗号分隔 |
| `ROOM_DEBUG` | `0` | 点唱房用例请求前打印房间缓存快照（`exists/ttl/len/has_factory_type`），排查「房间类型错误」时开 |
| `ASSERT_SLEEP` | `0.3` | 每次状态码断言前的等待秒数（rpc 延迟补偿），设 `0` 关闭 |
| `WAIT_TIMEOUT` / `WAIT_INTERVAL` | `3` / `0.2` | `assert_equal_eventually` 的轮询上限与间隔 |
| `RETRY_SLEEP` | `1` | 重试间隔基数，第 n 次重试等 `n × RETRY_SLEEP` 秒，设 `0` 改为立即重试 |
| `REQUEST_INTERVAL` | `2` | 同一账号两次请求的最小间隔（服务端频控） |
| `FREQUENT_RETRY` | `2` | 命中「请勿频繁操作」后的重试次数 |
| `PUSH_WX` | `0` | 是否推送企业微信群；默认关闭，结果只落控制台与日志 |
| `LIST_PASS` | `0` | 推送时额外列出通过用例（需 `PUSH_WX=1`） |
| `WX_BOT_SLP` / `SLACK_BOT_SLP` | 内置测试群 | 通知 webhook，换群/轮换 key 不用改代码 |
| `DB_HOST` / `DB_USER` / `DB_PASS` | `192.168.1.24` / `root` / `root` | 测试库连接信息 |

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 全部用例通过 |
| `1` | 存在失败或异常（跳过不计） |
| `2` | 命令行参数错误（`run_crontab_case.py` 传了 slp/xsg 以外的值） |

在 `cmd && 下一步`、cron 告警、调度平台里都靠这个退出码判断本轮结果。

---

## 日志与报告

执行结束后控制台输出带编号的完整未通过清单（编号 / FAIL|ERROR|SKIP / 用例名 / des / 失败明细），同时落到 `log/`：

| 日志 | 内容 |
|------|------|
| `notPassCase.log` | 未通过清单，**排查先看这个** |
| `failCase.log` | 失败与异常的完整堆栈（不刷控制台，避免淹没清单） |
| `caseResult.log` | 每轮执行的条数汇总 |
| `getSession.log` | token 获取情况 |
| `updateGitCode.log` / `gitBranchError.log` | 分支检查与上次执行时间 |
| `runCode.log` | 入口异常（如 App 名不认识） |

```bash
tail -n 100 log/notPassCase.log   # 先看未通过清单
tail -n 200 log/failCase.log      # 需要堆栈时再看
```

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
        assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - money)
```

断言怎么选：

| 断言 | 用途 |
|------|------|
| `assert_code(res['code'])` | HTTP 状态码，默认期望 200 |
| `assert_body(body, 'success' 或 'msg', 预期, reason(des, res))` | 响应字段，多值可传元组当白名单 |
| `assert_equal(actual, expect)` | 等值；数值自动容忍 `1e-4` 误差（覆盖 `Decimal` 与 float 混比） |
| `assert_between(actual, low, high)` | 浮动区间，如分成比例 |
| `assert_equal_eventually(mysql.xxx, expect)` | **异步结算场景用它，别用 `sleep`**：轮询读值，直到等于预期或超时 |

`assert_equal_eventually` 内部处理了两件容易踩的事：中间轮次的失败原因不会污染报告；超时后拿最后一轮的失败信息报错。

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
4. **看到「房间类型错误」先查有没有 `[Retry]` 行**。这类偶发失败的真因可能在重试回放：首轮请求业务失败后，重试轮复用了那份失败响应，四轮都不重发请求，看起来就像服务端持续故障（已修复，见 `common/Request.py` 的 `_is_business_success`）。另外没必要主动删 `Room.Data.<rid>`：库数据正确时，缓存刷新交给 binlog 同步任务即可。
5. **环境数据先行断言**。用例开头用 `checkRidFactoryType(rid)` / `checkUserBroker(uid)` 这类断言确认房间类型、公会关系，环境被改坏时能一眼看出是“数据不对”而不是“代码坏了”。
6. **改完先编译**：`python3 -m compileall -q caseSlp caseXsg common`，比跑一遍全量快得多。

---

## 常见问题

| 问题 | 处理 |
|------|------|
| 一条用例都没跑 / 大量跳过 | 看 `log/getSession.log` 是否取到 token，再看 `log/caseResult.log` 的条数汇总；跳过信息里会写依赖了哪条前序用例 |
| `pip install` 失败 | 确认 `python3 --version` ≥ 3.9；`requirements.txt` 只保留 4 个真实依赖 |
| 数据库连接失败 | 检查与 `192.168.1.24:3306` 的连通性 |
| Token 获取失败 | 检查 `192.168.1.23/test/userToken` 是否可访问 |
| `ModuleNotFoundError` | 重新 `pip3 install -r requirements.txt` |
| 网络/端口要求 | 见 [DEPLOY.md](DEPLOY.md) 的「网络要求」 |

---

## 提交约定

- 提交信息用中文写清「为什么改」，一次提交一件事
- 用 `git add -u`（只暂存已跟踪文件）而不是 `git add -A`，别把临时脚本、日志、`.commit_msg.txt` 带进提交
- 代码改动完成、自检通过后直接提交推送，不留半成品
