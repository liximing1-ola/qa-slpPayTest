# -*- encoding=utf8 -*-
__desc__ = "用户,自刷"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_between, assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='用户,商业房,自刷,80%(扣mc到账mc,扣其他到账mcb)'):
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		
		base_amount = giftId['69']['price'] * default_num
		user_rate = rates['normal']['room-self']
		
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash_b'), int(base_amount * user_rate * normal_rate_money_base) + int(base_amount * user_rate * rate_money_cash_b))
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', payUid, money_type='money_cash'), int(base_amount * user_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', payUid), 0, int(base_amount * user_rate))

	def test_002(self, des='用户,个人房,自刷,90%(mcb)'):
		rid = mysql.selectUserInfoSql('vip')
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal']['vip-room-self'])

	def test_003(self, des='用户,靓号房,自刷,90%(mcb)'):
		rid = gs_A_ceo_pretty_rid
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal']['vip-pretty-room-self'])

	def test_004(self, des='用户,私聊,自刷,90%(mcb)'):
		uid = payUid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		mysql.updateUserMoneyClearSql(uid)
		mysql.updateMoneySql(uid, giftId['69']['price']* default_num)

		data = encodeData(
			payType='chat-gift',
			num=default_num,
			uid=uid,
			giftId=giftId['69']['gid'],
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal']['chat-self'])
