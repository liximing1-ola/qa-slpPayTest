# -*- encoding=utf8 -*-
__desc__ = "跨档-非派单-主播分成"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	def test_001(self, des='用户,商业房-非派单,跨档,上周厅存在,已配置<=总计80%,且主播>=60%,按跨档最高60%规则分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_B_rid_1)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_1_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_1_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_1_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_002(self, des='用户,商业房-非派单,跨档,上周厅存在,已配置<=总计80%,且主播<60%,按配置规则分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_B_rid_2)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_2_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_2_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['other-broker-not-slporder']['last_week_room_2_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_003(self, des='用户,商业房-非派单,跨档,上周厅存在,已配置>总计80%,基础规则兜底(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_B_rid_3)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_004(self, des='用户,商业房-非派单,跨档,上周厅存在,点唱,未配置,结算频道规则>跨档最高60%限制,按跨档最高60%规则分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_B_rid_4)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_005(self, des='用户,商业房-非派单,跨档,上周厅存在,树洞,未配置,按未配置的结算频道兜底分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_B_rid_5)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['other']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_006(self, des='用户,商业房-非派单,跨档,上周厅不存在,按基础规则兜底分成(mc)'):

		rid = gs_A_rid_1
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})
		mysql.deleteXsstRoomacsSum(uid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)