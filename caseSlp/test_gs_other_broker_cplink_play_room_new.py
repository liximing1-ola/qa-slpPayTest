# -*- encoding=utf8 -*-
__desc__ = "跨档-连连�?踢保(拍卖)-主播分成"

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
	def test_001(self, des='主播,商业�?连连�?跨档,按所在厅配置分成,已配�?=总计80%,按配置规则分�?mc)'):

		rid = gs_A_rid_6
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_6_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_6_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_6_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)

		case_list_b2[des] = result

	def test_002(self, des='主播,商业�?踢保(拍卖),跨档,按所在厅配置分成,已配�?=总计80%,按配置规则分�?mc)'):

		rid = gs_A_rid_7
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_7_config']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_7_config']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['A-工会']['room_7_config']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)

		case_list_b2[des] = result

	def test_003(self, des='主播,商业�?连连�?跨档,按所在厅配置分成,已配�?总计80%,基础规则兜底(mc)'):

		rid = gs_A_rid_10
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)
		case_list_b2[des] = result

	def test_004(self, des='主播,商业�?踢保(拍卖),跨档,按所在厅配置分成,已配�?总计80%,基础规则兜底(mc)'):

		rid = gs_A_rid_11
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['base_config']['base']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)
		case_list_b2[des] = result

	def test_005(self, des='主播,商业�?连连�?跨档,按所在厅配置分成,连连�?未配�?按结算频�?规则分成(mc)'):

		rid = gs_A_rid_8
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['cplink']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['cplink']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['cplink']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)
		case_list_b2[des] = result

	def test_006(self, des='主播,商业�?踢保(拍卖),跨档,按所在厅配置分成,踢保(拍卖),未配�?按结算频�?规则分成(mc)'):

		rid = gs_A_rid_8
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, gs_B_room_owner_1_uid, gs_B_ceo_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 2})
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
		# �?gs_B_uid,gs_A_room_owner_1_uid,gs_A_ceo_uid 分成
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['play']['anchor_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['play']['owner_rate'])
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'),giftId['69']['price'] * default_num * rates['settlement_channel_config']['play']['broker_rate'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)
		# gs_B_room_owner_1_uid,gs_B_ceo_uid 不分�?		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_room_owner_1_uid, money_type='money_cash'),0)
		assert_equal(mysql.selectUserInfoSql('sum_money', gs_B_ceo_uid, money_type='money_cash'),0)
		case_list_b2[des] = result