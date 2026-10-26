# -*- encoding=utf8 -*-
__title__ = ""
__desc__ = "礼物优惠�?有损"

import time
import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop, prepare_test_data, insert_coupon
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b, result, case_list
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	@unittest.skip("""优惠�?不支持私�?"")
	def test_001(self, des='私聊,9折券(有损),打赏单个礼物'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['937']['price'] * num * rates['pop']['chat'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)
		case_list_b[des] = result

	@unittest.skip("""优惠�?不支持私�?"")
	def test_002(self, des='私聊,9折券(有损),打赏多个礼物'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['937']['price'] * 1 * rates['pop']['chat'] * (1 - commodityId['89297']['discount']) +
		             giftId['937']['price'] * (num - 1) * rates['pop']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * 1 * (1 - commodityId['89297']['discount']) -
		             giftId['937']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_003(self, des='房间,9折券(有损),打赏1个人单个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播�?		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['937']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['937']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_004(self, des='房间,9折券(有损),打赏1个人多个礼物'):
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播�?		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['937']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['937']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['937']['price'] * 1 * rates['gs']['default'] * (1 - commodityId['89297']['discount'])
		             + giftId['937']['price'] * (num - 1) * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * 1 * (1 - commodityId['89297']['discount'])
		             - giftId['937']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_005(self, des='房间,9折券(有损),打赏多个人单个礼�?):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

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
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['937']['price'] * rates['gs']['as_normal'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_006(self, des='房间,9折券(有损),打赏多个人多个礼�?):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

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
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['937']['price'] * rates['gs']['as_normal'] * 1 * (1 - commodityId['89297']['discount'])
		             + giftId['937']['price'] * rates['gs']['as_normal'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['937']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['937']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	@unittest.skip("""优惠�?不支持私�?"")
	def test_007(self, des='私聊,9折券(有损),打赏单个礼物,大额礼物,折扣无上�?):
		uid = gsUid
		default_money = 99999999
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['211026']['price'] * num * rates['pop']['chat'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	@unittest.skip("""优惠�?不支持私�?"")
	def test_008(self, des='私聊,9折券(有损),打赏多个礼物,大额礼物,折扣无上�?):
		uid = gsUid
		default_money = 99999999
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateUserMoneyClearSql(uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.updateUserGodSql(uid, 2)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['211026']['price'] * 1 * rates['pop']['chat'] * (1 - commodityId['89297']['discount']) +
		             giftId['211026']['price'] * (num - 1) * rates['pop']['chat'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * 1 * (1 - commodityId['89297']['discount']) -
		             giftId['211026']['price'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_009(self, des='房间,9折券(有损),打赏1个人单个礼物,大额礼物,折扣无上�?):
		rid = gs_B_rid
		default_money = 99999999
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播�?		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['211026']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', uid),
		             giftId['211026']['price'] * num * rates['gs']['default'] * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid),
		             default_money - giftId['211026']['price'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_010(self, des='房间,9折券(有损),打赏1个人多个礼物,大额礼物,折扣无上�?):
		rid = gs_B_rid
		default_money = 99999999
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播�?		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
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

		case_list_b[des] = result

	def test_011(self, des='房间,9折券(有损),打赏多个人单个礼�?大额礼物,折扣无上�?):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 1
		mysql.updateUserGodSql(gs_A_uid, 0)
		mysql.updateUserGodSql(gs_B_uid, 1)
		mysql.updateMoneySql(payUid, giftId['211026']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_A_uid, gs_B_uid, normal_uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['211026']['price'] * rates['gs']['as_normal'] * num * (1 - commodityId['89297']['discount']))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['211026']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['211026']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['211026']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result

	def test_012(self, des='房间,9折券(有损),打赏多个人多个礼�?大额礼物,折扣无上�?):
		rid = gs_B_ceo_rid
		uids = tuple([str(i) for i in [gs_A_uid, gs_B_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(gs_B_uid), True)  # 确认 uid是工会成�?		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员

		num = 10
		mysql.updateUserGodSql(gs_A_uid, 0)
		mysql.updateUserGodSql(gs_B_uid, 1)
		mysql.updateMoneySql(payUid, giftId['211026']['price'] * num * len(uids))
		mysql.updateUserMoneyClearSql(gs_A_uid, gs_B_uid, normal_uid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		# 插入9折优惠券
		mysql.insertXsUserCommodity(payUid, commodityId['89297']['cid'], 1)
		mysql.insertXsUserCouponUse(payUid, commodityId['89297']['cid'])
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=commodityId['89297']['cid']))
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
		assert_code(res['code'], 200)
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_A_uid, money_type='money_cash_b'),
		             giftId['211026']['price'] * rates['gs']['as_normal'] * 1 * (1 - commodityId['89297']['discount'])
		             + giftId['211026']['price'] * rates['gs']['as_normal'] * (num - 1))
		assert_equal(mysql.selectUserInfoSql('single_money', gs_B_uid, money_type='money_cash'),
		             giftId['211026']['price'] * rates['gs']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), giftId['211026']['price'] * rates['normal']['default'] * num)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), giftId['211026']['price'] * commodityId['89297']['discount'])
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89297']['cid']), 0)

		case_list_b[des] = result
