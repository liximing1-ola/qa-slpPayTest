# -*- encoding=utf8 -*-
__desc__ = "普通用户-个人守护"

import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_vip_pop_data, prepare_acceleration_card, clear_acceleration_card
from common.Assert import assert_code, assert_equal, assert_body
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
	def test_001(self, des='给普通用户开通个人守护场景60%(mcb)'):
		"""
		用例描述：
		给普通用户开通个人守护场景60%(mcb)
		脚本步骤：
		1.构造开通者和被守护者数据
		2.开通价值52000钻小宝贝守护（xs_relation_config id=2）
		3.校验接口状态和返回值数据
		4.检查打赏者余额
		5.检查被打赏者余额,预期：52000 * 0.62 = 32240
		"""
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(normal_uid)
		data = encodeData(
			uid=normal_uid,
			payType='defend',
			defend_id=defend['小宝贝']['id'],
			money=defend['小宝贝']['price']
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['price'])
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'),
		             defend['小宝贝']['price'] * rates['normal']['default'])

	def test_002(self, des='给普通用户开通个人守护进阶场景,不分成'):
		"""
		 用例描述：
		给普通用户开通个人守护进阶场景60%(mcb)
		 脚本步骤：
		 1.接test_01
		 2.购买进阶版（99900钻），黄金小宝贝对应进阶价格
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：100000 - 99900 = 100
		 5.检查被打赏者余额,预期： 99900 * 0.62 = 61938
		INSERT INTO `xianshi`.`xs_relation_defend`(`id`, `uid`, `defend_uid`, `defend_value`, `relation_id`, `expire_time`, `create_time`, `update_time`, `app_id`, `upgrade`, `hidden`, `defend_name`, `diy_name`, `diy_status`, `diy_fail_reason`, `gift_defend_value`) VALUES (90, 200254777, 200252072, 30000, 2, 1752113866, 1693484097, 1715594801, 66, 0, 0, '', '', 0, '', 0);
		INSERT INTO `xianshi`.`xs_relation_defend`(`id`, `uid`, `defend_uid`, `defend_value`, `relation_id`, `expire_time`, `create_time`, `update_time`, `app_id`, `upgrade`, `hidden`, `defend_name`, `diy_name`, `diy_status`, `diy_fail_reason`, `gift_defend_value`) VALUES (89, 200252072, 200254777, 30000, 2, 1752113866, 1693484097, 1715594801, 66, 0, 0, '', '', 0, '', 0);
		 """

		prepare_vip_pop_data(normal_uid, payUid)
		mysql.updateUserInfoSql('user_title_new', payUid, level=juewei_level['侯爵']['level'])

		payUid_old_vip = mysql.selectUserInfoSql('pay_room_money', payUid)
		payUid_old_pop = mysql.selectUserInfoSql('popularity', payUid)
		uid_old_vip = mysql.selectUserInfoSql('pay_room_money', normal_uid)
		uid_old_pop = mysql.selectUserInfoSql('popularity', normal_uid)

		# 添加使用vip/人气加速卡
		acc = prepare_acceleration_card(normal_uid, 1.4, payUid, 1.2)
		payUid_speed = acc['pay_speed']
		normal_uid_speed = acc['uid_speed']

		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(normal_uid)
		defend_id = mysql.selectUserInfoSql('relation_id', payuid=payUid, uid=normal_uid, cid=defend['小宝贝']['id'])
		mysql.updateRelationExpire(payUid, normal_uid)  # 不能api开通关系了,直接改表续时长
		data = encodeData(
			uid=normal_uid,
			payType='defend-upgrade',
			money=defend['小宝贝']['upgrade_price'],
			defend_id=defend_id
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		clear_acceleration_card(normal_uid, payUid)
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['upgrade_price'])
		assert_equal(mysql.selectUserInfoSql('sum_money', normal_uid), 0)

		assert_equal(mysql.selectUserInfoSql('pay_room_money', payUid), payUid_old_vip + juewei_level['侯爵']['update'] * defend['小宝贝']['upgrade_price'] / 100*payUid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', payUid), payUid_old_pop + juewei_level['侯爵']['update'] * defend['小宝贝']['upgrade_price'] / 100*payUid_speed)
		assert_equal(mysql.selectUserInfoSql('pay_room_money', normal_uid), uid_old_vip + defend['小宝贝']['upgrade_price']*normal_uid_speed)
		assert_equal(mysql.selectUserInfoSql('popularity', normal_uid), uid_old_pop + defend['小宝贝']['upgrade_price']*normal_uid_speed)

	def test_003(self, des='普通用户个人守护解除场景,不分成'):
		"""
		 用例描述：
		普通用户个人守护解除场景,不分成
		 脚本步骤：
		 1.接test_01，test_02
		 2.强制解除关系
		 3.校验接口状态和返回值数据
		 4.检查打赏者余额，预期：40000 - 36000 = 4000
		 """
		mysql.updateMoneySql(payUid, money=default_money)
		mysql.updateMoneySql(normal_uid)
		mysql.selectUserInfoSql('relation_id', uid=normal_uid, cid=defend['小宝贝']['id'])
		defend_id = mysql.selectUserInfoSql('relation_id', payuid=payUid, uid=normal_uid, cid=defend['小宝贝']['id'])
		data = encodeData(
			uid=normal_uid,
			payType='defend-break',
			money=defend['小宝贝']['break_price'],
			defend_id=defend_id
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - defend['小宝贝']['break_price'])
		assert_equal(mysql.selectUserInfoSql('sum_money', normal_uid), 0)
