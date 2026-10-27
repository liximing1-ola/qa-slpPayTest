# -*- encoding=utf8 -*-
__desc__ = "公会主播-私聊"

import unittest

from caseXsg.config import *
from caseXsg.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conRedis import conRedis
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def setUp(self):
		if self._testMethodName == 'test_002':
			conRedis.set(f"Xs.Traveler.XSG.{payUid}", 1)

	def tearDown(self):
		conRedis.delete(f"Xs.Traveler.XSG.{payUid}")

	def test_001(self, des='非不夜-新用户,私聊,打赏主播,90%(mcb)'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['gs']['xsg-chat']['gs_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_002(self, des='不夜活跃-用户,私聊,打赏主播,60%(mc)'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['slp-chat']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_003(self, des='主播,私聊,自刷,90%(mcb)'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateUserMoneyClearSql(uid)
		mysql.updateMoneySql(uid, giftId['69']['price']* default_num)

		data = encodeData(
			payType='chat-gift',
			num=default_num,
			uid=uid,
			giftId=giftId['69']['gid'],
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['gs']['xsg-chat']['gs_self_rate'])
