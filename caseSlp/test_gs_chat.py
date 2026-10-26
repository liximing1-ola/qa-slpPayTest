# -*- encoding=utf8 -*-
__title__ = ""
__desc__ = "公会主播-私聊"

import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop, prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='主播GS-外显人气-私聊打赏分成90%(mcb)'):
		"""
		用例描述�?		主播GS-私聊打赏分成60%进mc
		脚本步骤�?		1.构造打赏者和被打赏者数�?		2.私聊一对一打赏流程(礼物:棒棒�?
		3.校验接口和返回值数�?        4.检查被打赏者余额和账户，预期为�?0 * 0.6 = 30(mc)
        5.检查打赏者余�?预期为：1000 - 50 = 950
		"""
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['pop']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_002(self, des='主播GS-外显vip-私聊打赏分成90%(mcb)'):
		"""
		用例描述�?		主播GS-私聊打赏分成60%进mc
		脚本步骤�?		1.构造打赏者和被打赏者数�?		2.私聊一对一打赏流程(礼物:棒棒�?
		3.校验接口和返回值数�?        4.检查被打赏者余额和账户，预期为�?0 * 0.6 = 30(mc)
        5.检查打赏者余�?预期为：1000 - 50 = 950
		"""
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 0})

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "vip"), True)

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['vip']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result