# -*- encoding=utf8 -*-
__desc__ = "礼物优惠券-无损-收礼方不打折"
#
# 「有损 / 无损」不是独立的配置项，而是由券商品的 coupon_type 决定的（xs_commodity.coupon_type）：
#   89297  9折礼物优惠券  coupon_type=gift_discount      折扣额平台直接减免，
#                                                     收礼方按实付分成 → 有损（见 test_coupon.py）
#   89370  9折礼物优惠券  coupon_type=pro_gift_discount  折扣额平台补贴，
#                                                     收礼方按原价分成 → 无损（本模块）
# 两种券的 extra.coupon_gifts 可用礼物也不同：89297 含 211026，89370 只有
# "937,1217,1407,1408"，所以本模块只能用 937，用 211026 会被券白名单挡掉。
#
# pro_gift_discount 目前只接入了房间链路，私聊（chat-coupon）会被服务端拒单，
# 所以本模块是「房间正向用例 + 一条私聊负向用例（test_001）」。

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data, insert_coupon
from common.Assert import assert_body, assert_between, assert_code, assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='私聊,9折券(无损/pro券),不支持,校验拒单且数据不变'):
		"""pro_gift_discount 目前只接入了房间链路，私聊（chat-coupon）会被拒单。

		这条是负向契约：等私聊接入 pro 券后 success 会变成 1，这条就会亮红，
		那时应该照着房间用例改成正向断言（收礼方按原价分成），而不是把预期放宽。
		"""
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		# 插入9折优惠券
		cid = insert_coupon(payUid, commodityId['89370']['cid'], 1)
		num = 1

		# 拒单前提：券确实在背包里，余额也足够——“余额不足”的解释站不住脚就在于此
		coupon_num = mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid'])
		assert_between(coupon_num, 1, 999)
		payUid_old_money = mysql.selectUserInfoSql('sum_money', payUid)
		uid_old_money = mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b')

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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 0, reason(des, res))
		# 不校 msg：现在回的是「余额不足，无法支付~~」，但余额 100 万、礼物才 600，
		# 真实原因是券类型不支持私聊，这个文案是误导，等开发修正后再补文案断言
		# 被拒后打赏者分文未扣（“拒单却扣了钱”会在这里亮红）
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), payUid_old_money)
		# 收礼方没有分成（如果链路走到了结算，无损券按原价应该是 540）
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'), uid_old_money)
		# 券没被吃掉：拒单却核销券同样是缺陷
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), coupon_num)

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
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', uid), giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * num * (1 - commodityId['89370']['discount']))
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

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
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', uid), giftId['937']['price'] * num * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['937']['price'] * 1 * (1 - commodityId['89370']['discount'])
		                        - giftId['937']['price'] * (num - 1))
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

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
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89370']['discount'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)

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
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), giftId['937']['price'] * commodityId['89370']['discount'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=commodityId['89370']['cid']), 0)
