# -*- encoding=utf8 -*-
__desc__ = "甄选礼盒"

import time
import unittest

from caseSlp.config import *
from common.Assert import assert_code, assert_equal, assert_body
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	@unittest.skip("测试环境配置数据变更,不在维护用例")
	def test_001(self, des='送礼人=亲王(vip=1.2倍),甄选礼盒(6元),送多人多个'):
		"""
		用例描述：
		甄选礼盒,送礼人爵位=亲王,送多人多个场景
		脚本步骤：
		1.构造打赏者和被打赏者数据
		2.私聊一对一打赏流程(礼物:棒棒糖)
		3.校验接口和返回值数据
		4.检查预期返回msg，预期：支付失败，提示Toast
		5.检查被打赏者余额,预期：0
		"""
		jw = juewei_level['亲王']
		base_money = 10000000
		mysql.updateUserMoneyClearSql(payUid, normal_uid, gsUid)
		mysql.deleteUserAccountSql('user_commodity', payUid)
		mysql.deleteUserAccountSql('user_title_new', payUid)  # 关闭贵族,还原数据
		mysql.updateUserGodSql(gsUid, 1)
		# 清除打赏流水
		mysql.deleteUserAccountSql('pay_change', payUid)
		# 清空人气值
		mysql.deleteUserAccountSql('user_popularity', normal_uid)
		mysql.deleteUserAccountSql('user_popularity', gsUid)
		# 清空VIP值
		mysql.deleteUserAccountSql('pay_room_money', payUid)
		# 开启爵位
		mysql.updateUserInfoSql('user_title_new', payUid, level=jw['level'])
		mysql.updateMoneySql(payUid, base_money)

		data = encodeData(
			payType='zx_box',
			num=1000,
			giftId=zx_box['6']['gid'],
			price=zx_box['6']['price'],
			uids=('{}'.format(normal_uid), '{}'.format(gsUid))
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		time.sleep(5)
		# 查询 打赏人/收礼人数据,用于计算
		send_gift_data= mysql.selectZxPayData(payUid)
		# 校验收礼人气值
		normal_rq_total = 0
		gs_rq_total = 0
		normal_fencheng_total = 0
		gs_fencheng_total = 0
		for data in send_gift_data:
			if int(data['to_uid']) == gsUid:
				price = zx_box['6'][data['gid']]['price']
				RQ = zx_box['6'][data['gid']]['RQ']
				total_num = int(data['total_num'])
				gs_rq_total += price * RQ * total_num
				gs_fencheng_total += price * total_num
			if int(data['to_uid']) == normal_uid:
				price = zx_box['6'][data['gid']]['price']
				RQ = zx_box['6'][data['gid']]['RQ']
				total_num = int(data['total_num'])
				normal_rq_total += price * RQ * total_num
				normal_fencheng_total += price * total_num
		assert_equal(mysql.selectUserInfoSql("popularity", normal_uid), normal_rq_total)
		assert_equal(mysql.selectUserInfoSql("popularity", gsUid), gs_rq_total)
		# 校验收礼人分成
		assert_equal(mysql.selectUserInfoSql('single_money', gsUid, money_type='money_cash'), gs_fencheng_total * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('single_money', normal_uid, money_type='money_cash_b'), normal_fencheng_total * rates['normal']['default'])
		# 校验送礼人VIP值
		pay_vip_total = 0
		for data in send_gift_data:
			price = zx_box['6'][data['gid']]['price']
			VIP = zx_box['6'][data['gid']]['VIP']
			total_num = int(data['total_num'])
			pay_vip_total += price * VIP * total_num
		assert_equal(mysql.selectUserInfoSql("pay_room_money", payUid), pay_vip_total * jw['update'] / 100)

		# 校验送礼人贵族成长值
		pay_czz_total = 0
		for data in send_gift_data:
			price = zx_box['6'][data['gid']]['price']
			CZZ = zx_box['6'][data['gid']]['CZZ']
			total_num = int(data['total_num'])
			if price >= 10000:  # 大于10000钻+送礼人成长值
				pay_czz_total += price * CZZ * total_num
		assert_equal(mysql.selectUserInfoSql("growth", payUid), pay_czz_total + jw['base'])

		# 校验送礼人扣费
		pay_total_money = 0
		for data in send_gift_data:
			price = zx_box['6'][data['gid']]['price']
			total_num = int(data['total_num'])
			pay_total_money += price * total_num
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), base_money - pay_total_money)
