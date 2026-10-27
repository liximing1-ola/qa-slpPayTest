# -*- encoding=utf8 -*-
__desc__ = "公会主播-房间打赏"

import time
import unittest

from caseSlp.config import *
from caseSlp.tools import check_vip_pop, prepare_test_data, insert_package_gift
from common.Assert import assert_equal, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='商业房-直播,礼物打赏GS到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_002(self, des='商业房-直播,房间私聊打赏GS到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房房间私聊打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_003(self, des='商业房-直播,背包礼物打赏GS到账60%(mc)'):
		"""
		用例描述：
		商业房-直播,背包礼物打赏GS到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		cid = insert_package_gift(payUid, cid=giftId['69']['cid'], num=default_num)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			package_cid=cid,
			ctype='gift'
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)  # 不扣费
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=giftId['69']['cid']), 0)

	def test_004(self, des='商业房-非直播,礼物打赏GS到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房-非直播打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_friend_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_005(self, des='商业房-非直播,房间私聊打赏GS到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房-非直播房间私聊打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_friend_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_006(self, des='商业房-非直播,背包礼物打赏GS到账60%(mc)'):
		"""
		用例描述：
		商业房-非直播,背包礼物打赏GS到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_friend_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		cid = insert_package_gift(payUid, cid=giftId['69']['cid'], num=default_num)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			package_cid=cid,
			ctype='gift'
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)  # 不扣费
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=giftId['69']['cid']), 0)

	def test_007(self, des='个人房,外显人气-礼物打赏GS到账90%(mcb)'):
		"""
		用例描述：
		验证余额足够时，个人房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_008(self, des='个人房,外显人气-房间私聊打赏GS到账90%(mcb)'):
		"""
		用例描述：
		验证余额足够时，个人房房间私聊打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_009(self, des='个人房,外显人气-背包礼物打赏GS到账90%(mcb)'):
		"""
		用例描述：
		个人房,背包礼物打赏GS到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		cid = insert_package_gift(payUid, cid=giftId['69']['cid'], num=default_num)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "pop"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			package_cid=cid,
			ctype='gift'
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['pop']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)  # 不扣费
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=giftId['69']['cid']), 0)

	def test_010(self, des='商业房-直播,礼物打赏GS(签署大神且是房主),到账60%(mc)'):
		"""
		用例描述：
		商业房-直播,礼物打赏GS(签署大神且是房主),到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_A_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_011(self, des='商业房-直播,礼物打赏GS(签署大神且非房主),到账60%(mc)'):
		"""
		用例描述：
		商业房-直播,礼物打赏GS(签署大神且非房主),到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_A_ceo_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_012(self, des='商业房-直播,礼物打赏GS(不签署大神且是房主),到账60%(mcb)'):
		"""
		用例描述：
		商业房-直播,礼物打赏GS(不签署大神且是房主),到账60%(mcb)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_A_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_013(self, des='商业房-直播,礼物打赏GS(不签署大神且非房主),到账60%(mcb)'):
		"""
		用例描述：
		商业房-直播,礼物打赏GS(不签署大神且非房主),到账60%(mcb)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_A_ceo_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_014(self, des='商业房-非直播,礼物打赏GS(签署大神且是房主)到账60%(mc)'):
		"""
		用例描述：
		商业房-非直播,礼物打赏GS(签署大神且是房主)到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_015(self, des='商业房-非直播,房间私聊打赏GS(签署大神且非房主)到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房-非直播房间私聊打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_B_ceo_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_016(self, des='***商业房-非直播,礼物打赏GS(不签署大神且是房主)到账80%(mcb)'):
		"""
		用例描述：
		商业房-非直播,礼物打赏GS(签署大神且是房主)到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_B_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_017(self, des='商业房-非直播,房间私聊打赏GS(不签署大神且非房主)到账60%(mcb)'):
		"""
		用例描述：
		商业房-非直播,房间私聊打赏GS(不签署大神且非房主)到账60%(mcb)		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = gs_B_ceo_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-friend")  # 确认rid不是直播房
		uid = gs_B_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['gs']['as_normal'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_018(self, des='商业房-才艺厅-购买观众位,表演者=主播到账60%(mc)'):
		"""
		用例描述：
		验证余额足够时，商业房-非直播打赏礼物给普通用户分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash_b)
		"""

		rid = gs_A_ceo_talent_show_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-talent-show")  # 确认rid是才艺厅
		uid = gs_A_uid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.deleteXsMicPermission(rid)
		mysql.updateXsChatroomConfig(rid, uid=uid, position=0)
		talent_show = {
			"position": talent_show_config['真爱']["1"]['position'],
			"price_id": talent_show_config['真爱']["1"]['price_id'],
			"price": talent_show_config['真爱']["1"]['price'],

		}
		data = encodeData(
			payType='talent_show',
			rid=rid,
			uid=uid,  # 表演者
			talent_show=talent_show
		)
		time.sleep(2)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             talent_show_config['真爱']["1"]['price'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), talent_show_config['真爱']["1"]['price'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - talent_show_config['真爱']["1"]['price'])

	def test_019(self, des='个人房,外显vip-礼物打赏GS到账90%(mcb)'):
		"""
		用例描述：
		验证余额足够时，个人房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "vip"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_020(self, des='个人房,外显vip-房间私聊打赏GS到账90%(mcb)'):
		"""
		用例描述：
		验证余额足够时，个人房房间私聊打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "vip"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - giftId['69']['price'] * default_num)

	def test_021(self, des='个人房,外显vip-背包礼物打赏GS到账90%(mcb)'):
		"""
		用例描述：
		个人房,背包礼物打赏GS到账60%(mc)
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = mysql.selectUserInfoSql('vip')
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 0)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.insertXsUserCommodity(payUid, cid=giftId['69']['cid'], num=default_num)
		cid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=giftId['69']['cid']))

		# 断言是否展示预期中的标签
		assert_equal(check_vip_pop(uid, "vip"), True)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid'],
			package_cid=cid,
			ctype='gift'
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash_b'),
		             giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), giftId['69']['price'] * default_num * rates['vip']['viproom'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)  # 不扣费
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=giftId['69']['cid']), 0)