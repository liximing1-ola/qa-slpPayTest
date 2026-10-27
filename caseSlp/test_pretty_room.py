# -*- encoding=utf8 -*-
__desc__ = "个人靓号房-房间打赏"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='靓号房-房间内打赏多人(gs+normal)多礼物场景'):
		"""
		用例描述：
		验证非直播类型房间内一对多打赏场景
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间内一对多打赏流程
		3.校验接口状态和返回值数据
		4.检查打赏者余额,预期为：20000-1000*6*3 = 2000
		5.检查被打赏者余额，预期为：1000*6*0.62 = 3720(非一代宗师) 1000*6*0.7=4200(一代宗师) 1000*6*0.62=3720（公会）
		"""
		rid = gs_A_ceo_pretty_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 5
		prepare_test_data(payUid, gs_A_uid, gs_B_uid, normal_uid,
		                  money=giftId['69']['price'] * num * len(uids),
		                  god_status={gs_A_uid: 0, gs_B_uid: 1},
		                  clear_commodity=False)
		data = encodeData(
			rid=rid,
			payType='package-more',
			num=num,
			uids=uids
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'), giftId['69']['price'] * rates['normal']['vip-pretty-room'] * num)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'), giftId['69']['price'] * rates['gs']['vip-pretty-room'] * num)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['69']['price'] * rates['normal']['vip-pretty-room'] * num)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), 0)