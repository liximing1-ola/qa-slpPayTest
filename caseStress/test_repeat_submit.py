# -*- encoding=utf8 -*-
__desc__ = "重复提交与幂等"

import os

# 与 test_pay_concurrent 同理：必须在 import common.Request 之前把间隔归零，
# 否则连发会被节流补足成 1 秒一笔，测的就不是"重发"而是"排队"
os.environ.setdefault('REQUEST_INTERVAL', '0')

import unittest

from caseStress.config import CONCURRENT_PAYERS, GIFT, PAY_AMOUNT, REPEAT_TIMES, ROOM_RID, pay_url
from caseStress.tools import classify, read_money, reset_payer
from common.Assert import assert_between, assert_equal_eventually
from common.Request import post_request_session
from common.Session import Session
from common.basicSlpXsgData import encodeData
from common.tools import get_test_token


class TestRepeatSubmit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 并发名单里有 gs_A_ceo_uid / normal_uid，Session.getSession 不备这两个账号的 token
        for uid, token in get_test_token(*CONCURRENT_PAYERS).items():
            Session.checkUserToken('write', app_name='slp', uid=uid, token=token)

    def test_001(self, des='同一请求连发 3 次(无幂等键): 账与响应严格对应, 重复成交只记录不判红'):
        uid = CONCURRENT_PAYERS[0]
        price = PAY_AMOUNT
        # 余额留够 N 笔：若只留一笔，"重复扣费"会被余额不足挡住而看不见
        reset_payer(uid, price * REPEAT_TIMES)
        before = read_money(uid)

        # 同一份请求体连发，等价于客户端超时后重发（encodeData 只算一次）
        data = encodeData(rid=ROOM_RID, payType='package', uid=uid, giftId=GIFT['gid'], display_page=1)
        responses = []
        for index in range(REPEAT_TIMES):
            res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
            responses.append(res)
            print('[重复提交] 第 {} 次: code={} body={}'.format(
                index + 1, res.get('code'), res.get('body')), flush=True)

        kinds = [classify(res) for res in responses]
        expect_deducted = kinds.count('success') * price
        try:
            # 余额可能异步落库：轮询到扣款额稳定，避免把「还没写库」误判成没扣钱
            assert_equal_eventually(lambda: before - read_money(uid), expect_deducted)
        finally:
            left = read_money(uid)
            print('[重复提交] {} 次提交: 成功 {} 笔, 频控 {} 笔, 异常 {} 笔; 扣款 {} (期望 {}, 单笔 {})，余额 {} -> {}'.format(
                REPEAT_TIMES, kinds.count('success'), kinds.count('limited'), kinds.count('broken'),
                before - left, expect_deducted, price, before, left), flush=True)

        # 余额不得为负：扣的钱比单笔多又不报错，就是超扣
        assert_between(left, 0, before)

        # 接口没有幂等键（请求体只有 sign + 业务字段），「重复提交几次算正常」属产品口径。
        # 口径确定前只显著记录现状、不判红——但成交笔数 > 1 时必须让它可见：
        # 客户端只要存在超时重发，这就是重复扣费。
        if kinds.count('success') > 1:
            print('[重复提交][待确认] 同一请求成交 {} 笔、扣款 {}：客户端若超时重发即为重复扣费，'
                  '需产品确认口径后固化成断言'.format(kinds.count('success'), before - left), flush=True)
