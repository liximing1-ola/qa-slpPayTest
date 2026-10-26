# -*- encoding=utf8 -*-
__desc__ = "点唱房-点歌/冠歌"

import time
import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data
from common.Assert import assert_code, assert_equal, assert_body
from common.Consts import result, case_list_b
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry


@Retry(max_n=2)
class TestPayCreate(unittest.TestCase):
	# test_004~test_006 都对 test_003 造出的冠歌记录做二次操作，记录不存在时接口会直接成功/不生效，
	# 用例会以「预期失败却成功」的形式误报，用它标记前置状态是否就绪
	_naming_ready = False

	def test_001(self, des='点唱房-点歌,一首歌'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		for song_id in order_songs_list:
			mysql.updateXsRoomUserMusicList(song_id)  # 删除冠歌信息

		num = 1
		money = unit_price * num
		order_songs = [
			{"song_id": song_id, "singer_id": uid} for song_id in order_songs_list[:num]
		]
		data = encodeData(
			rid=rid,
			payType='choose_song',
			money=money,
			order_songs=order_songs
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), money * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - money)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_002(self, des='点唱房-点歌,多首歌'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		for song_id in order_songs_list:
			mysql.updateXsRoomUserMusicList(song_id)  # 删除冠歌信息
			
		num = 2
		money = unit_price * num
		order_songs = [
			{"song_id": song_id, "singer_id": uid} for song_id in order_songs_list[:num]
		]
		data = encodeData(
			rid=rid,
			payType='choose_song',
			money=money,
			order_songs=order_songs
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), money * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - money)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_003(self, des='点唱房-冠歌'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv="2"
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 1,
			"ucid": 0,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 0
		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result
		TestPayCreate._naming_ready = True  # 冠歌记录已就绪，后续依赖用例可以执行

	def test_004(self, des='点唱房-冠歌[未过期]后,冠歌同一首歌.同倍数,失败'):
		if not TestPayCreate._naming_ready:
			self.skipTest('依赖 test_003 冠歌成功，该用例未执行或已失败')
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		# mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "2"
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 1,
			"ucid": 0,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 0
		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(5)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 0, reason(des, res))
		assert_body(res['body'], 'msg', '冠名等级需高于当前等级', reason(des, res))

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_005(self, des='点唱房-冠歌[已过期]后,冠歌同一首歌.同倍数,成功'):
		if not TestPayCreate._naming_ready:
			self.skipTest('依赖 test_003 冠歌成功，该用例未执行或已失败')
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		# mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		mysql.updateXsRoomUserMusicNaming(order_songs_list[0])  # 修改冠歌信息-过期
		beilv = "2"
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 1,
			"ucid": 0,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 0
		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(5)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_006(self, des='点唱房-抢冠-高倍数,成功'):
		if not TestPayCreate._naming_ready:
			self.skipTest('依赖 test_003 冠歌成功，该用例未执行或已失败')
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		# mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "3"
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 1,
			"ucid": 0,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 0
		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(5)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_007(self, des='点唱房-冠歌,礼物上架,用背包礼物支付,礼物个数<所需个数,[混合支付],扣[背包+钻石]'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "5-上架"
		# 插入礼物
		mysql.insertXsUserCommodity(payUid, naming_song_config[beilv]['cid'], 1)
		# 查询礼物在背包的id
		ucid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=naming_song_config[beilv]['cid']))
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 2,
			"ucid": ucid,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 1

		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(8)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_008(self, des='点唱房-冠歌,礼物上架,用背包礼物支付,礼物个数>=所需个数,[背包支付],扣[背包]'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "5-上架"
		# 插入礼物
		mysql.insertXsUserCommodity(payUid, naming_song_config[beilv]['cid'], 2)
		# 查询礼物在背包的id
		ucid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=naming_song_config[beilv]['cid']))
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 2,
			"ucid": ucid,
			"money_pay": 0,
			"ucnum": 2

		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(8)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_009(self, des='点唱房-冠歌,礼物下架,用背包礼物支付,礼物个数<所需个数,扣款失败[该礼物暂不支持购买]'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "5-下架"
		# 插入礼物
		mysql.insertXsUserCommodity(payUid, naming_song_config[beilv]['cid'], 1)
		# 查询礼物在背包的id
		ucid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=naming_song_config[beilv]['cid']))
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 2,
			"ucid": ucid,
			"money_pay": naming_song_config[beilv]['money_pay'],
			"ucnum": 1

		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(8)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'msg', '该礼物暂不支持购买', reason(des, res))

		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal(mysql.selectUserInfoSql('sum_money', uid), 0)
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 1)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result

	def test_010(self, des='点唱房-冠歌,礼物下架,用背包礼物支付,礼物个数>=所需个数,[背包支付],扣[背包]'):
		rid = gs_music_rid
		assert_equal(mysql.checkRidFactoryType(rid), "business-music")  # 确认rid是点唱房
		uid = gsUid
		assert_equal(mysql.checkUserBroker(uid), True)  # 确认 uid是工会成员
		prepare_test_data(payUid, uid, money=default_money, god_status={uid: 2})
		mysql.updateXsChatroomConfig(rid, gs_A_ceo_uid, position=0)  # 接待位上人
		mysql.updateXsRoomUserMusicList(order_songs_list[0])  # 删除冠歌信息
		beilv = "5-下架"
		# 插入礼物
		mysql.insertXsUserCommodity(payUid, naming_song_config[beilv]['cid'], 2)
		# 查询礼物在背包的id
		ucid = int(mysql.selectUserInfoSql('id_commodity', payUid, cid=naming_song_config[beilv]['cid']))
		naming_song = {
			'money': naming_song_config[beilv]['money'],
			'song_id': order_songs_list[0],
			'gift_id': naming_song_config[beilv]['gift_id'],
			'multiple_id': naming_song_config[beilv]['multiple_id'],

			"gift_cnt": 2,
			"ucid": ucid,
			"money_pay": 0,
			"ucnum": 2

		}
		data = encodeData(
			rid=rid,
			uid=uid,
			payType='naming_song',
			naming_song=naming_song
		)
		time.sleep(8)
		res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 1, reason(des, res))
		assert_equal(mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		             naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal(mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal(mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
		case_list_b[des] = result
