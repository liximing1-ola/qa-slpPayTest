# -*- encoding=utf8 -*-
"""并发与幂等用例的公共动作：重置余额、读余额、读分成流水、给响应分类

两条用例共用这几个动作，口径必须一致——「频控算不算失败」的判断若在两个文件里
各写一遍，迟早会出现一个宽松一个严格，那时报告里的「并发异常 0 笔」就不可信了。
"""
import time

from common.Assert import WAIT_INTERVAL, WAIT_TIMEOUT
from common.Request import FREQUENT_MSG_KEYWORDS
from common.conSlpXsgMysql import conMysql as mysql


def read_money(uid):
    """读 xs_user_money.money：并发用例只给 money 渠道放钱，对账口径才唯一"""
    return mysql.selectUserInfoSql('single_money', uid, money_type='money')


# 除主渠道外的其他钱包：余额不足时服务端可能回退到别的渠道扣款，
# 只读 money 会把「从别处扣了」看成「压根没扣」，对账就失去意义
WALLET_CHANNELS = ('money', 'money_b', 'money_cash', 'money_cash_b', 'gold_coin')


def read_wallets(uid):
    """读全部钱包渠道，只在失败现场打印用：断言走 read_total_money（一条 SQL），
    不必为了对账多读 5 倍"""
    return {channel: mysql.selectUserInfoSql('single_money', uid, money_type=channel)
            for channel in WALLET_CHANNELS}


def read_total_money(uid):
    """四个人民币渠道的余额合计：money + money_b + money_cash + money_cash_b

    用合计而不是单个渠道：分成落到 money_cash 还是 money_cash_b，由「是否在工会、
    是否签署大神」决定，只看 money 会把「到账落别处」当成没到账。

    必须记住它是**可变余额**，不是累计收入（这点写错过一次）：账号自己打赏会从这里扣，
    所以只有「确定不是付款方」的账号才能拿它做增量校验——现在只给主播用。

    gold_coin 不在内：那是金币，不是人民币收入。
    """
    return mysql.selectUserInfoSql('sum_money', uid)


def reset_payer(uid, amount):
    """余额只留 amount，其余渠道清零；背包也清空——渠道一多，扣款落在哪个字段就不确定了"""
    mysql.updateMoneySql(uid, money=amount)
    mysql.deleteUserAccountSql('user_commodity', uid)


def max_pay_change_id():
    """账户流水表当前最大 id，当批次水位线：之后新增的行属于这一批"""
    rows = mysql.selectRawDict('select max(id) as max_id from xs_pay_change')
    return int(rows[0]['max_id'] or 0) if rows else 0


def read_gift_flows(after_id, gid):
    """取水位线之后、指定礼物的全部账户流水（不限 op、不限收款人）

    为什么按流水对账而不是按余额：余额是下游结果，里面混了自己付款、渠道差异
    （money_cash / money_cash_b）、到账迟到；流水是结算服务真正写下的东西，
    一行一个收款人，reason 里带 from / gid / num / rate，丢了一笔就是少一行。

    不限 op：分成可能落在 income，也可能落在别的 op 上——先让探针把「一笔打赏
    会写哪些行」量出来，而不是我先假设它只写 income。
    reason 里的 from / gid 有时存成整数有时存成字符串，JSON_UNQUOTE 后统一按字符串比。
    """
    sql = ("select id, uid, money, op, reason from xs_pay_change "
           "where id > {} and JSON_UNQUOTE(JSON_EXTRACT(reason,'$.gid'))='{}' order by id"
           .format(int(after_id), gid))
    return mysql.selectRawDict(sql)


def read_flows_by_uid(after_id, uid):
    """水位线之后某个账号的全部流水，不按 gid 过滤

    用途只有一个：探针成交却按 gid 一行都查不到时，把两种可能分开——结算压根没写
    流水（真缺陷），还是写了但 reason 里没有 gid（我们的筛选口径失效）。只看前者
    会把后者报成假红，只看后者会放过真缺陷。
    """
    sql = ("select id, uid, money, op, reason from xs_pay_change "
           "where id > {} and uid={} order by id".format(int(after_id), int(uid)))
    return mysql.selectRawDict(sql)


def wait_flows_stable(after_id, gid, least=1, quiet=5, await_uids=(), keep_uid=None):
    """等这批流水写完：至少读到 least 行，且连续 quiet 次读到的条数不再变化

    不用「读到 least 行就返回」：一笔订单写几行取决于分成配置（只给主播是 1 行，
    配了厅和公会长是 3 行），只要 1 行就返回会把探针的另外两条写路径漏掉，
    后面整条用例就只验了主播那一行，还看不出来。而「条数不再增长」与配置无关。

    least 是下界：它拦的是「结算分两段写、中间停了 0.3 秒就被当成写完了」；
    一笔都没读到时不谈稳定，会一直等到超时，把已有结果（可能为空）返回，
    由调用方的断言去判差多少。

    await_uids：这批里每笔都该留下付款流水的账号。光看行数不够——实测出现过
    「4 笔分成都到了、付款行只到 3 行」，然后行数静默了整整 0.6 秒，读的人以为
    写完了。传了它多个下界：这些账号各自至少一行，否则继续等（到超时为止）。
    只延长等待，不放宽断言：超时仍未覆盖，就是调用方那些断言要红的事。

    keep_uid：只看某一个账号的行（自刷分支）。自刷时这一批里只有这一个账号下单，
    别的账号的行只可能是**别的批次晚到**的：2026-10-29 真机撞上——test_003 频控未测到
    直接 SkipTest、没等自己那 8 笔落库，紧接着 test_004 的探针一取水位线，就把
    200250759 / 200252072 的 consume 行当成了自己这一笔的写路径，期望值凭空多两条。
    行数下界（least）也应按过滤后的行算，否则别人晚到的行会让它提前返回。
    """
    deadline = time.time() + WAIT_TIMEOUT
    last = -1
    same = 0
    expected = set(int(uid) for uid in await_uids)
    while True:
        rows = read_gift_flows(after_id, gid)
        if keep_uid is not None:
            rows = [row for row in rows if int(row['uid']) == int(keep_uid)]
        covered = set(int(row['uid']) for row in rows)
        # 覆盖度变化必然带来行数变化，所以只靠行数判静默就够；
        # 覆盖度单独作为「还不能返回」的条件
        same = same + 1 if len(rows) == last and len(rows) >= least else 0
        last = len(rows)
        if same >= quiet and expected <= covered:
            return rows
        if time.time() >= deadline:
            return rows
        time.sleep(WAIT_INTERVAL)


def wait_flow_quiet(quiet=5):
    """等流水表安静下来（最大 id 连续 quiet 次不变）再取水位线

    为什么需要：因「未测到」而 SkipTest 的用例**不等自己那批流水落库**。紧接着跑的下一条
    一取水位线，就会把上一条还在异步写的行当成自己的：2026-10-29 真机撞上——test_003
    频控未测到直接跳，test_004 的探针凭空多出 200250759 / 200252072 两条 consume，
    期望值多两条，红得毫无道理。这一步不宽不放任何断言，只是不把别人的行当自己的。

    超时也返回：结算真卡住时不能在这里无限等，该红的事交给调用方的断言。
    """
    deadline = time.time() + WAIT_TIMEOUT
    last = -1
    same = 0
    while True:
        now = max_pay_change_id()
        same = same + 1 if now == last else 0
        last = now
        if same >= quiet or time.time() >= deadline:
            return now
        time.sleep(WAIT_INTERVAL)


def split_flows(rows, payers=()):
    """把流水拆成收款行与付款行

    付款行按**付款方 uid** 认，不按 op 名认：实测这个厅写的是 op='consume'，
    op='pay' 一次都没出现过。按 op 名认会把付款行当成一条「收款写路径」——
    探针只有 1 个付款账号、并发有 4 个，两边的键集合永远不相等，报出来的红是假的；
    更糟的是「付款行数 = 成功笔数」那道校验因为探针付款行为空而整段跳过。
    op='pay' 仍然算付款行：别的厅/渠道也许就是这个字面量，两种判据取并集。

    payers 是调用方自己下单的账号。自刷（付款方同时是收款人）会把收款行误判成
    付款行，所以不能把收款人也塞进来——并发用例只打赏给主播，刚好满足。

    收款侧聚合成 {(uid, op): [行数, 金额合计]}，一个 key 就是一条写路径：
    三方分成就是三个 key，其中任何一个少写一笔都会在行数上露出来。
    """
    payer_set = set(payers)
    income, pay = {}, []
    for row in rows:
        if row['op'] == 'pay' or row['uid'] in payer_set:
            pay.append(row)
            continue
        slot = income.setdefault((row['uid'], row['op']), [0, 0])
        slot[0] += 1
        slot[1] += int(row['money'] or 0)
    return income, pay


def flows_by_key(rows):
    """把一批流水按（账号, op）聚合成 {key: [行数, 金额]}，不区分付款行与收款行

    给自刷分支用。自刷时付款方就是收款人，按 uid 认付款行（split_flows 的做法）会把
    收款行一起算进付款行，收款侧一条都剩不下——「收一份钱、发两份货」在付款侧完全
    看不出来（行数、金额都对）。按 op 分桶后不区分收付：一笔自刷写下的每个桶都要
    严格按成功笔数放大，多一行 income 就是多发了一份分成。

    金额允许为空（流水表 money 可空），按 0 算：直接相加会抛 TypeError，整条用例
    变成 ERROR，报告里就看不出是账错了还是代码崩了。
    """
    bucket = {}
    for row in rows:
        slot = bucket.setdefault((row['uid'], row['op']), [0, 0])
        slot[0] += 1
        slot[1] += int(row['money'] or 0)
    return bucket


def scale_income(income_probe, success):
    """把探针单笔实测的写路径按成功笔数放大，用来和并发批次的聚合值整体比较

    为什么整体比、不分开比：分开比键集合、再逐 key 比条数、再比金额，会漏掉
    「主播多一行、厅长少一行」——两个 key 都在，条数各自对不上但总额一样；
    整体比较时「多一条写路径」「某条路径条数不对」「金额有偏差」一次全露出来。

    乘法只作用在探针实测出来的值上，不写死比例、也不写死行数：厅配置从 71:6:3
    变成 80:0:0 只是探针值变了，不会红；红的只有「和探针不成比例」。

    success=0 时每个写路径都应放大成 [0, 0]：并发批次里若还有行，就是不相等，
    这正是「一笔都没成交却发了分成」要红的地方。

    入参也能是 flows_by_key 分出来的桶（自刷分支）——只要 key 带 op，乘法就不关心
    它到底是收款行还是付款行。
    """
    return {key: [count * success, amount * success]
            for key, (count, amount) in income_probe.items()}


def expected_rows(income_probe, pay_probe, success):
    """这批流水一共该有几行：探针实测的行数 × 成功笔数

    拿它当 wait_flows_stable 的 least（等待下界），不放宽断言：
    - 该写的都写了，行数一到位就能返回，不必靠「静默」去赌；
    - 真漏写时行数永远到不了，一直等到超时，再由调用方的行数断言判红。
    上一次那只红就是反例：期望 8 行、实际只读到 7 行，而旧判据只要求「至少 1 行 +
    静默」，在第 7 行就收工了。

    不写死行数（不按「一笔几行」猜）：行数来自探针，厅配置变了先变的是探针值。
    """
    probe_rows = sum(count for count, _ in income_probe.values()) + len(pay_probe)
    return probe_rows * success


def concurrent_window_tested(kinds_by_uid):
    """同账号连发多笔时，哪些账号是真的把每一笔都送到了业务校验

    频控（「请求太快了，请稍后重试」）在请求层就被挡下，那一笔根本没走到余额与幂等
    校验。四个账号的第二笔全被挡下时，「同账号重复提交」这个场景本轮一次都没验到
    ——而扣款侧仍然「各扣一笔、全对」，报告上是一条通过。这就是绿得毫无意义，
    必须让调用方转成未测到。实测 2026-10-29 的 test_003 就是这样绿的（4 次频控，
    每个账号各挡一笔）。

    返回没被限流的账号（顺序与传入一致）。空列表表示一对都没验到。
    """
    return [uid for uid, kinds in kinds_by_uid.items() if 'limited' not in kinds]


def is_success(res):
    """成功 = HTTP 200 且 body.success 为真

    body 不一定是 dict：网关拦截或后端 500 时 post_request_session 会把响应原文
    原样带回来，字符串上没有 .get，直接取会抛 AttributeError——用例会变成 ERROR，
    报告里成了一条「跑不起来」，而不是一条「服务端返回了异常响应」的失败。
    自检里的「非 dict body」场景就是钉这一条。
    """
    body = res.get('body')
    if not isinstance(body, dict):
        return False
    return res.get('code') == 200 and str(body.get('success')) in ('1', 'True')


def classify(res):
    """响应分成 成功 / 频控 / 业务拒绝 / 服务端异常

    并发场景下必须把「业务拒绝」与「服务端异常」分开：余额不足、防重、频控都会返回
    code=200 + success=False，它们是正常反馈，不能算 bug；真正能证明有问题的是
    「钱与响应对不上」（由守恒断言抓）和「服务端异常」（HTTP 非 200、空 body、没有 msg）。
    统一个「失败」只会把两者混在一起，要么放过真异常，要么把正常拒绝报成 bug。
    服务端拒绝时 msg 可能为空（实测同账号并发第二笔就是空 msg），不能靠 msg 判有无。
    """
    if is_success(res):
        return 'success'
    body = res.get('body')
    msg = str(body.get('msg', '')) if isinstance(body, dict) else ''
    if any(keyword in msg for keyword in FREQUENT_MSG_KEYWORDS):
        return 'limited'
    if res.get('code') != 200 or not isinstance(body, dict) or res.get('error'):
        return 'broken'
    return 'rejected'
