# -*- encoding=utf8 -*-
__title__ = ""
__desc__ = "经验值相关用�?

import time
import unittest

from caseXsg.config import *
from caseXsg.tools import prepare_test_data, prepare_vip_pop_data, prepare_acceleration_card, clear_acceleration_card
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):

	def test_001(self, des='vip人气计算,使用爵位+加速卡,房间送礼'):
		rid = gs_A_rid_1
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid不是工会成员
		prepare_vip_pop_data(uid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['normal_uid']['�?]['level'])
		prepare_vip_pop_data(payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['normal_uid']['�?]['level'])
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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		time.sleep(0.5)
		clear_acceleration_card(uid, payUid)
		# 贵族加速vip,加速卡加速vip和人�?		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid),
		             payUid_old_vip + juewei_level['normal_uid']['�?]['update'] * giftId['69']['price'] / 100 * payUid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid),
		             payUid_old_pop + giftId['69']['price'] * payUid_speed * 3)

		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip)
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'] * uid_speed)
		case_list_b2[des] = result

	def test_002(self, des='vip人气计算,使用爵位+加速卡,私聊送礼'):
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成�?		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', uid, level=juewei_level['normal_uid']['�?]['level'])
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['normal_uid']['�?]['level'])

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
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))

		time.sleep(0.5)
		clear_acceleration_card(uid, payUid)
		# 贵族加速vip,加速卡加速vip和人�?		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid),
		             payUid_old_vip + juewei_level['normal_uid']['�?]['update'] * giftId['69']['price'] / 100 * payUid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid),
		             payUid_old_pop + giftId['69']['price'] * payUid_speed * 3)

		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip)
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + giftId['69']['price'] * uid_speed)
		case_list_b2[des] = result
