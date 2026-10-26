# -*- encoding=utf8 -*-
__desc__ = "公会主播-个人守护"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_vip_pop_data, prepare_acceleration_card, clear_acceleration_card
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b2, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


# 开守护关系功能已下线（SLP-5.18.0）：test_001 造关系被 skip 后，test_002/test_003 依赖它造出的关系，
# 单独保留只会每次必输。整类 skip，待功能重新上线再恢复。
@unittest.skip("开守护关系功能下线,SLP-5.18.0")
@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	def test_001(self, des='给GS开通个人守护场景60%(mc)'):
		"""
		用例描述：
		给GS开通个人守护场景60%(mc)
		脚本步骤：
		1.构造开通者和被守护者数据
		2.开通价值52000钻小宝贝守护（xs_relation_config id=2）
		3.校验接口状态和返回值数据
		4.检查打赏者余额
		5.检查被打赏者余额,预期：52000 * 0.62 = 32240
		"""
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		data = encodeData(
			uid=uid,
			payType='defend',
			defend_id=defend['小宝贝']['id'],
			money=defend['小宝贝']['price']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['price'])
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), defend['小宝贝']['price'] * rates['gs']['default'])
		case_list_b2[des] = result

	def test_002(self, des='给GS开通个人守护进阶场景,不分成'):
		"""
		 用例描述：
		给GS开通个人守护进阶场景60(mc)
		 脚本步骤：
		 1.接test_01
		 2.购买进阶版（99900钻），黄金小宝贝对应进阶价格
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查被打赏者余额,预期： 99900 * 0.62 = 61938
		 """
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员

		prepare_vip_pop_data(uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['侯爵']['level'])

		payUid_old_vip = mysql.selectUserInfoSql('pay_room_money', payUid)
		payUid_old_pop = mysql.selectUserInfoSql('popularity', payUid)
		uid_old_vip = mysql.selectUserInfoSql('pay_room_money', uid)
		uid_old_pop = mysql.selectUserInfoSql('popularity', uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		uid_speed = acc['uid_speed']

		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		defend_id = mysql.selectUserInfoSql('relation_id', payuid=payUid, uid=uid, cid=defend['小宝贝']['id'])
		mysql.updateRelationExpire(payUid, uid)  # 不能api开通关系了,直接改表续时长
		data = encodeData(
			uid=uid,
			payType='defend-upgrade',
			money=defend['小宝贝']['upgrade_price'],
			defend_id=defend_id
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		clear_acceleration_card(uid, payUid)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['upgrade_price'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), 0)

		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid),
		             payUid_old_vip + juewei_level['侯爵']['update'] * defend['小宝贝']['upgrade_price'] / 100 * payUid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid),
		             payUid_old_pop + juewei_level['侯爵']['update'] * defend['小宝贝']['upgrade_price'] / 100 * payUid_speed)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', uid), uid_old_vip + defend['小宝贝']['upgrade_price'] * uid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', uid), uid_old_pop + defend['小宝贝']['upgrade_price'] * uid_speed)

		case_list_b2[des] = result

	def test_003(self, des='GS个人守护解除场景,不分成'):
		"""
		 用例描述：
		GS个人守护解除场景,不分成
		 脚本步骤：
		 1.接test_01，test_02
		 2.强制解除关系
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：40000 - 36000 = 4000
		 """
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(uid)
		mysql.updateUserGodSql(uid, 2)
		mysql.selectUserInfoSql('relation_id', uid=uid, cid=defend['小宝贝']['id'])
		defend_id = mysql.selectUserInfoSql('relation_id', payuid=payUid, uid=uid, cid=defend['小宝贝']['id'])
		data = encodeData(
			uid=uid,
			payType='defend-break',
			money=defend['小宝贝']['break_price'],
			defend_id=defend_id
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['break_price'])
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), 0)
		case_list_b2[des] = result
