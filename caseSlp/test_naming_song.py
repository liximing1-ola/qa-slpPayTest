# -*- encoding=utf8 -*-
__desc__ = "点唱房-点歌/冠歌"

import os
import time
import unittest

from caseSlp.config import *
from caseSlp.tools import prepare_test_data, insert_package_gift
from common import Consts
from common.Assert import assert_body, assert_code, assert_equal, assert_equal_eventually, assert_pay_success
from common.Request import post_request_session
from common.basicSlpXsgData import encodeData
from common.conRedis import conRedis
from common.conSlpXsgMysql import conMysql as mysql
from common.method import reason
from common.runFailed import Retry

# 房间快照只在排查时输出：ROOM_DEBUG=1 打开。默认关闭——每条冠歌用例都打一行，
# 正常跑的人用不上，反而淹掉真正要看的输出
ROOM_DEBUG = os.environ.get('ROOM_DEBUG') == '1'

# 服务端在「房间取不到」「RPC/回源失败」时复用的同一句文案，从不作为预期结果
ROOM_TYPE_ERROR = '房间类型错误'

# 改库到下单之间的固定等待可以被 NAMING_SLEEP 整体覆盖（对照实验用），不设就保持各处原值
NAMING_SLEEP = os.environ.get('NAMING_SLEEP')
NAMING_SLEEP = None if NAMING_SLEEP is None else float(NAMING_SLEEP)


def cache_wait(seconds):
	"""改库之后、下单之前的等待。

	名义上是「留出造数完成到访问的间隔」。实测过 NAMING_SLEEP=0 与不设各 3 轮：
	耗时 67.1s vs 76.0s，只差 9 秒，重试次数完全相同（都是每轮 1 条房间类型错误）。
	也就是说这 52 秒里有 43 秒并非白等——它同时在为异步落库争取时间，去掉之后
	那部分时间会转移到 assert_equal_eventually 的轮询里，并不会消失。

	所以默认值保留原样：用 9 秒换一个更宽的等待窗口（5/8 秒 > WAIT_TIMEOUT 的 3 秒）
	不划算，服务端变慢时反而是风险。NAMING_SLEEP 留作探针，等明确变快后再评测。
	"""
	time.sleep(seconds if NAMING_SLEEP is None else NAMING_SLEEP)


def room_scene(rid):
	"""一行描述房间现场：Redis 缓存 + 库内行。只读取证，自身异常全部吞掉

	「房间类型错误」既可能是房间数据真的坏了（被删/类型被改/多出一行），也可能是服务端
	RPC 或回源失败复用了同一句话。只剩一句文案时分不开这两种，所以失败时把现场一起带上。
	只读不删：删 Room.Data.<rid> 会让服务端 go2cache 必然 miss 并回源重建，
	并不比让它自己跟 binlog 同步更可靠。
	"""
	parts = []
	try:
		key = 'Room.Data.{}'.format(rid)
		raw = conRedis.getRawConn().get(key)
		parts.append('redis exists={} ttl={} len={} has_factory_type={}'.format(
			1 if raw else 0, conRedis.getConn().ttl(key), len(raw) if raw else 0,
			b'business-music' in raw if raw else False))
	except Exception as error:
		# 现场只是辅助信息，读不到不能反过来把用例搞红
		parts.append('redis 读取失败: {}'.format(error))
	try:
		scene = mysql.checkRoomScene(rid)
		parts.append('db 行数={} 类型={} deleted={} 房主={}'.format(
			scene['rows'], scene['factory_type'], scene['deleted'], scene['owner']))
	except Exception as error:
		parts.append('db 读取失败: {}'.format(error))
	return '; '.join(parts)


def snapshot_room(rid):
	"""请求前打一行房间快照（需 ROOM_DEBUG=1）"""
	if ROOM_DEBUG:
		print('[room] {} {}'.format(rid, room_scene(rid)))


def post_pay(rid, data, des):
	"""下单。命中「房间类型错误」时把房间现场写进失败原因再抛出。

	这句文案在本文件里从来不是预期结果（预期失败的用例等的是「冠名等级需高于当前等级」
	「该礼物暂不支持购买」这类业务文案），所以遇到就立即失败，不继续往下走断言——
	否则 test_009 那种用例会报成「预期『该礼物暂不支持购买』实际『房间类型错误』」，
	看着像业务分支不符，实际是请求在房间校验阶段就被挡回去了。
	"""
	snapshot_room(rid)
	res = post_request_session(pay_url, data, tokenName='slp', pay_uid=payUid)
	body = res.get('body') if isinstance(res, dict) else None
	if isinstance(body, dict) and body.get('msg') == ROOM_TYPE_ERROR:
		detail = '{}：实际返回值 {}, 预期 任何非房间类错误（房间现场: {}）'.format(
			reason(des, res), ROOM_TYPE_ERROR, room_scene(rid))
		Consts.fail_case_reason.append(detail)
		raise AssertionError(detail)
	return res


# 偶发「房间类型错误」的开关已收掉（见 snapshot_room：请求前不再删缓存），重试只当兜底：
# 服务端 RPC 超时或返回 err 时报的也是同一句文案，隔 5 秒重试能跟瞬时故障错开；
# 间隔太短等于拿同一份数据反复撞墙
@Retry(max_n=3, sleep=5)
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
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), money * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - money)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'), money * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - money)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		cache_wait(5)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
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
		cache_wait(5)
		res = post_pay(rid, data, des)
		assert_code(res['code'])
		assert_body(res['body'], 'success', 0, reason(des, res))
		assert_body(res['body'], 'msg', '冠名等级需高于当前等级', reason(des, res))

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		cache_wait(5)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		cache_wait(5)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		ucid = insert_package_gift(payUid, cid=naming_song_config[beilv]['cid'], num=1)
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
		cache_wait(8)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money - naming_song_config[beilv]['money_pay'])

		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		ucid = insert_package_gift(payUid, cid=naming_song_config[beilv]['cid'], num=2)
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
		cache_wait(8)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		ucid = insert_package_gift(payUid, cid=naming_song_config[beilv]['cid'], num=1)
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
		cache_wait(8)
		res = post_pay(rid, data, des)
		assert_code(res['code'])
		assert_body(res['body'], 'msg', '该礼物暂不支持购买', reason(des, res))

		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', uid), 0)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 1)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人

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
		ucid = insert_package_gift(payUid, cid=naming_song_config[beilv]['cid'], num=2)
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
		cache_wait(8)
		res = post_pay(rid, data, des)
		assert_pay_success(res, des)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('single_money', uid, money_type='money_cash'),
		                        naming_song_config[beilv]['money'] * rates['gs']['default'])
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('sum_money', payUid), default_money)
		assert_equal_eventually(lambda: mysql.selectUserInfoSql('num_commodity', uid=payUid, cid=naming_song_config[beilv]['cid']), 0)

		mysql.updateXsChatroomConfig(rid, 0, position=0)  # 接待位下人
