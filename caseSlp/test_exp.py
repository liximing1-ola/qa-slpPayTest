# -*- encoding=utf8 -*-
__desc__ = "经验值相关用例"

import time
import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data, prepare_vip_pop_data, prepare_acceleration_card, clear_acceleration_card, read_vip_pop
from common.Assert import assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='打赏者,贵族爵位=骑士(lv1,1倍)消费,vip经验值1:1增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.deleteUserAccountSql('user_popularity', uid)  # 修改pop值,还原数据
		mysql.deleteUserAccountSql('user_title_new', uid)  # 关闭贵族,还原数据
		mysql.deleteUserAccountSql('pay_room_money', uid)  # 修改vip值,还原数据

		mysql.deleteUserAccountSql('user_popularity', payUid)  # 修改pop值,还原数据
		mysql.deleteUserAccountSql('user_title_new', payUid)  # 关闭贵族,还原数据
		mysql.deleteUserAccountSql('pay_room_money', payUid)  # 修改vip值,还原数据
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['骑士']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)
		# 上面刚把双方的 vip/人气 复位，基线必然是 0。不为 0 只可能有两种原因：上游用例的异步
		# 结算迟到、或有别的用例把值改了回来。在这里直接报出来，比让下面的增量断言报
		# 「实际 6100 / 预期 100」好定位得多（6100 = 残留 6000 + 本次 100）
		assert_equal((payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop), (0, 0, 0, 0))

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['骑士']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['骑士']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_002(self, des='打赏者,贵族爵位=男爵(lv1,1倍)消费,vip经验值1:1增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['男爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['男爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['男爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_003(self, des='打赏者,贵族爵位=子爵(lv1,1倍)消费,vip经验值1:1增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['子爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['子爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['子爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_004(self, des='打赏者,贵族爵位=伯爵(1.05倍)消费,vip经验值1:1.05增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['伯爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['伯爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['伯爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_005(self, des='打赏者,贵族爵位=侯爵(1.1倍)消费,vip经验值1:1.1增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['侯爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['侯爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['侯爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_006(self, des='打赏者,贵族爵位=公爵(1.15倍)消费,vip经验值1:1.15增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['公爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['公爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['公爵']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_007(self, des='打赏者,贵族爵位=亲王(1.2倍)消费,vip经验值1:1.2增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['亲王']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['亲王']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['亲王']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_008(self, des='打赏者,贵族爵位=国王(1.25倍)消费,vip经验值1:1.25增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['国王']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['国王']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['国王']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	def test_009(self, des='打赏者,贵族爵位=皇帝(1.3倍)消费,vip经验值1:1.3增加'):
		"""
		用例描述：
		验证余额足够时，商业房打赏礼物给GS分成为：60，且收入在公会魅力值
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['皇帝']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['皇帝']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['皇帝']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'])

	@unittest.skip('多人场景后续维护') # todo
	def test_010(self, des='打赏者=皇帝(1.3倍),被打赏者多人,多个礼物,分别加成计算'):
		"""
		用例描述：
		打赏者=皇帝(1.3倍),被打赏者多人,多个礼物,分别加成计算
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.房间打赏礼物（打赏100分）
		3.校验接口状态和返回值数据
		4.检查被打赏者余额，预期为：1000 * 0.6 =600 (money_cash)
		"""
		rid = business_room_rid
		uids = tuple([str(i) for i in [gs_A_uid, normal_uid]])
		assert_equal(mysql.checkUserBroker(gs_A_uid), True)  # 确认 gs_A_uid是工会成员
		prepare_vip_pop_data(gs_A_uid)
		mysql.updateUserInfoSql('user_title_new', gs_A_uid, level=juewei_level['公爵']['level'])

		assert_equal(mysql.checkUserBroker(normal_uid), False)  # 确认 uid不是工会成员
		prepare_vip_pop_data(normal_uid)
		mysql.updateUserInfoSql('user_title_new', normal_uid, level=juewei_level['亲王']['level'])

		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['皇帝']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip = mysql.selectUserInfoSql('pay_room_money', payUid)
		payUid_old_pop = mysql.selectUserInfoSql('popularity', payUid)
		normal_uid_old_vip = mysql.selectUserInfoSql('pay_room_money', normal_uid)
		normal_uid_old_pop = mysql.selectUserInfoSql('popularity', normal_uid)
		gs_A_uid_old_vip = mysql.selectUserInfoSql('pay_room_money', gs_A_uid)
		gs_A_uid_old_pop = mysql.selectUserInfoSql('popularity', gs_A_uid)

		num = 10
		data = encodeData(
			rid=rid,
			payType='package-more',
			num=num,
			uids=uids
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(1)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid),
		             payUid_old_vip + len(uids) * num * juewei_level['皇帝']['update'] * giftId['69']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid),
		             payUid_old_pop + len(uids) * num * juewei_level['皇帝']['update'] * giftId['69']['price'] / 100)
		# 收礼人 不加成
		assert_equal(mysql.selectUserInfoSql('pay_room_money', normal_uid), normal_uid_old_vip + num * giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', normal_uid), normal_uid_old_pop + num * giftId['69']['price'])
		# 收礼人 不加成
		assert_equal(mysql.selectUserInfoSql('pay_room_money', gs_A_uid), gs_A_uid_old_vip + num * giftId['69']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', gs_A_uid), gs_A_uid_old_pop + num * giftId['69']['price'])

	def test_011(self, des='房间守护-双方均增加vip/人气值'):
		"""
		 用例描述：
		房间守护-双方均增加vip/人气值
		 脚本步骤：
		 1.构造开通者和被守护者数据
		 2.开通真爱守护 月
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查公会长余额，预期为： 0(不分成)
		 6.检查被打赏者余额.预期为：99900 * 0.6 = 59940
		 """
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房

		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['亲王']['level'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['皇帝']['level'])

		mysql.updateUserGodSql(uid, 2)
		mysql.updateUserGodSql(gs_A_ceo_uid, 1)
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateUserMoneyClearSql(uid, gs_A_ceo_uid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			payType='package-knightDefend',
			money=room_defend['zhenai']['month']['price'],
			uid=uid,
			rid=rid,
			knight_level=room_defend['zhenai']['month']['knight_level'],
			duration_level=room_defend['zhenai']['month']['duration_level'],
			price=room_defend['zhenai']['month']['price'],
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid),
		             payUid_old_vip + juewei_level['皇帝']['update'] * room_defend['zhenai']['month']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid),
		             payUid_old_pop + juewei_level['皇帝']['update'] * room_defend['zhenai']['month']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + room_defend['zhenai']['month']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + room_defend['zhenai']['month']['price'])

	@unittest.skip('功能下线')
	def test_012(self, des='个人守护-双方均增加vip/人气值'):
		"""
		用例描述：
		个人守护-双方增加vip/人气值
		脚本步骤：
		1.构造开通者和被守护者数据
		2.开通价值52000钻小宝贝守护（xs_relation_config id=2）
		3.校验接口状态和返回值数据
		4.检查打赏者余额
		5.检查被打赏者余额,预期：52000 * 0.62 = 32240
		"""

		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['亲王']['level'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['皇帝']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		data = encodeData(
			uid=uid,
			payType='defend',
			defend_id=defend['小宝贝']['id'],
			money=defend['小宝贝']['price']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['皇帝']['update'] * defend['小宝贝']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['皇帝']['update'] * defend['小宝贝']['price'] / 100)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + defend['小宝贝']['price'])
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + defend['小宝贝']['price'])

	def test_013(self, des='使用vip/人气加速卡,直播开通房间守护'):
		"""
		 用例描述：
		房间守护-双方均增加vip/人气值
		 脚本步骤：
		 1.构造开通者和被守护者数据
		 2.开通真爱守护 月
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查公会长余额，预期为： 0(不分成)
		 6.检查被打赏者余额.预期为：99900 * 0.6 = 59940
		 """
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		rid = gs_soundchat_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-soundchat")  # 确认rid是直播房

		mysql.deleteUserAccountSql('user_popularity', uid)  # 修改pop值,还原数据
		mysql.deleteUserAccountSql('user_title_new', uid)  # 关闭贵族,还原数据
		mysql.deleteUserAccountSql('pay_room_money', uid)  # 修改vip值,还原数据
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['亲王']['level'])

		mysql.deleteUserAccountSql('user_popularity', payUid)  # 修改pop值,还原数据
		mysql.deleteUserAccountSql('user_title_new', payUid)  # 关闭贵族,还原数据
		mysql.deleteUserAccountSql('pay_room_money', payUid)  # 修改vip值,还原数据
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['皇帝']['level'])

		mysql.updateUserGodSql(uid, 2)
		mysql.updateUserGodSql(gs_A_ceo_uid, 1)
		mysql.updateMoneySql(payUid, default_money)
		mysql.updateUserMoneyClearSql(uid, gs_A_ceo_uid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(
			payType='package-knightDefend',
			money=room_defend['zhenai']['month']['price'],
			uid=uid,
			rid=rid,
			knight_level=room_defend['zhenai']['month']['knight_level'],
			duration_level=room_defend['zhenai']['month']['duration_level'],
			price=room_defend['zhenai']['month']['price'],
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		# 加速卡要覆盖整个结算窗口：收礼方的 vip/人气是异步落库的，实测会慢于这里的 0.5 秒。
		# 原来先 clear_acceleration_card 再断言，结算慢于 0.5 秒时服务端已读不到加速卡，
		# 收礼方读数会停在 0（偶发红）；故改为断言后再清卡，并用轮询断言等落库。预期值不变。
		try:
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
			                        payUid_old_vip + juewei_level['皇帝']['update'] * room_defend['zhenai']['month']['price'] / 100 * payUid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
			                        payUid_old_pop + juewei_level['皇帝']['update'] * room_defend['zhenai']['month']['price'] / 100 * payUid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid),
			                        uid_old_vip + room_defend['zhenai']['month']['price'] * uid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid),
			                        uid_old_pop + room_defend['zhenai']['month']['price'] * uid_speed)
		finally:
			clear_acceleration_card(uid, payUid)


	def test_014(self, des='使用vip/人气加速卡,房间送礼,收礼方为人气标签,1倍vip'):
		"""
		 用例描述：
		房间守护-双方均增加vip/人气值
		 脚本步骤：
		 1.构造开通者和被守护者数据
		 2.开通真爱守护 月
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查公会长余额，预期为： 0(不分成)
		 6.检查被打赏者余额.预期为：99900 * 0.6 = 59940
		 """
		rid = business_room_rid
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['公爵']['level'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['公爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		# 加速卡要覆盖整个结算窗口：收礼方的 vip/人气是异步落库的，实测会慢于这里的 0.5 秒。
		# 原来先 clear_acceleration_card 再断言，结算慢于 0.5 秒时服务端已读不到加速卡，
		# 收礼方读数会停在 0（偶发红）；故改为断言后再清卡，并用轮询断言等落库。预期值不变。
		try:
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
			                        payUid_old_vip + juewei_level['公爵']['update'] * giftId['69']['price'] / 100 * payUid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
			                        payUid_old_pop + juewei_level['公爵']['update'] * giftId['69']['price'] / 100 * payUid_speed)
			# 收礼人-开通爵位的vip加速,不会收礼时对vip值加倍
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid),
			                        uid_old_vip + giftId['69']['price'] * uid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid),
			                        uid_old_pop + giftId['69']['price'] * uid_speed)
		finally:
			clear_acceleration_card(uid, payUid)

	def test_015(self, des='使用vip/人气加速卡,私聊送礼,收礼方为人气标签,1倍vip'):
		"""
		用例描述：
		主播GS-私聊打赏分成60%进mc
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.私聊一对一打赏流程(礼物:棒棒糖)
		3.校验接口和返回值数据
        4.检查被打赏者余额和账户，预期为：50 * 0.6 = 30(mc)
        5.检查打赏者余额.预期为：1000 - 50 = 950
		"""
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['国王']['level'])
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['国王']['level'])

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)

		time.sleep(0.5)
		# 加速卡要覆盖整个结算窗口：收礼方的 vip/人气是异步落库的，实测会慢于这里的 0.5 秒。
		# 原来先 clear_acceleration_card 再断言，结算慢于 0.5 秒时服务端已读不到加速卡，
		# 收礼方读数会停在 0（偶发红）；故改为断言后再清卡，并用轮询断言等落库。预期值不变。
		try:
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
			                        payUid_old_vip + juewei_level['国王']['update'] * giftId['69']['price'] / 100 * payUid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
			                        payUid_old_pop + juewei_level['国王']['update'] * giftId['69']['price'] / 100 * payUid_speed)
			# 收礼人-开通爵位的vip加速,不会收礼时对vip值加倍
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid),
			                        uid_old_vip + giftId['69']['price'] * uid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid),
			                        uid_old_pop + giftId['69']['price'] * uid_speed)
		finally:
			clear_acceleration_card(uid, payUid)

	def test_016(self, des='使用vip/人气加速卡,房间送礼,收礼方为vip标签,2倍vip'):
		"""
		 用例描述：
		房间守护-双方均增加vip/人气值
		 脚本步骤：
		 1.构造开通者和被守护者数据
		 2.开通真爱守护 月
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查公会长余额，预期为： 0(不分成)
		 6.检查被打赏者余额.预期为：99900 * 0.6 = 59940
		 """
		rid = business_room_rid
		uid = normal_uid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid不是工会成员
		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['公爵']['level'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['公爵']['level'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(
			rid=rid,
			payType='package',
			uid=uid,
			giftId=giftId['69']['gid']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		# 加速卡要覆盖整个结算窗口：收礼方的 vip/人气是异步落库的，实测会慢于这里的 0.5 秒。
		# 原来先 clear_acceleration_card 再断言，结算慢于 0.5 秒时服务端已读不到加速卡，
		# 收礼方读数会停在 0（偶发红）；故改为断言后再清卡，并用轮询断言等落库。预期值不变。
		try:
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
			                        payUid_old_vip + juewei_level['公爵']['update'] * giftId['69']['price'] / 100 * payUid_speed * 2)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
			                        payUid_old_pop + juewei_level['公爵']['update'] * giftId['69']['price'] / 100 * payUid_speed * 2)
			# 收礼人-开通爵位的vip加速,不会收礼时对vip值加倍
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid),
			                        uid_old_vip + giftId['69']['price'] * uid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid),
			                        uid_old_pop + giftId['69']['price'] * uid_speed)
		finally:
			clear_acceleration_card(uid, payUid)

	def test_017(self, des='使用vip/人气加速卡,私聊送礼,收礼方为vip标签,2倍vip'):
		"""
		用例描述：
		主播GS-私聊打赏分成60%进mc
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.私聊一对一打赏流程(礼物:棒棒糖)
		3.校验接口和返回值数据
        4.检查被打赏者余额和账户，预期为：50 * 0.6 = 30(mc)
        5.检查打赏者余额.预期为：1000 - 50 = 950
		"""
		uid = normal_uid
		assert_equal(mysql.checkUserBroker(uid), False)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['国王']['level'])
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['国王']['level'])

		payUid_old_vip, payUid_old_pop, uid_old_vip, uid_old_pop = read_vip_pop(payUid, uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_pay_success(res, des)

		time.sleep(0.5)
		# 加速卡要覆盖整个结算窗口：收礼方的 vip/人气是异步落库的，实测会慢于这里的 0.5 秒。
		# 原来先 clear_acceleration_card 再断言，结算慢于 0.5 秒时服务端已读不到加速卡，
		# 收礼方读数会停在 0（偶发红）；故改为断言后再清卡，并用轮询断言等落库。预期值不变。
		try:
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
			                        payUid_old_vip + juewei_level['国王']['update'] * giftId['69']['price'] / 100 * payUid_speed * 2)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
			                        payUid_old_pop + juewei_level['国王']['update'] * giftId['69']['price'] / 100 * payUid_speed * 2)
			# 收礼人-开通爵位的vip加速,不会收礼时对vip值加倍
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid),
			                        uid_old_vip + giftId['69']['price'] * uid_speed)
			assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid),
			                        uid_old_pop + giftId['69']['price'] * uid_speed)
		finally:
			clear_acceleration_card(uid, payUid)