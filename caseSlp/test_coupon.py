# -*- encoding=utf8 -*-
__desc__ = "礼物优惠券-有损"

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
	def test_001(self, des='私聊,9折券(有损),打赏单个礼物,按9折成交,券已消耗'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
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
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 实测私聊打赏会用券：收礼方按 9 折后的实付金额分成，扣款也按 9 折
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['937']['price'] * num * rates['pop']['chat'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * num * (1 - commodityId['89297']['discount']))
		# 券被正常消耗
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_002(self, des='私聊,9折券(有损),打赏多个礼物,按9折成交,券已消耗'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
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
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 券只抵 1 个礼物、其余 9 个原价；分成异步分批（券抵那笔先到），用轮询
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['937']['price'] * 1 * rates['pop']['chat'] * (1 - commodityId['89297']['discount']) +
			giftId['937']['price'] * (num - 1) * rates['pop']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * 1 * (1 - commodityId['89297']['discount']) -
		             giftId['937']['price'] * (num - 1))
		# 券被正常消耗
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_003(self, des='房间,9折券(有损),打赏1个人单个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
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
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['937']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_004(self, des='房间,9折券(有损),打赏1个人多个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
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
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['937']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['937']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['937']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * 1 * (1 - commodityId['89297']['discount'])
		             - giftId['937']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_005(self, des='房间,9折券(有损),打赏多个人单个礼物'):
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
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['937']['price'] * rates['gs']['as_normal'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_006(self, des='房间,9折券(有损),打赏多个人多个礼物'):
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
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['937']['gid'],
			price=giftId['937']['price'],
			money=giftId['937']['price'] * num,
			cid=cid,
			duction_money=giftId['937']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 分成是分批异步写入的：实测约 0.9 秒才全部到齐，用券那个收礼人还会拆成两笔
		# （券抵的那 1 个礼物先到、剩余 9 个稍后到），固定睡一觉再读容易撞在中间态上
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['gs']['as_normal'] * 1 * (1 - commodityId['89297']['discount'])
			+ giftId['937']['price'] * rates['gs']['as_normal'] * (num - 1))
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
			giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
			giftId['937']['price'] * rates['normal']['default'] * num)
		# 扣款是同步的：请求返回时打赏者余额就已扣好，不需要轮询
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_007(self, des='私聊,9折券(有损),打赏单个礼物,大额礼物,按9折成交,折扣无上限'):
		uid = gsUid
		default_money = 99999999
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
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
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 1314000 钻的大额礼物同样打 9 折：折扣无上限，券正常消耗
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['211026']['price'] * num * rates['pop']['chat'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_008(self, des='私聊,9折券(有损),打赏多个礼物,大额礼物,按9折成交,折扣无上限'):
		uid = gsUid
		default_money = 99999999
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		num = 10

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
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 券只抵 1 个 1314000 钻礼物、其余 9 个原价；分成异步分批，用轮询
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
			giftId['211026']['price'] * 1 * rates['pop']['chat'] * (1 - commodityId['89297']['discount']) +
			giftId['211026']['price'] * (num - 1) * rates['pop']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * 1 * (1 - commodityId['89297']['discount']) -
		             giftId['211026']['price'] * (num - 1))
		# 券被正常消耗
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_009(self, des='房间,9折券(有损),打赏1个人单个礼物,大额礼物,折扣无上限'):
		rid = gs_B_rid
		default_money = 99999999
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		num = 1
		uids = tuple([str(i) for i in [uid]])
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			uids=uids,
			num=num,
			giftId=giftId['211026']['gid'],
			price=giftId['211026']['price'],
			money=giftId['211026']['price'] * num,
			cid=cid,
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['211026']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['211026']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_010(self, des='房间,9折券(有损),打赏1个人多个礼物,大额礼物,折扣无上限'):
		rid = gs_B_rid
		default_money = 99999999
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		num = 10
		uids = tuple([str(i) for i in [uid]])
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			uids=uids,
			num=num,
			giftId=giftId['211026']['gid'],
			price=giftId['211026']['price'],
			money=giftId['211026']['price'] * num,
			cid=cid,
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['211026']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['211026']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['211026']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['211026']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * 1 * (1 - commodityId['89297']['discount'])
		             - giftId['211026']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_011(self, des='房间,9折券(有损),打赏多个人单个礼物,大额礼物,折扣无上限'):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 1
		mysql.updateUserGodSql(gs_A_uid, 0)
		mysql.updateUserGodSql(gs_B_uid, 1)
		mysql.updateMoneySql(payUid, giftId['211026']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_A_uid, gs_B_uid, normal_uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['211026']['gid'],
			price=giftId['211026']['price'],
			money=giftId['211026']['price'] * num,
			cid=cid,
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['211026']['price'] * rates['gs']['as_normal'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['211026']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['211026']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['211026']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

	def test_012(self, des='房间,9折券(有损),打赏多个人多个礼物,大额礼物,折扣无上限'):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成员
		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 10
		mysql.updateUserGodSql(gs_A_uid, 0)
		mysql.updateUserGodSql(gs_B_uid, 1)
		mysql.updateMoneySql(payUid, giftId['211026']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_A_uid, gs_B_uid, normal_uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89297']['cid'], 1)
		data = encodeData(
			payType='room-coupon',
			rid=rid,
			num=num,
			uids=uids,
			giftId=giftId['211026']['gid'],
			price=giftId['211026']['price'],
			money=giftId['211026']['price'] * num,
			cid=cid,
			duction_money=giftId['211026']['price'] * commodityId['89297']['discount']

		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		# 分成异步分批写入（同 test_006）：每人 10 个礼物要等约 1 秒才全部到齐，用券那个收礼人还拆成两笔
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
			giftId['211026']['price'] * rates['gs']['as_normal'] * 1 * (1 - commodityId['89297']['discount'])
			+ giftId['211026']['price'] * rates['gs']['as_normal'] * (num - 1))
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
			giftId['211026']['price'] * rates['gs']['default'] * num)
		assert_equal_eventually(
			lambda: mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
			giftId['211026']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['211026']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)
