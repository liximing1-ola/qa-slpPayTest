# -*- encoding=utf8 -*-
__desc__ = "主播,自刷"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body, assert_between
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='主播,商业房,非跨档,自刷,按配置分成(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_1
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(uid, uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 1})

		mysql.updateMoneySql(
			uid,
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['A-工会']['room_1_config']['anchor_rate']
		owner_rate = rates['A-工会']['room_1_config']['owner_rate']
		broker_rate = rates['A-工会']['room_1_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', uid), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))

	def test_002(self, des='主播,商业房-非派单,跨档,自刷,上周厅存在,已配置<=总计80%,且主播>=60%,按跨档最高60%规则分成(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_B_rid_1
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(uid, uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 1})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_A_rid_1)
		mysql.updateMoneySql(
			uid,
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['other-broker-not-slporder']['last_week_room_1_config']['anchor_rate']
		owner_rate = rates['other-broker-not-slporder']['last_week_room_1_config']['owner_rate']
		broker_rate = rates['other-broker-not-slporder']['last_week_room_1_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', uid), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))

	def test_003(self, des='主播,商业房-派单,跨档,自刷,上周厅存在,已配置<=总计80%,按配置规则分成(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_B_rid_2
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(uid, uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 1})
		mysql.deleteXsstRoomacsSum(uid)
		mysql.insertXsstRoomacsSum(uid, gs_A_rid_1)
		mysql.updateMoneySql(
			uid,
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['A-工会']['room_1_config']['anchor_rate']
		owner_rate = rates['A-工会']['room_1_config']['owner_rate']
		broker_rate = rates['A-工会']['room_1_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', uid), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))

	def test_004(self, des='主播,商业房-派单,跨档,自刷,上周厅不存在,按特殊规则分成(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_B_rid_2
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(uid, uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 1})
		mysql.deleteXsstRoomacsSum(uid)

		mysql.updateMoneySql(
			uid,
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['other-broker-slporder']['last_week_room_none']['anchor_rate']
		owner_rate = rates['other-broker-slporder']['last_week_room_none']['owner_rate']
		broker_rate = rates['other-broker-slporder']['last_week_room_none']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', uid), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))

	def test_005(self, des='主播,个人房,自刷,90%(mcb)'):
		rid = mysql.selectUserInfoSql('vip')
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['gs']['vip-room-self'])

	def test_006(self, des='主播,靓号房,自刷,80%(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_A_ceo_pretty_rid
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(uid, uid,gs_A_room_owner_1_uid,gs_A_ceo_uid, money=default_money, god_status={uid: 1})

		mysql.updateMoneySql(
			uid,
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['gs']['vip-pretty-room-self']
		owner_rate = 0
		broker_rate = 0

		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', uid), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))

	def test_007(self, des='主播,私聊,自刷,90%(mcb)'):
		uid = gs_A_uid
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
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['gs']['chat-self'])
