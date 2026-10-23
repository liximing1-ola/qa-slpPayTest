# -*- encoding=utf8 -*-
__author__ = "Wu.Zhenxing"
__title__ = ""
__desc__ = "公会主播-房间打赏"

import random
import time
import unittest

from caseSlp.config import *
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import case_list_b, result
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conRedis import conRedis
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=1)
class TestPayCreate(unittest.TestCase):
	@unittest.skip("""测试造数据""")
	def test_001(self, des='造数据'):
		results = mysql.select_uid_rid()
		for row in results:
			# 删除送礼上限的key
			conRedis.delKey_slp(f'slp_go:user_growth:package_limit:{payUid}*')
			uid = row[0]
			rid = row[1]

			num = random.randint(1, 500)
			money = giftId['69']['price'] * num
			mysql.updateMoneySql(payUid, money)
			mysql.updateMoneySql(uid)
			mysql.updateUserGodSql(uid, 2)
			mysql.deleteUserAccountSql('user_commodity', payUid)
			data = encodeData(
				rid=rid,
				payType='package',
				uid=uid,
				giftId=giftId['69']['gid'],
				money=money,
				num=num
			)
			res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
			time.sleep(0.2)
			assert_code(res['code'])
			assert_body(res['body'], 'success', 1, reason(des, res))
			case_list_b[des] = result
