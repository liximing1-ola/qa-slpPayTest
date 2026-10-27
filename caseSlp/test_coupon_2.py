# -*- encoding=utf8 -*-
__desc__ = "礼物优惠券-无损-收礼方不打折"  # 无损券：收礼方按礼物原价分成，券只影响打赏者扣款

import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop, prepare_test_data, insert_coupon
from common.Assert import assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='私聊,9折券(无损),打赏单个礼物,收礼方按原价分成'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 1

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			payType='chat-coupon',
			num=num,
			uid=uid,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 无损：分成按礼物原价算，券只影响打赏者扣款（不能乘 1-discount）
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['937']['price'] * num * rates['pop']['chat'])
		# 扣款按实付，与券核销同在服务端消费阶段完成，用轮询
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('sum_money', payUid),
			default_money - giftId['937']['price'] * num * (1 - commodityId['89370']['discount']))
		# 券被正常消耗
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

	def test_002(self, des='私聊,9折券(无损),打赏多个礼物,收礼方按原价分成'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 10

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			payType='chat-coupon',
			num=num,
			uid=uid,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89370']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 无损的关键：券只抵 1 件、但分成不打折，10 件全按原价 —— 与有损用例的差异就在这一行
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['937']['price'] * num * rates['pop']['chat'])
		# 扣款按实付：券只抵 1 件，其余 9 件原价
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('sum_money', payUid),
			default_money - giftId['937']['price'] * 1 * (1 - commodityId['89370']['discount']) -
			giftId['937']['price'] * (num - 1))
		# 券被正常消耗
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

	def test_007(self, des='私聊,9折券(无损),打赏单个礼物,大额礼物,收礼方按原价分成'):
		uid = gsUid
		default_money = 99999999
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 1

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			payType='chat-coupon',
			num=num,
			uid=uid,
			giftId=giftId['211026']['gid'],
			price=giftId['211026']['price'],
			money=giftId['211026']['price'] * num,
			cid=cid,
			duction_money=giftId['211026']['price'] * commodityId['89370']['discount']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 1314000 钻的大额礼物：抵扣额不封顶（扣 131400），但分成仍是原价、不打折
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['211026']['price'] * num * rates['pop']['chat'])
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('sum_money', payUid),
			default_money - giftId['211026']['price'] * num * (1 - commodityId['89370']['discount']))
		# 券被正常消耗
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

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
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * num * (1 - commodityId['89370']['discount']))
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
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * 1 * (1 - commodityId['89370']['discount'])
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
		# 无损：分成按礼物原价算，券只影响扣款。多人分批异步落库，用轮询
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['gs']['as_normal'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
			giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['normal']['default'] * num)
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
		# 无损：分成按礼物原价算（用券那个收礼人也不打折），用券的分成会单独拆一批写入，用轮询
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['gs']['as_normal'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
			giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89370']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)
