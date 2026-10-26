# -*- encoding=utf8 -*-
__desc__ = "普通用户-私聊"

import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop, prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='普通用户-私聊打赏分成90%(mcb)'):
		"""
		用例描述：
		普通用户-私聊打赏分成60%(mcb)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.私聊一对一打赏流程(礼物:棒棒糖)
		3.校验接口和返回值数据
        4.检查被打赏者余额和账户，预期为：50 * 0.6 = 30(mcb)
        5.检查打赏者余额.预期为：1000 - 50 = 950
		"""
		uid = rewardUid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid不是工会成员
		prepare_test_data(payUid, normal_uid, money=default_money)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(normal_uid, "vip"), True)

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['vip']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['69']['price'] * default_num)
		case_list[des] = result
