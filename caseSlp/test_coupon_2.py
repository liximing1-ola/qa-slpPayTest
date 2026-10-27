# -*- encoding=utf8 -*-
__desc__ = "礼物优惠券-无损-收礼方不打折"  # 无损券 无私聊场景

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data, insert_coupon
from common.Assert import assert_equal, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_003(self, des='房间,9折券(无损),打赏1个人单个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 1
		uids = tuple([str(i) for i in [uid]])
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			uids=uids,
			num=num,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * num * 0.9)
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

	def test_004(self, des='房间,9折券(无损),打赏1个人多个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 10
		uids = tuple([str(i) for i in [uid]])
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			uids=uids,
			num=num,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * 1 * 0.9
		             - giftId['937']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

	def test_005(self, des='房间,9折券(无损),打赏多个人单个礼物'):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 1
		prepare_test_data(payUid, gs_A_uid, gs_B_uid, normal_uid,
		                  money=giftId['937']['price'] * num * len(uids),
		                  god_status={gs_A_uid: 0, gs_B_uid: 1})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['gs']['as_normal'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89370']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

	def test_006(self, des='房间,9折券(无损),打赏多个人多个礼物'):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 10
		prepare_test_data(payUid, gs_A_uid, gs_B_uid, normal_uid,
		                  money=giftId['937']['price'] * num * len(uids),
		                  god_status={gs_A_uid: 0, gs_B_uid: 1})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['gs']['as_normal'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89370']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)
