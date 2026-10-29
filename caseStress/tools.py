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


def wait_gift_flows(after_id, gid, least=1):
    """等流水落库：至少读到 least 行或超时，返回最后一次读到的全部行

    和余额一样，结算流水是异步写的：发完请求立刻查会读到空，或者只读到前几笔。
    超时也把已有结果返回，由调用方的断言去判断差多少。
    """
    deadline = time.time() + WAIT_TIMEOUT
    while True:
        rows = read_gift_flows(after_id, gid)
        if len(rows) >= least or time.time() >= deadline:
            return rows
        time.sleep(WAIT_INTERVAL)


def split_flows(rows):
    """把流水拆成收款行与付款行

    op='pay' 是付款方自己扣钱那一行，它和分成混在一起算会互相抵消。
    收款侧聚合成 {(uid, op): [行数, 金额合计]}，一个 key 就是一条写路径：
    三方分成就是三个 key，其中任何一个少写一笔都会在行数上露出来。
    """
    income, pay = {}, []
    for row in rows:
        if row['op'] == 'pay':
            pay.append(row)
            continue
        slot = income.setdefault((row['uid'], row['op']), [0, 0])
        slot[0] += 1
        slot[1] += int(row['money'] or 0)
    return income, pay


def is_success(res):
    body = res.get('body') or {}
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
