# -*- encoding=utf8 -*-
__desc__ = "用户-房间打赏,自刷"

import unittest

from caseXsg.config import *
from caseXsg.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body, assert_between
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conRedis import conRedis
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	def setUp(self):
		if self._testMethodName == "test_002":
			conRedis.set(f"Xs.Traveler.XSG.{payUid}", 1)

	def tearDown(self):
		conRedis.delete(f"Xs.Traveler.XSG.{payUid}")

	def test_001(self, des='非不夜-新用户,商业房,打赏自己,94%(扣mc到账mc,扣其他到账mcb)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		normal_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_1
		uid = payUid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		prepare_test_data(payUid, normal_uid, money=default_money, god_status={uid: 0})

		mysql.updateMoneySql(
			payUid,
			money=giftId['69']['price'] * rate_money,
			money_b=giftId['69']['price'] * rate_money_b,
			money_cash_b=giftId['69']['price'] * rate_money_cash_b,
			money_cash=giftId['69']['price'] * rate_money_cash
		)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		
		base_amount = giftId['69']['price'] * default_num
		user_rate = rates['normal_uid']['room']['user_self_rate']
		
		assert_equal(mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash_b'), int(base_amount * user_rate * normal_rate_money_base) + int(base_amount * user_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash'), int(base_amount * user_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', payUid), 0, int(base_amount * user_rate))

	def test_002(self, des='不夜活跃-用户,商业房,打赏自己,94%(扣mc到账mc,扣其他到账mcb)'):
		rate_money = 0
		rate_money_b = 0
		rate_money_cash_b = 0.71
		rate_money_cash = 0.29

		normal_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_1
		uid = payUid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		prepare_test_data(payUid, normal_uid, money=default_money, god_status={uid: 0})

		mysql.updateMoneySql(
			payUid,
			money=giftId['69']['price'] * rate_money,
			money_b=giftId['69']['price'] * rate_money_b,
			money_cash_b=giftId['69']['price'] * rate_money_cash_b,
			money_cash=giftId['69']['price'] * rate_money_cash
		)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		
		base_amount = giftId['69']['price'] * default_num
		user_rate = rates['normal_uid']['room']['user_self_rate']
		
		assert_equal(mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash_b'), int(base_amount * user_rate * normal_rate_money_base) + int(base_amount * user_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash'), int(base_amount * user_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', payUid), 0, int(base_amount * user_rate))

	def test_003(self, des='个人房,普通用户打赏普通用户自己,94%(mcb)'):
		rid = mysql.selectUserInfoSql('vip',app_id=70)
		uid = payUid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		mysql.updateUserMoneyClearSql(uid)
		mysql.updateMoneySql(uid, giftId['69']['price']* default_num)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal_uid']['xsg-vip-room']['user_self_rate'])