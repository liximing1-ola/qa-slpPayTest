# -*- encoding=utf8 -*-
__author__ = "Wu.Zhenxing"
__title__ = ""
__desc__ = "用户-房间打赏"

import time
import unittest

from caseXsg.config import *
from caseXsg.tools import check_vip_pop, prepare_test_data, insert_package_gift
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result
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

	def test_001(self, des='非不夜-新用户,商业房,打赏普通用户,94%(mcb)'):
		rid = gs_A_rid_1
		uid = normal_uid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		prepare_test_data(payUid, normal_uid, money=default_money, god_status={uid: 0})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal_uid']['room']['user_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_002(self, des='不夜活跃-用户,商业房,打赏普通用户,94%(mcb)'):
		rid = gs_A_rid_1
		uid = normal_uid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		prepare_test_data(payUid, normal_uid, money=default_money, god_status={uid: 0})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal_uid']['room']['user_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_003(self, des='个人房,打赏普通用户,90%(mcb)'):
		rid = mysql.selectUserInfoSql('vip',app_id=70)
		uid = normal_uid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		mysql.updateUserMoneyClearSql(uid)
		mysql.updateMoneySql(payUid, giftId['69']['price']* default_num)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['normal_uid']['xsg-vip-room']['user_rate'])
		case_list_b2[des] = result

