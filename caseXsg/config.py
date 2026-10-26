# 打赏�?from common.Config import config as old_config

pay_url = old_config.xsg_pay_url
default_num = 1  # 礼物个数
default_money = 1000000  # 打赏者默认金�?payUid = 600041937  # 15025800021

gs_A_bid = 600041992  # A工会 工会id
gs_B_bid = 600030905  # B工会 工会id

gs_A_ceo_uid = 600041992  # 公会�?15025800001	600041992
gs_A_room_owner_1_uid = 600042759  # 厅长1	15025800002	600042759
gs_A_room_owner_2_uid = 600030957  # 厅长2	15025800003	600030957
gs_A_uid_1 = gsUid = 600005148  # 主播1	15025800004	600005148
gs_A_uid_2 = 600031261  # 主播2	15025800005	600031261

gs_A_rid_1 = 170000126  # A工会 工会id 8�?joy-man,已配�?=96%分成�?gs_A_rid_2 = 170000124  # A工会 工会id 直播�?已配�?96%分成�?
gs_B_ceo_uid = 600030905  # 公会�?15025800011	600030905
gs_B_room_owner_1_uid = 600044742  # 厅长1	15025800012	600044742
gs_B_room_owner_2_uid = 600001086  # 厅长2	15025800013	600001086
gs_B_uid_1 = 600006063  # 主播1	15025800014	600006063
gs_B_uid_2 = 600011936  # 主播2	15025800015	600011936

gs_B_rid_1 = 170000127  # A工会 工会id 8�?joy-woman,未配置分成比
gs_B_rid_2 = 170000125  # A工会 工会id 直播�?
normal_uid = 600042179  # 普通用�?收礼 15025800022	600042179

# 礼物配置
giftId = {
	"69": {  # 椰子�?100�?		"gid": 69,
		"cid": 329,
		"price": 100
	}
}
# 分成 config.bbs_room_gift_rate
rates = {
	"A-工会": {
		"room_1_config": {  # 本公会房�?已配置且<=96%,按配置规则分�?合计0.96 money_cash
			"anchor_rate": 0.81,  # 主播
			"owner_rate": 0.09,  # 房主
			"broker_rate": 0.06,  # 会长
		},
		"room_2_over_config": {  # 本公会房�?已配置且>96%超上�?兜底 主播0.94 money_cash
			"anchor_rate": 0.94,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
		"room_other": {  # 跨档 合计0.96 money_cash_b
			"anchor_rate": 0.8,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
	},
	"B-工会": {
		"room_1_not_config": {  # 本公会房�?未配�?兜底 主播0.94 money_cash
			"anchor_rate": 0.94,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
		"room_other": {  # 跨档 合计0.96 money_cash_b
			"anchor_rate": 0.8,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
	},
	"gs": {
		"slp-chat": {  # 不夜活跃用户,私聊 0.8 money_cash
			"anchor_rate": 0.6,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
		"slp-room": {  # 不夜活跃用户,私聊 0.8 money_cash
			"anchor_rate": 0.5,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0.1,  # 会长
		},
		"xsg-chat": {
			"gs_rate": 0.9,  # 小拾光新用户,私聊 主播 0.9 money_cash_b
			"gs_self_rate": 0.9,  # 主播,私聊,自刷
		},
		"xsg-vip-room": {  # 个人�?			"gs_rate": 0.9,  # 小拾光新用户,个人�?主播 0.9 money_cash_b
			"gs_self_rate": 0.9,  # 主播,个人�?自刷
		}
	},
	"normal_uid": {  # 普通用�?		"chat": {  # 私聊 0.90 money_cash_b
			"user_rate": 0.90,  # 用户
			"user_self_rate": 0.90,  # 用户,私聊,自刷
		},
		"room": {
			"user_rate": 0.90,  # 用户 # 房间 0.90 money_cash_b
			"user_self_rate": 0.94,  # 用户,房间,自刷 0.94 钻石/个人魅力值变成个人魅力值，公会魅力值变成公会魅力�?		},
		"xsg-vip-room": {  # 个人�?			"user_rate": 0.90,  # 用户 个人�?0.90 money_cash_b
			"user_self_rate": 0.94,  # 用户,个人�?自刷 0.94 钻石/个人魅力值变成个人魅力值，公会魅力值变成公会魅力�?		}
	}
}

# 爵位
juewei_level = {
	"normal_uid": {
		'�?: {
			'level': 10,
			'update': 100,
			'base': 0,
		},
		'�?: {
			'level': 20,
			'update': 100,
			'base': 60000,
		},
		'�?: {
			'level': 30,
			'update': 100,
			'base': 300000,
		},
		'�?: {
			'level': 40,
			'update': 105,
			'base': 1000000,
		},
		'�?: {
			'level': 50,
			'update': 110,
			'base': 4000000,
		},
		'�?: {
			'level': 60,
			'update': 115,
			'base': 10000000,
		},
		'�?: {
			'level': 70,
			'update': 120,
			'base': 25000000,
		},
		'�?: {
			'level': 80,
			'update': 125,
			'base': 60000000,
		},
		'�?: {
			'level': 90,
			'update': 130,
			'base': 200000000,
		},
		'�?: {
			'level': 100,
			'update': 140,
			'base': 800000000,
		},
	},
	"gs": {
		'�?: {
			'level': 10,
			'update': 100,
			'base': 0,
		},
		'�?: {
			'level': 20,
			'update': 100,
			'base': 20000,
		},
		'�?: {
			'level': 30,
			'update': 100,
			'base': 100000,
		},
		'�?: {
			'level': 40,
			'update': 105,
			'base': 300000,
		},
		'�?: {
			'level': 50,
			'update': 110,
			'base': 1200000,
		},
		'�?: {
			'level': 60,
			'update': 115,
			'base': 3000000,
		},
		'�?: {
			'level': 70,
			'update': 120,
			'base': 8000000,
		},
		'�?: {
			'level': 80,
			'update': 125,
			'base': 20000000,
		},
		'�?: {
			'level': 90,
			'update': 130,
			'base': 60000000,
		},
		'�?: {
			'level': 100,
			'update': 140,
			'base': 260000000,
		},
	}
}

# gs_B_ceo_uid = 600030905  # 15025800011	B公会�?bid=600030905
# gs_A_uid = gsUid = 200255399  # 15008520003	支付测试0003	A工会-成员
# gs_B_uid = 200250759  # 15008520004	支付测试0004	B工会-成员,星舰成员
# business_room_uid = 200254463  # 15008520005	商业房房�?不加工会,不签大神
# normal_uid = rewardUid = 200252072  # 15008520006	普通用�?普通用�?星舰成员
#
# gs_A_ceo_rid = gs_soundchat_rid = 100104323  # A工会-工会�?rid  商业-直播�?business-soundchat
# gs_A_ceo_rid_music = gs_music_rid = 100104333  # A工会-工会�?rid  商业-点唱/business-soundchat
# gs_B_ceo_rid = gs_friend_rid = 100104324  # B工会-工会�?rid  商业-标准9�?business-friend
# gs_A_rid = 100104325  # A工会-成员 rid  商业-直播�?business-soundchat
# gs_B_rid = 100104326  # B工会-成员 rid  商业-标准9�?business-friend
# business_room_rid = 100104327  # 商业房房�?rid  商业-标准9�?business-friend
#
# gs_A_ceo_pretty_rid = 100504535  # A工会-工会�?个人靓号�?靓号 6826
# gs_A_ceo_starship_rid = 100504581  # A工会-工会�?星舰�?rid
# gs_A_ceo_starship_sid = 300000119  # A工会-工会�?星舰id
# gs_A_ceo_starship_group_id = 300000153  # A工会-工会�?星舰对应的IM-id
#
# gs_A_ceo_talent_show_rid = 100504588  # A工会-工会�?商业-才艺�?rid
#
# # 麦位index
# microphone_num = {  # todo
# 	"接待": 0,
# 	"普�?: 1,
# 	"老板": 8,
# }
# # 礼物配置
# giftId = {
# 	"69": {  # 椰子�?100�?# 		"gid": 69,
# 		"cid": 329,
# 		"price": 100
# 	},
# 	"70": {  # 羽毛*300�?# 		"gid": 70,
# 		"cid": 330,
# 		"price": 300
# 	},
# 	"937": {  # 枫叶落书*600�?9折礼物优惠券(有损/无损)专用礼物
# 		"gid": 937,
# 		"cid": 21314,
# 		"price": 600
# 	},
# 	"211220": {  # 羽毛*300�?# 		"gid": 211220,
# 		"cid": None,
# 		"price": 100
# 	},
# 	"211026": {  # 冰封王座*1314000�?9折礼物优惠券(有损)专用礼物
# 		"gid": 211026,
# 		"cid": None,
# 		"price": 1314000
# 	},
# }
#
# commodityId = {
# 	'89297': {  # 9折礼物优惠券-有损,9�?# 		'cid': 89297,
# 		'discount': 0.1  # 100-10=90
# 	},
# 	'89370': {  # 9折礼物优惠券,9�?# 		'cid': 89370,
# 		'discount': 0.1  # 100-10=90
# 	},
# }
#
# room_defend = {  # 房间守护
# 	'chunai': {  # 纯爱
# 		'week': {
# 			'knight_level': 1,
# 			'duration_level': 1,
# 			'price': 9900,
# 		},
# 		'month': {
# 			'knight_level': 1,
# 			'duration_level': 2,
# 			'price': 29900,
# 		},
# 		'year': {
# 			'knight_level': 1,
# 			'duration_level': 3,
# 			'price': 299000,
# 		}
# 	},
# 	'zhenai': {  # 真爱
# 		'week': {
# 			'knight_level': 2,
# 			'duration_level': 1,
# 			'price': 28800,
# 		},
# 		'month': {
# 			'knight_level': 2,
# 			'duration_level': 2,
# 			'price': 99900,
# 		},
# 		'year': {
# 			'knight_level': 2,
# 			'duration_level': 3,
# 			'price': 999000,
# 		},
# 	},
# 	'zhiai': {  # 挚爱
# 		'week': {
# 			'knight_level': 3,
# 			'duration_level': 1,
# 			'price': 88800,
# 		},
# 		'month': {
# 			'knight_level': 3,
# 			'duration_level': 2,
# 			'price': 299900,
# 		},
# 		'year': {
# 			'knight_level': 3,
# 			'duration_level': 3,
# 			'price': 29999000,
# 		},
# 	},
# }
# defend = {  # 个人守护
# 	"CP": {
# 		"id": 1,
# 		"price": 520000,
# 		"upgrade_price": 520000,
# 		"break_price": 99900,
#
# 	},
# 	"小宝�?: {
# 		"id": 2,
# 		"price": 52000,
# 		"upgrade_price": 99900,
# 		"break_price": 28800,
# 	},
# 	"知己": {
# 		"id": 3,
# 		"price": 52000,
# 		"upgrade_price": 99900,
# 		"break_price": 28800,
# 	},
# 	"守卫": {
# 		"id": 4,
# 		"price": 36000,
# 		"upgrade_price": 66600,
# 		"break_price": 28800,
# 	},
# 	"队友": {
# 		"id": 5,
# 		"price": 6600,
# 		"upgrade_price": 66600,
# 		"break_price": 28800,
# 	},
# 	"跟班": {
# 		"id": 6,
# 		"price": 36000,
# 		"upgrade_price": 9900,
# 		"break_price": 28800,
# 	},
# 	"闺蜜": {
# 		"id": 7,
# 		"price": 52000,
# 		"upgrade_price": 520000,
# 		"break_price": 28800,
# 	},
# 	"兄弟": {
# 		"id": 8,
# 		"price": 36000,
# 		"upgrade_price": 66600,
# 		"break_price": 28800,
# 	},
# }
# # 分成比例
# rates = {
# 	# 主播,mc
# 	'gs': {
# 		"default": 0.6,  # 默认,直播/商业�?靓号�?个播房间守护/才艺厅麦�?mc
# 		# "viproom": 0.75,  # 个人�?mcb
# 		# "chat": 0.75,  # 私聊 mcb
# 		# "starship-room": 0.75,  # 星舰�?mcb
# 		# "starship-im": 0.75,  # 星舰群聊 mcb
# 		# "other_room": 0,  # 跨档
# 		# "room": 0,  # 房间
# 		# "defend": 0,  # 个人守护
# 		# "room_defend": 0,  # 直播房间守护
# 	},
# 	# 普通用�?mcb
# 	'normal': {
# 		"default": 0.6,  # 默认,直播/商业�?靓号�?个播房间守护/才艺厅麦�?mcb
# 		# "viproom": 0.8,  # 个人�?mcb
# 		# "chat": 0.8,  # 私聊 mcb
# 		# "starship-room": 0.8,  # 星舰�?mcb
# 		# "starship-im": 0.8,  # 星舰群聊 mcb
# 		# "room": 0,  # 房间
# 		# "chat": 0,  # 私聊
# 		# "defend": 0,  # 个人守护
# 	},
# 	# 星舰�?星舰群聊/个人�?私聊 不根�?用户身份判定,根据外显�?VIP/人气标签 来判�?# 	# 需求文�?# 	# """https://docs.google.com/document/d/1UTRvszzmh2jz_CLfokJsISEgAWd9vxgodNNbXGwpS54/edit?tab=t.0"""
# 	"vip": {
# 		"viproom": 0.8,  # 个人�?mcb
# 		"chat": 0.8,  # 私聊 mcb
# 		"starship-room": 0.8,  # 星舰�?mcb
# 		"starship-im": 0.8,  # 星舰群聊 mcb
# 	},
# 	"pop": {
# 		"viproom": 0.8,  # 个人�?mcb
# 		"chat": 0.8,  # 私聊 mcb
# 		"starship-room": 0.8,  # 星舰�?mcb
# 		"starship-im": 0.8,  # 星舰群聊 mcb
# 	}
# }
# # 爵位
# juewei_level = {
# 	'骑士': {
# 		'level': 10,
# 		'update': 100,
# 		'base': 0,
# 	},
# 	'男爵': {
# 		'level': 20,
# 		'update': 100,
# 		'base': 20000,
# 	},
# 	'子爵': {
# 		'level': 30,
# 		'update': 100,
# 		'base': 800000,
# 	},
# 	'伯爵': {
# 		'level': 40,
# 		'update': 105,
# 		'base': 250000,
# 	},
# 	'侯爵': {
# 		'level': 50,
# 		'update': 110,
# 		'base': 1000000,
# 	},
# 	'公爵': {
# 		'level': 60,
# 		'update': 115,
# 		'base': 2500000,
# 	},
# 	'亲王': {
# 		'level': 70,
# 		'update': 120,
# 		'base': 6500000,
# 	},
# 	'国王': {
# 		'level': 80,
# 		'update': 125,
# 		'base': 15000000,
# 	},
# 	'皇帝': {
# 		'level': 90,
# 		'update': 130,
# 		'base': 50000000,
# 	},
# }
# zx_box = {
# 	'6': {
# 		"gid": '210788',
# 		"price": 600,
# 		# "max_price": 52000
# 		"210774": {
# 			"price": 300,
# 			"RQ": 1,  # 人气倍率
# 			"VIP": 1,  # VIP倍率
# 			"CZZ": 0  # 贵族倍率
# 		},
# 		"210775": {
# 			"price": 600,
# 			"RQ": 1,
# 			"VIP": 1,
# 			"CZZ": 0
# 		},
# 		"210776": {
# 			"price": 1000,
# 			"RQ": 1,
# 			"VIP": 1,
# 			"CZZ": 0
# 		},
# 		"210785": {
# 			"price": 18800,
# 			"RQ": 1,
# 			"VIP": 2,
# 			"CZZ": 1
# 		},
# 		"210786": {
# 			"price": 52000,
# 			"RQ": 1,
# 			"VIP": 3,
# 			"CZZ": 1
# 		},
# 	}
# }
#
# # ==================== 语义化常�?====================
# # 默认测试礼物（椰子水*100钻）
# DEFAULT_GIFT = giftId['69']
# DEFAULT_GIFT_ID = DEFAULT_GIFT['gid']
# DEFAULT_GIFT_PRICE = DEFAULT_GIFT['price']
# DEFAULT_GIFT_CID = DEFAULT_GIFT['cid']
#
# # 分成比例快捷访问
# RATE_GS_DEFAULT = rates['gs']['default']  # 公会主播默认分成 60%
# RATE_NORMAL_DEFAULT = rates['normal']['default']  # 普通用户默认分�?60%
# RATE_VIP_CHAT = rates['vip']['chat']  # VIP私聊分成 80%
# RATE_VIP_ROOM = rates['vip']['viproom']  # VIP个人房分�?80%
# RATE_POP_CHAT = rates['pop']['chat']  # 人气私聊分成 80%
# RATE_POP_ROOM = rates['pop']['viproom']  # 人气个人房分�?80%
# RATE_POP_STARSHIP_ROOM = rates['pop']['starship-room']  # 人气星舰房分�?80%
# RATE_POP_STARSHIP_IM = rates['pop']['starship-im']  # 人气星舰群聊分成 80%
#
# # 点歌单价
# unit_price = 3000
# # 歌单
# order_songs_list = [100200,100201,100202]
# #  冠歌
# naming_song_config = {
# 	"2": {"money": 28800, "multiple_id": 1001, "gift_id": 211030, "money_pay": 28800},
# 	"3": {"money": 334400, "multiple_id": 1004, "gift_id": 211576, "money_pay": 334400},
# 	"5": {"money": 666600, "multiple_id": 1005, "gift_id": 211024, "money_pay": 666600},
# 	"7": {"money": 999900, "multiple_id": 1006, "gift_id": 210853, "money_pay": 999900},
#
# 	"5-上架": {"money": 668800, "multiple_id": 1005, "gift_id": 211576, "money_pay": 334400, "cid": 100915},  # 上架状�?# 	"5-下架": {"money": 668800, "multiple_id": 1005, "gift_id": 316, "money_pay": 334400, "cid": 2000},  # 下架状�?#
# }
# # # # 角色配置 todo
# # live_role = {
# # 	'pack_ceo': 105002314,  # 直播公会公会�?# # 	'pack_master_NoPack': 105002319,  # 非公会一代宗师主�?# # 	'pack_cal_uid': 105002313,  # 公会签约主播（打包结算），宗师等级可设置为一代和非一�?# # 	'live_rid': 193185577,  # 直播�?types=live)，房�?105002313
# # 	'auto_rid': 193185484,  # business | types: auto | room_factory_type: business-content | settlement_channel: cp-women
# # }
# # # 被打赏者（一代宗师） todo
# # masterUid = 100500338
#
# # 才艺厅观众位配置
# talent_show_config = {
# 	"真爱": {
# 		"1": {
# 			"position": 1,
# 			"price_id": 1001,
# 			"price": 6600
# 		},
# 		"2": {
# 			"position": 1,
# 			"price_id": 1002,
# 			"price": 18800
# 		},
# 		"3": {
# 			"position": 1,
# 			"price_id": 1003,
# 			"price": 99900
# 		},
# 	},
# 	"爆灯": {},
# 	"应援": {},
# }
