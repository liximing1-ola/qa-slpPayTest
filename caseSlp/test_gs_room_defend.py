# -*- encoding=utf8 -*-
__desc__ = "公会主播-房间守护"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry

@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='商业房-直播,开通房间守护给GS收60%（mc）'):
		"""
		 用例描述：
		商业房-直播,开通房间守护给GS收60%（mc）
		 脚本步骤：
		 1.构造开通者和被守护者数据
		 2.开通真爱守护 月
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查公会长余额，预期为： 0(不分成)
		 6.检查被打赏者余额.预期为：99900 * 0.6 = 59940
		 """
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房

		# test_uid = self.live_role['pack_cal_uid']
		# ceo_uid = self.live_role['pack_ceo']
		# mysql.updateUserInfoSql('chatroom', test_uid)  # 商业房房主
		# mysql.updateUserInfoSql('broker_user', test_uid, ceo_uid)  # 打包结算
		# mysql.checkUserXsBroker(ceo_uid)  # 公会长
		prepare_test_data(payUid, uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2, gs_A_ceo_uid: 1})
		data = encodeData(
			payType='package-knightDefend',
			money=room_defend['zhenai']['month']['price'],
			uid=uid,
			rid=rid,
			knight_level=room_defend['zhenai']['month']['knight_level'],
			duration_level=room_defend['zhenai']['month']['duration_level'],
			price=room_defend['zhenai']['month']['price'],
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - room_defend['zhenai']['month']['price'])
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             room_defend['zhenai']['month']['price'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_A_ceo_uid), 0)
		case_list_b2[des] = result
