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


def reset_payer(uid, amount):
    """余额只留 amount，其余渠道清零；背包也清空——渠道一多，扣款落在哪个字段就不确定了"""
    mysql.updateMoneySql(uid, money=amount)
    mysql.deleteUserAccountSql('user_commodity', uid)


def is_success(res):
    body = res.get('body') or {}
    return res.get('code') == 200 and str(body.get('success')) in ('1', 'True')


def classify(res):
    """响应分成 成功 / 频控 / 其它异常

    只有「其它异常」才是服务端 bug。频控是并发压在同一个 App 或同一个 IP 上的
    正常反馈，必须单独计数——它既不能混进失败被当成支付 bug，也不能被悄悄忽略，
    因为限流笔数决定了这一轮结果可不可信。
    """
    if is_success(res):
        return 'success'
    msg = str((res.get('body') or {}).get('msg', ''))
    if any(keyword in msg for keyword in FREQUENT_MSG_KEYWORDS):
        return 'limited'
    return 'broken'
