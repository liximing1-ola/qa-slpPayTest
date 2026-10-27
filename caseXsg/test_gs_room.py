# -*- encoding=utf8 -*-
__desc__ = "公会主播-房间打赏"

import unittest

from caseXsg.config import *
from caseXsg.tools import prepare_test_data
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
		if self._testMethodName in ("test_005","test_006","test_007","test_008"):
			conRedis.set(f"Xs.Traveler.XSG.{payUid}", 1)

	def tearDown(self):
		conRedis.delete(f"Xs.Traveler.XSG.{payUid}")
	def test_001(self, des='非不夜-新用户,商业房,非跨档,已配置<=总计96%,按配置分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result
	def test_002(self, des='非不夜-新用户,商业房,非跨档,已配置>总计96%,兜底94%(mc)'):

		rid = gs_A_rid_2
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_2_over_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_2_over_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_2_over_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result
	def test_003(self, des='非不夜-新用户,商业房,非跨档,未配置,兜底94%(mc)'):

		rid = gs_B_rid_1
		uid = gs_B_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_B_uid_1, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['B-工会']['room_1_not_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['B-工会']['room_1_not_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['B-工会']['room_1_not_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result
	def test_004(self, des='非不夜-新用户,商业房,跨档,80%(mcb)'):

		rid = gs_B_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['A-工会']['room_other']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['A-工会']['room_other']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['A-工会']['room_other']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_005(self, des='不夜活跃-用户,商业房,非跨档,已配置<=总计96%,60%(mc)'):

		rid = gs_A_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_006(self, des='不夜活跃-用户,商业房,非跨档,已配置>总计96%,主播50%(mc),公会长10%(mc)'):

		rid = gs_A_rid_2
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_007(self, des='不夜活跃-用户,商业房,非跨档,未配置,主播50%(mc),公会长10%(mc)'):

		rid = gs_B_rid_1
		uid = gs_B_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_B_uid_1, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_008(self, des='不夜活跃-用户,商业房,跨档,主播50%(mc),公会长10%(mc)'):

		rid = gs_B_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['gs']['slp-room']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_009(self, des='个人房,打赏主播,90%(mcb)'):
		rid = mysql.selectUserInfoSql('vip',app_id=70)
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
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
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['gs']['xsg-vip-room']['gs_rate'])
		case_list_b2[des] = result

