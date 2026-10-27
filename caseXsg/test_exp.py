# -*- encoding=utf8 -*-
__desc__ = "经验值相关用例"

import time
import unittest

from caseXsg.config import *
from caseXsg.tools import prepare_test_data, prepare_vip_pop_data, prepare_acceleration_card, clear_acceleration_card
from common.Assert import assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='vip人气计算,使用爵位+加速卡,房间送礼'):
		rid = gs_A_rid_1
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		# xsg 的爵位成长值（殿=2500 万）与 slp 那套完全不同，必须显式传入 growth，
		# 否则 updateUserInfoSql 会按 slp 表写成 650 万，库里 level 与 growth 不自洽
		jw = juewei_level['normal_uid']['殿']
		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=jw['level'], growth=jw['base'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=jw['level'], growth=jw['base'])
		mysql.updateMoneySql(payUid, default_money)
		mysql.deleteUserAccountSql('user_commodity', payUid)

		payUid_old_vip = mysql.selectUserInfoSql('pay_room_money', payUid)
		payUid_old_pop = mysql.selectUserInfoSql('popularity', payUid)
		uid_old_vip = mysql.selectUserInfoSql('pay_room_money', uid)
		uid_old_pop = mysql.selectUserInfoSql('popularity', uid)

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
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_pay_success(res, des)
		time.sleep(0.5)
		clear_acceleration_card(uid, payUid)
		# 贵族加速vip,加速卡加速vip和人气
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
		                        payUid_old_vip + juewei_level['normal_uid']['殿']['update'] * giftId['69']['price'] / 100 * payUid_speed)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
		                        payUid_old_pop + giftId['69']['price'] * payUid_speed * 3)

		assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'] * uid_speed)

	def test_002(self, des='vip人气计算,使用爵位+加速卡,私聊送礼'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		jw = juewei_level['normal_uid']['帝']
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', uid, level=jw['level'], growth=jw['base'])
		mysql.updateUserInfoSql('user_title_new', payUid, level=jw['level'], growth=jw['base'])

		payUid_old_vip = mysql.selectUserInfoSql('pay_room_money', payUid)
		payUid_old_pop = mysql.selectUserInfoSql('popularity', payUid)
		uid_old_vip = mysql.selectUserInfoSql('pay_room_money', uid)
		uid_old_pop = mysql.selectUserInfoSql('popularity', uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		data = encodeData(payType='chat-gift',
		                  num=default_num,
		                  uid=uid,
		                  giftId=giftId['69']['gid'])
		res = post_request_session(pay_url, data, tokenName='xsg', pay_uid=payUid)
		assert_pay_success(res, des)

		time.sleep(0.5)
		clear_acceleration_card(uid, payUid)
		# 贵族加速vip,加速卡加速vip和人气
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', payUid),
		                        payUid_old_vip + juewei_level['normal_uid']['帝']['update'] * giftId['69']['price'] / 100 * payUid_speed)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', payUid),
		                        payUid_old_pop + giftId['69']['price'] * payUid_speed * 3)

		assert_equal_eventually(lambda: mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'] * uid_speed)
