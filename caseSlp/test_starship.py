# -*- encoding=utf8 -*-
__desc__ = "星舰相关"

import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result, case_list
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	@unittest.skip("""群组定期解散,不维护了""")
	def test_001(self, des='星舰房-房间内打赏多人(gs(人气)-90%+gs(vip)-90%+normal-90%)多礼物场景(mcb)'):
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
		rid = gs_A_ceo_starship_rid
		uids = tuple([str(i) for i in [gs_B_uid, gs_A_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 5
		mysql.updateUserGodSql(gs_B_uid, 1)
		mysql.updateUserGodSql(gs_A_uid, 0)
		mysql.updateMoneySql(payUid, giftId['69']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_B_uid, gs_A_uid, normal_uid)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(gs_B_uid, "pop"), True)
		assert_equal(check_vip_pop(gs_A_uid, "vip"), True)
		assert_equal(check_vip_pop(normal_uid, "vip"), True)

		data = encodeData(
			rid=rid,
			payType='package-more',
			num=num,
			uids=uids
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['pop']['starship-room'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['vip']['starship-room'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['vip']['starship-room'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), 0)
		case_list[des] = result

	@unittest.skip("""群组定期解散,不维护了""")
	def test_002(self, des='星舰群聊内,打赏多人(gs(人气)-910%+gs(vip)-90%+normal-90%)多礼物场景(mcb)'):
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
		group_id = gs_A_ceo_starship_group_id

		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 5
		mysql.updateUserGodSql(gs_A_uid, 1)
		mysql.updateUserGodSql(gs_B_uid, 0)
		mysql.updateMoneySql(payUid, giftId['69']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_A_uid, gs_B_uid, normal_uid)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(gs_A_uid, "pop"), True)
		assert_equal(check_vip_pop(gs_B_uid, "vip"), True)
		assert_equal(check_vip_pop(normal_uid, "vip"), True)

		data = encodeData(
			payType='starship-im',
			num=num,
			uids=uids,
			group_id=group_id
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['pop']['starship-im'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['vip']['starship-im'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
		             giftId['69']['price'] * rates['vip']['starship-im'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), 0)
		case_list[des] = result
