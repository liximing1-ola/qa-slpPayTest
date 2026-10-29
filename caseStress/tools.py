# -*- encoding=utf8 -*-
"""并发与幂等用例的公共动作：重置余额、读余额、给响应分类

两条用例共用这几个动作，口径必须一致——「频控算不算失败」的判断若在两个文件里
各写一遍，迟早会出现一个宽松一个严格，那时报告里的「并发异常 0 笔」就不可信了。
"""
from common.Request import FREQUENT_MSG_KEYWORDS
from common.conSlpXsgMysql import conMysql as mysql


def read_money(uid):
    """读 xs_user_money.money：并发用例只给 money 渠道放钱，对账口径才唯一"""
    return mysql.selectUserInfoSql('single_money', uid, money_type='money')


# 除主渠道外的其他钱包：余额不足时服务端可能回退到别的渠道扣款，
# 只读 money 会把「从别处扣了」看成「压根没扣」，对账就失去意义
WALLET_CHANNELS = ('money', 'money_b', 'money_cash', 'money_cash_b', 'gold_coin')


def read_wallets(uid):
    """读全部钱包渠道，只在失败现场打印用：轮询断言仍只看 money，避免多读 5 倍"""
    return {channel: mysql.selectUserInfoSql('single_money', uid, money_type=channel)
            for channel in WALLET_CHANNELS}


def read_income(uid):
    """收款方到账总额：money 系列全部累加，gold_coin 不算

    分成落在 money_cash 还是 money_cash_b，由「是否在工会、是否签署大神」决定，
    写死单个渠道会在配置变动时把「到账落别处」判成「没到账」；而总额守恒与落在
    哪个渠道无关。轮询时多读三个渠道的代价，远小于把一个渠道判断错。
    gold_coin 不计入：那是金币，不是人民币收入。
    """
    return sum(value for channel, value in read_wallets(uid).items()
               if channel.startswith('money'))


def read_sum_money(uid):
    """历史累计收益：只增不减的字段，用它做守恒对账比当前余额干净

    single_money 是当前余额，会被消费、转账、再打赏改掉；sum_money 是累计，
    只随分成增加。并发的「读-加-写」丢一次，余额可能被后一笔盖住看不出来，
    累计字段则永远少一部分——所以守恒断言优先压在它上面。

    另：公会长也在并发打赏名单里，但打赏只扣 money、不碰 sum_money，
    所以用这个字段对账时，不会和他自己花出去的钱糊在一起。
    """
    return mysql.selectUserInfoSql('sum_money', uid)


def reset_payer(uid, amount):
    """余额只留 amount，其余渠道清零；背包也清空——渠道一多，扣款落在哪个字段就不确定了"""
    mysql.updateMoneySql(uid, money=amount)
    mysql.deleteUserAccountSql('user_commodity', uid)


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
