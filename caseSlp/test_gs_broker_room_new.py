# -*- encoding=utf8 -*-
__desc__ = "非跨档主播分�?

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
	def test_001(self, des='用户,商业�?非跨�?已配�?=总计80%,按配置分�?mc)'):

		rid = gs_A_rid_1
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, gs_A_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_1_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_002(self, des='用户,商业�?非跨�?已配�?总计80%,按基础规则-兜底分成(mc)'):

		rid = gs_A_rid_3
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, gs_A_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_003(self, des='用户,商业�?非跨�?点唱,未配�?按结算频�?规则分成(mc)'):

		rid = gs_A_rid_4
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, gs_A_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data,    tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['music']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['music']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['music']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result

	def test_004(self, des='用户,商业�?非跨�?树洞,未配�?按未配置的结算频道兜底分�?mc)'):

		rid = gs_A_rid_5
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, gs_A_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		case_list_b2[des] = result
