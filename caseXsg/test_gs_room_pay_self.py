# -*- encoding=utf8 -*-
__desc__ = "公会主播-房间打赏,自刷"

import random
import time
import unittest

from caseXsg.config import *
from caseXsg.tools import check_vip_pop, prepare_test_data, insert_package_gift
from common.Assert import assert_code, assert_equal, assert_body, assert_between
from common.Consts import case_list_b2, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conRedis import conRedis
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


def generate_random_rates():
	"""生成4个随机2位小数,合计=1"""
	r1 = round(random.uniform(0, 1), 2)
	r2 = round(random.uniform(0, 1 - r1), 2)
	r3 = round(random.uniform(0, 1 - r1 - r2), 2)
	r4 = round(1 - r1 - r2 - r3, 2)
	return r1, r2, r3, r4

@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	# def setUp(self):
	# 	if self._testMethodName in ("test_005","test_006","test_007","test_008"):
	# 		conRedis.set(f"Xs.Traveler.XSG.{payUid}", 1)
	#
	# def tearDown(self):
	# 	conRedis.delete(f"Xs.Traveler.XSG.{payUid}")
	def test_001(self, des='主播,商业房,自刷,非跨档,已配置<=总计96%,按配置分成(扣mcb到账mcb,扣其他到账mc)'):
		rate_money = 0.1
		rate_money_b = 0.2
		rate_money_cash_b = 0.3
		rate_money_cash = 0.4

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})

		mysql.updateMoneySql(
			gs_A_uid_1,
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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=gs_A_uid_1)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['A-工会']['room_1_config']['anchor_rate']
		owner_rate = rates['A-工会']['room_1_config']['owner_rate']
		broker_rate = rates['A-工会']['room_1_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', gs_A_uid_1), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))
		case_list_b2[des] = result

	def test_002(self, des='主播,商业房,自刷,非跨档,已配置>总计96%,兜底94%(扣mcb到账mcb,扣其他到账mcb'):
		rate_money, rate_money_b, rate_money_cash_b, rate_money_cash = generate_random_rates()

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_2
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})

		mysql.updateMoneySql(
			gs_A_uid_1,
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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=gs_A_uid_1)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['A-工会']['room_2_over_config']['anchor_rate']
		owner_rate = rates['A-工会']['room_2_over_config']['owner_rate']
		broker_rate = rates['A-工会']['room_2_over_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', gs_A_uid_1), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))
		case_list_b2[des] = result

	def test_003(self, des='主播,商业房,自刷,非跨档,未配置,兜底94%(扣mcb到账mcb,扣其他到账mc)'):
		rate_money, rate_money_b, rate_money_cash_b, rate_money_cash = generate_random_rates()

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_B_rid_1
		uid = gs_B_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_B_uid_1, gs_B_room_owner_1_uid, gs_B_ceo_uid, money=default_money, god_status={uid: 2})

		mysql.updateMoneySql(
			gs_B_uid_1,
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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=gs_B_uid_1)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['B-工会']['room_1_not_config']['anchor_rate']
		owner_rate = rates['B-工会']['room_1_not_config']['owner_rate']
		broker_rate = rates['B-工会']['room_1_not_config']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid_1, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid_1, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', gs_B_uid_1), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))
		case_list_b2[des] = result

	def test_004(self, des='主播,商业房,自刷,跨档,80%(扣mcb到账mcb,扣其他到账mc)'):
		rate_money, rate_money_b, rate_money_cash_b, rate_money_cash = generate_random_rates()

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_B_rid_1
		uid = gs_A_uid_1
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, money=default_money, god_status={uid: 2})

		mysql.updateMoneySql(
			gs_A_uid_1,
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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=gs_A_uid_1)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * default_num
		anchor_rate = rates['A-工会']['room_other']['anchor_rate']
		owner_rate = rates['A-工会']['room_other']['owner_rate']
		broker_rate = rates['A-工会']['room_other']['broker_rate']

		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))
		assert_between(mysql.selectUserInfoSql('sum_money', gs_A_uid_1), 0, base_amount * anchor_rate)

		# todo 房主和公会长 分成待定
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'), int(base_amount * owner_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), int(base_amount * owner_rate * gs_rate_money_base) + int(base_amount * owner_rate * rate_money_cash))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), int(base_amount * broker_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), int(base_amount * broker_rate * gs_rate_money_base) + int(base_amount * broker_rate * rate_money_cash))
		case_list_b2[des] = result

	def test_005(self, des='主播,商业房,打赏多人(含自己),非跨档,按照各自身份到账'):

		rate_money, rate_money_b, rate_money_cash_b, rate_money_cash = generate_random_rates()

		gs_rate_money_base = rate_money + rate_money_b

		rid = gs_A_rid_1

		uids = tuple([str(i) for i in [gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, gs_B_uid_1, normal_uid]])

		num = 10
		prepare_test_data(payUid, gs_A_uid_1, gs_A_room_owner_1_uid, gs_A_ceo_uid, gs_B_uid_1, normal_uid,
		                  money=0,
		                  god_status={gs_A_uid_1: 2, gs_A_room_owner_1_uid: 2,gs_A_ceo_uid: 2, gs_B_uid_1: 2,normal_uid: 0},
		                  clear_commodity=False)

		mysql.updateMoneySql(
			gs_A_uid_1,
			money=giftId['69']['price'] * rate_money * num * len(uids),
			money_b=giftId['69']['price'] * rate_money_b * num * len(uids),
			money_cash_b=giftId['69']['price'] * rate_money_cash_b * num * len(uids),
			money_cash=giftId['69']['price'] * rate_money_cash * num * len(uids)
		)

		data = encodeData(
			rid=rid,
			payType='package-more',
			num=num,
			uids=uids,
			display_page=1
		)
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=gs_A_uid_1)
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))

		# 按照扣款比例 分别增加,并向下取整
		base_amount = giftId['69']['price'] * num
		anchor_rate = rates['A-工会']['room_1_config']['anchor_rate']  # 0.81
		owner_rate = rates['A-工会']['room_1_config']['owner_rate']  # 0.09
		broker_rate = rates['A-工会']['room_1_config']['broker_rate']  # 0.06
		user_rate = rates['normal_uid']['room']['user_rate']
		room_other_rate = rates['B-工会']['room_other']['anchor_rate']
		# gs_A_uid_1 主播,非跨档
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash_b'), int(base_amount * anchor_rate * rate_money_cash_b))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid_1, money_type='money_cash'), int(base_amount * anchor_rate * gs_rate_money_base) + int(base_amount * anchor_rate * rate_money_cash))

		# gs_A_room_owner_1_uid 房主,非跨档
		# gs_A_room_owner_1_uid 作为 gs 收礼的分成 mc
		room_owner_as_gs_mc = int(base_amount * anchor_rate)
		# gs_A_room_owner_1_uid 作为 房主 收礼的分成 mcb 和 来自:自刷*1
		room_owner_as_owner_mcb = int(base_amount * owner_rate * rate_money_cash_b)
		# gs_A_room_owner_1_uid 作为 房主 收礼的分成合计 mc 和 来自:自刷*1+非自刷*2
		room_owner_as_owner_mc = (int(base_amount * owner_rate * gs_rate_money_base)+int(base_amount * owner_rate * rate_money_cash)) + int(base_amount * owner_rate)*2

		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash_b'),  room_owner_as_owner_mcb)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_room_owner_1_uid, money_type='money_cash'), room_owner_as_gs_mc + room_owner_as_owner_mc)

		# gs_A_ceo_uid 工会长,非跨档
		# gs_A_ceo_uid 作为 gs 收礼的分成合计 mc
		ceo_as_gs_mc = int(base_amount * anchor_rate)
		# gs_A_ceo_uid 作为 公会长 收礼的分成 mcb 和 来自:自刷*1
		ceo_as_ceo_mcb = int(base_amount * broker_rate * rate_money_cash_b)
		# gs_A_ceo_uid 作为 公会长 收礼的分成合计 mc 和 来自:自刷*1+非自刷*2
		ceo_as_ceo_mc = (int(base_amount * broker_rate * gs_rate_money_base)+int(base_amount * broker_rate * rate_money_cash)) + int(base_amount * broker_rate)*2
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash_b'), ceo_as_ceo_mcb)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_ceo_uid, money_type='money_cash'), ceo_as_gs_mc + ceo_as_ceo_mc)

		# gs_B_uid_1 主播,跨档
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid_1, money_type='money_cash_b'),int(base_amount * room_other_rate))

		# normal_uid 用户
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), int(base_amount * user_rate))

		case_list_b2[des] = result

	def test_006(self, des='个人房,主播打赏主播自己,90%(mcb)'):
		rid = mysql.selectUserInfoSql('vip',app_id=70)
		uid = gs_A_uid_1
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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=uid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),giftId['69']['price'] * default_num * rates['gs']['xsg-vip-room']['gs_self_rate'])
		case_list_b2[des] = result