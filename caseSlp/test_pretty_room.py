# -*- encoding=utf8 -*-
__title__ = ""
__desc__ = "个人靓号�?房间打赏"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result, case_list
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='靓号�?房间内打赏多�?gs+normal)多礼物场�?):
		"""
		用例描述�?		验证非直播类型房间内一对多打赏场景
		脚本步骤�?		1.构造打赏者和被打赏者数�?		2.房间内一对多打赏流程
		3.校验接口状态和返回值数�?		4.检查打赏者余�?预期为：20000-1000*6*3 = 2000
		5.检查被打赏者余额，预期为：1000*6*0.62 = 3720(非一代宗�? 1000*6*0.7=4200(一代宗�? 1000*6*0.62=3720（公会）
		"""
		rid = gs_A_ceo_pretty_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

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
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'), giftId['69']['price'] * rates['normal']['vip-pretty-room'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'), giftId['69']['price'] * rates['gs']['vip-pretty-room'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['69']['price'] * rates['normal']['vip-pretty-room'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), 0)
		case_list[des] = result