# 打赏人
from common.Config import config as old_config

pay_url = old_config.slp_pay_url
default_num = 1  # 礼物个数
default_money = 1000000  # 打赏者默认金额
payUid = 200254777  # 15008520000	支付测试0000	打赏者/Basic.yml 登录session 星舰成员
payUid_subsidiary = 200251538  # 15008520008	支付测试0008	打赏者-小号(同安全手机号)
payUid_subsidiary2 = 200251096  # 15008520009	支付测试0009	打赏者-小号(同实名认证,现在可以认证5个账号)

gs_A_bid = 200255209  # A工会 工会id
gs_B_bid = 200251746  # B工会 工会id

gs_A_ceo_uid = 200255209  # 15008520001	支付测试0001	A公会长 bid=200255209,星舰首席
gs_B_ceo_uid = 200251746  # 15008520002	支付测试0002	B公会长 bid=200251746
gs_A_uid = gsUid = 200255399  # 15008520003	支付测试0003	A工会-成员,歌手身份,星舰成员
gs_B_uid = 200250759  # 15008520004	支付测试0004	B工会-成员,星舰成员
business_room_uid = 200254463  # 15008520005	商业房房主 不加工会,不签大神
normal_uid = rewardUid = 200252072  # 15008520006	普通用户	普通用户,星舰成员

gs_A_ceo_rid = gs_soundchat_rid = 100104323  # A工会-工会长 rid  商业-直播厅/business-soundchat
gs_A_ceo_rid_music = gs_music_rid = 100104333  # A工会-工会长 rid  商业-点唱/business-soundchat
gs_B_ceo_rid = gs_friend_rid = 100104324  # B工会-工会长 rid  商业-标准9麦/business-friend
gs_A_rid = 100104325  # A工会-成员 rid  商业-直播厅/business-soundchat
gs_B_rid = 100104326  # B工会-成员 rid  商业-标准9麦/business-friend
business_room_rid = 100104327  # 商业房房主 rid  商业-标准9麦/business-friend

gs_A_ceo_pretty_rid = 100504535  # A工会-工会长 个人靓号房 靓号 6826
gs_A_ceo_starship_rid = 100504581  # A工会-工会长 星舰房 rid
gs_A_ceo_starship_sid = 300000119  # A工会-工会长 星舰id
gs_A_ceo_starship_group_id = 300000153  # A工会-工会长 星舰对应的IM-id

gs_A_ceo_talent_show_rid = 100504588  # A工会-工会长 商业-才艺厅 rid
#################
gs_A_rid_1 = 170000211  # A工会 8麦,joy-man,已配置<=80%分成比,71:6:3
gs_A_rid_2 = 170000212  # A工会 派单房,已配置<=80%分成比,74:3:3
gs_A_rid_3 = 170000215  # A工会 8麦,已配置>80%分成比,72:6:3
gs_A_rid_4 = 170000216  # A工会 点唱,未配置
gs_A_rid_5 = 170000217  # A工会 树洞,未配置
gs_A_rid_6 = 170000266  # A工会 连连看,已配置<=80%分成比,72:5:3
gs_A_rid_7 = 170000267  # A工会 踢保(拍卖),已配置<=80%分成比,73:5:2
gs_A_rid_8 = 170000268  # A工会 连连看,未配置
gs_A_rid_9 = 170000269  # A工会 踢保(拍卖),未配置
gs_A_rid_10 = 170000271  # A工会 连连看,已配置>80%分成比,72:6:3
gs_A_rid_11 = 170000270  # A工会 踢保(拍卖),已配置>80%分成比,72:6:3
gs_A_room_owner_1_uid = 200258475  # A工会 厅长1	15008520010	200258475

gs_B_rid_1 = 170000214  # B工会 8麦,joy-man,已配置<=80%分成比,71:6:3
gs_B_rid_2 = 170000213  # B工会 派单房,已配置<=80%分成比,55:20:5
gs_B_rid_3 = 170000218   # B工会 8麦,已配置>80%分成比,72:6:3
gs_B_rid_4 = 170000219  # B工会 点唱,未配置
gs_B_rid_5 = 170000220  # B工会 树洞,未配置
gs_B_room_owner_1_uid = 200259074  # B工会 厅长1	15008520013	200259074
#################
# 麦位index
microphone_num = {  # todo
	"接待": 0,
	"普通": 1,
	"老板": 8,
}
# 礼物配置
giftId = {
	"69": {  # 椰子水*100钻
		"gid": 69,
		"cid": 329,
		"price": 100
	},
	"70": {  # 羽毛*300钻
		"gid": 70,
		"cid": 330,
		"price": 300
	},
	"937": {  # 枫叶落书*600钻,9折礼物优惠券(有损/无损)专用礼物
		"gid": 937,
		"cid": 21314,
		"price": 600
	},
	"211220": {  # 羽毛*300钻
		"gid": 211220,
		"cid": None,
		"price": 100
	},
	"211026": {  # 冰封王座*1314000钻,9折礼物优惠券(有损)专用礼物
		"gid": 211026,
		"cid": None,
		"price": 1314000
	},
}

commodityId = {
	'89297': {  # 9折礼物优惠券-有损,9折
		'cid': 89297,
		'discount': 0.1  # 100-10=90
	},
	'89370': {  # 9折礼物优惠券,9折
		'cid': 89370,
		'discount': 0.1  # 100-10=90
	},
}

room_defend = {  # 房间守护
	'chunai': {  # 纯爱
		'week': {
			'knight_level': 1,
			'duration_level': 1,
			'price': 9900,
		},
		'month': {
			'knight_level': 1,
			'duration_level': 2,
			'price': 29900,
		},
		'year': {
			'knight_level': 1,
			'duration_level': 3,
			'price': 299000,
		}
	},
	'zhenai': {  # 真爱
		'week': {
			'knight_level': 2,
			'duration_level': 1,
			'price': 28800,
		},
		'month': {
			'knight_level': 2,
			'duration_level': 2,
			'price': 99900,
		},
		'year': {
			'knight_level': 2,
			'duration_level': 3,
			'price': 999000,
		},
	},
	'zhiai': {  # 挚爱
		'week': {
			'knight_level': 3,
			'duration_level': 1,
			'price': 88800,
		},
		'month': {
			'knight_level': 3,
			'duration_level': 2,
			'price': 299900,
		},
		'year': {
			'knight_level': 3,
			'duration_level': 3,
			'price': 29999000,
		},
	},
}
defend = {  # 个人守护
	"CP": {
		"id": 1,
		"price": 520000,
		"upgrade_price": 520000,
		"break_price": 99900,

	},
	"小宝贝": {
		"id": 2,
		"price": 52000,
		"upgrade_price": 99900,
		"break_price": 28800,
	},
	"知己": {
		"id": 3,
		"price": 52000,
		"upgrade_price": 99900,
		"break_price": 28800,
	},
	"守卫": {
		"id": 4,
		"price": 36000,
		"upgrade_price": 66600,
		"break_price": 28800,
	},
	"队友": {
		"id": 5,
		"price": 6600,
		"upgrade_price": 66600,
		"break_price": 28800,
	},
	"跟班": {
		"id": 6,
		"price": 36000,
		"upgrade_price": 9900,
		"break_price": 28800,
	},
	"闺蜜": {
		"id": 7,
		"price": 52000,
		"upgrade_price": 520000,
		"break_price": 28800,
	},
	"兄弟": {
		"id": 8,
		"price": 36000,
		"upgrade_price": 66600,
		"break_price": 28800,
	},
}
# 分成比例
rates = {
	# 主播,mc
	'gs': {
		"default": 0.7,  # 默认,直播/商业厅/个播房间守护/才艺厅麦位 mc
		"vip-pretty-room": 0.8,  # 个人靓号房 mc
		"as_normal": 0.8,  # 在工会且签署大神 缺一不可,否则按照普通用户比例分成 mcb

		"room-self": 0.8,  # 默认,商业房 自刷 mc
		"vip-room-self": 0.9,  # # 默认,个人房 自刷 mcb
		"vip-pretty-room-self": 0.8,  # 个人靓号房 自刷,mc
		"chat-self": 0.9,  # 个人靓号房 自刷,mcb
	},
	# 普通用户,mcb
	'normal': {
		"default": 0.8,  # 默认,直播/商业厅/个播房间守护/才艺厅麦位 mcb
		"vip-pretty-room": 0.9,  # 个人靓号房 mcb

		"room-self": 0.8,  # 默认,商业房 自刷 mcb
		"vip-room-self": 0.9,  # # 默认,个人房 自刷 mcb
		"vip-pretty-room-self": 0.9,  # 个人靓号房 自刷,mcb
		"chat-self": 0.9,  # 个人靓号房 自刷,mcb
	},
	# 星舰房/星舰群聊/个人房/私聊 不根据 用户身份判定,根据外显的 VIP/人气标签 来判断
	# 需求文档
	# """https://docs.google.com/document/d/1UTRvszzmh2jz_CLfokJsISEgAWd9vxgodNNbXGwpS54/edit?tab=t.0"""
	"vip": {
		"viproom": 0.9,  # 个人房 mcb
		"chat": 0.9,  # 私聊 mcb
		"starship-room": 0.9,  # 星舰房 mcb
		"starship-im": 0.9,  # 星舰群聊 mcb
	},
	"pop": {
		"viproom": 0.9,  # 个人房 mcb
		"chat": 0.9,  # 私聊 mcb
		"starship-room": 0.9,  # 星舰房 mcb
		"starship-im": 0.9,  # 星舰群聊 mcb
	},
	"A-工会": {
		"room_1_config": {  # 本公会房间,8麦,已配置且<=80%,按配置规则分成 合计0.80 money_cash
			"anchor_rate": 0.71,  # 主播
			"owner_rate": 0.06,  # 房主
			"broker_rate": 0.03,  # 会长
		},
		"room_2_config": {  # 本公会房间,派单,已配置且<=80%,按配置规则分成 合计0.80 money_cash
			"anchor_rate": 0.74,  # 主播
			"owner_rate": 0.03,  # 房主
			"broker_rate": 0.03,  # 会长
		},
		"room_6_config": {  # 本公会房间,连连看,已配置且<=80%,按配置规则分成 合计0.80 money_cash
			"anchor_rate": 0.72,  # 主播
			"owner_rate": 0.05,  # 房主
			"broker_rate": 0.03,  # 会长
		},
		"room_7_config": {  # 本公会房间,踢保(拍卖),已配置且<=80%,按配置规则分成 合计0.80 money_cash
			"anchor_rate": 0.73,  # 主播
			"owner_rate": 0.05,  # 房主
			"broker_rate": 0.02,  # 会长
		},
	},
	"other-broker-not-slporder": {  # 跨档,非派单厅
		"last_week_room_1_config": {  # 上周房存在 已配置且<=80%,且主播>=60%,按跨档最高60%规则分成 money_cash
			"anchor_rate": 0.60,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},
		"last_week_room_2_config": {  # 上周房存在 已配置且<=80%,且主播<60%,按配置规则分成 money_cash
			"anchor_rate": 0.55,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		},

	},
	"other-broker-slporder": {  # 跨档,派单厅
		"last_week_room_1_config": {  # 上周房存在 已配置且<=80%,且主播>=60%,按配置规则分成 money_cash
			"anchor_rate": 0.71,  # 主播
			"owner_rate": 0.06,  # 房主
			"broker_rate": 0.03,  # 会长
		},
		"last_week_room_none": {  # 上周房不存在 特殊规则 money_cash
			"anchor_rate": 0.6,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0.2,  # 会长=0.8-主播=0.2
		},
	},
	"settlement_channel_config": {  # 结算频道 兜底规则
		# 点唱	76	0	4
		# 游戏/派单	70	0	10
		# 直播	70	0	10
		# 情感男	76	0	4
		# 情感女	70	0	10
		# 连连看/踢保	76	0	4
		# 无结算频道兜底	70	0%	0
		'music': {  # 点唱
			"anchor_rate": 0.76,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0.04,  # 会长
		},
		'cplink': {  # 连连看
			"anchor_rate": 0.76,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0.04,  # 会长
		},
		'play': {  # 踢保
			"anchor_rate": 0.76,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0.04,  # 会长
		},
		# todo 没有列举所有配置
		'other': {  # 其他未配置的结算频道兜底
			"anchor_rate": 0.60,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		}
	},
	"base_config": {
		"base": {
			"anchor_rate": 0.60,  # 主播
			"owner_rate": 0,  # 房主
			"broker_rate": 0,  # 会长
		}
	}
}
# 爵位
juewei_level = {
	'骑士': {
		'level': 10,
		'update': 100,
		'base': 0,
	},
	'男爵': {
		'level': 20,
		'update': 100,
		'base': 20000,
	},
	'子爵': {
		'level': 30,
		'update': 100,
		'base': 800000,
	},
	'伯爵': {
		'level': 40,
		'update': 105,
		'base': 250000,
	},
	'侯爵': {
		'level': 50,
		'update': 110,
		'base': 1000000,
	},
	'公爵': {
		'level': 60,
		'update': 115,
		'base': 2500000,
	},
	'亲王': {
		'level': 70,
		'update': 120,
		'base': 6500000,
	},
	'国王': {
		'level': 80,
		'update': 125,
		'base': 15000000,
	},
	'皇帝': {
		'level': 90,
		'update': 130,
		'base': 50000000,
	},
}
zx_box = {
	'6': {
		"gid": '210788',
		"price": 600,
		# "max_price": 52000
		"210774": {
			"price": 300,
			"RQ": 1,  # 人气倍率
			"VIP": 1,  # VIP倍率
			"CZZ": 0  # 贵族倍率
		},
		"210775": {
			"price": 600,
			"RQ": 1,
			"VIP": 1,
			"CZZ": 0
		},
		"210776": {
			"price": 1000,
			"RQ": 1,
			"VIP": 1,
			"CZZ": 0
		},
		"210785": {
			"price": 18800,
			"RQ": 1,
			"VIP": 2,
			"CZZ": 1
		},
		"210786": {
			"price": 52000,
			"RQ": 1,
			"VIP": 3,
			"CZZ": 1
		},
	}
}

# ==================== 语义化常量 ====================
# 默认测试礼物（椰子水*100钻）
DEFAULT_GIFT = giftId['69']
DEFAULT_GIFT_ID = DEFAULT_GIFT['gid']
DEFAULT_GIFT_PRICE = DEFAULT_GIFT['price']
DEFAULT_GIFT_CID = DEFAULT_GIFT['cid']

# 分成比例快捷访问
RATE_GS_DEFAULT = rates['gs']['default']  # 公会主播默认分成 60%
RATE_NORMAL_DEFAULT = rates['normal']['default']  # 普通用户默认分成 60%
RATE_VIP_CHAT = rates['vip']['chat']  # VIP私聊分成 80%
RATE_VIP_ROOM = rates['vip']['viproom']  # VIP个人房分成 80%
RATE_POP_CHAT = rates['pop']['chat']  # 人气私聊分成 80%
RATE_POP_ROOM = rates['pop']['viproom']  # 人气个人房分成 80%
RATE_POP_STARSHIP_ROOM = rates['pop']['starship-room']  # 人气星舰房分成 80%
RATE_POP_STARSHIP_IM = rates['pop']['starship-im']  # 人气星舰群聊分成 80%

# 点歌单价
unit_price = 3000
# 歌单
order_songs_list = [100200,100201,100202]
#  冠歌
naming_song_config = {
	"2": {"money": 28800, "multiple_id": 1001, "gift_id": 211030, "money_pay": 28800},
	"3": {"money": 334400, "multiple_id": 1004, "gift_id": 211576, "money_pay": 334400},
	"5": {"money": 666600, "multiple_id": 1005, "gift_id": 211024, "money_pay": 666600},
	"7": {"money": 999900, "multiple_id": 1006, "gift_id": 210853, "money_pay": 999900},

	"5-上架": {"money": 668800, "multiple_id": 1005, "gift_id": 211576, "money_pay": 334400, "cid": 100915},  # 上架状态
	"5-下架": {"money": 668800, "multiple_id": 1005, "gift_id": 316, "money_pay": 334400, "cid": 2000},  # 下架状态

}
# # # 角色配置 todo
# live_role = {
# 	'pack_ceo': 105002314,  # 直播公会公会长
# 	'pack_master_NoPack': 105002319,  # 非公会一代宗师主播
# 	'pack_cal_uid': 105002313,  # 公会签约主播（打包结算），宗师等级可设置为一代和非一代
# 	'live_rid': 193185577,  # 直播间(types=live)，房主:105002313
# 	'auto_rid': 193185484,  # business | types: auto | room_factory_type: business-content | settlement_channel: cp-women
# }
# # 被打赏者（一代宗师） todo
# masterUid = 100500338

# 才艺厅观众位配置
talent_show_config = {
	"真爱": {
		"1": {
			"position": 1,
			"price_id": 1001,
			"price": 6600
		},
		"2": {
			"position": 1,
			"price_id": 1002,
			"price": 18800
		},
		"3": {
			"position": 1,
			"price_id": 1003,
			"price": 99900
		},
	},
	"爆灯": {},
	"应援": {},
}
