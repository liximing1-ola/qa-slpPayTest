# 打赏人
from common.Config import config as old_config

pay_url = old_config.xsg_pay_url
default_num = 1  # 礼物个数
default_money = 1000000  # 打赏者默认金额
payUid = 600041937  # 15025800021

gs_A_bid = 600041992  # A工会 工会id
gs_B_bid = 600030905  # B工会 工会id

gs_A_ceo_uid = 600041992  # 公会长	15025800001	600041992
gs_A_room_owner_1_uid = 600042759  # 厅长1	15025800002	600042759
gs_A_room_owner_2_uid = 600030957  # 厅长2	15025800003	600030957
gs_A_uid_1 = gsUid = 600005148  # 主播1	15025800004	600005148
gs_A_uid_2 = 600031261  # 主播2	15025800005	600031261

gs_A_rid_1 = 170000126  # A工会 工会id 8麦,joy-man,已配置<=96%分成比
gs_A_rid_2 = 170000124  # A工会 工会id 直播房,已配置>96%分成比

gs_B_ceo_uid = 600030905  # 公会长	15025800011	600030905
gs_B_room_owner_1_uid = 600044742  # 厅长1	15025800012	600044742
gs_B_room_owner_2_uid = 600001086  # 厅长2	15025800013	600001086
gs_B_uid_1 = 600006063  # 主播1	15025800014	600006063
gs_B_uid_2 = 600011936  # 主播2	15025800015	600011936

gs_B_rid_1 = 170000127  # A工会 工会id 8麦,joy-woman,未配置分成比
gs_B_rid_2 = 170000125  # A工会 工会id 直播房

normal_uid = 600042179  # 普通用户-收礼 15025800022	600042179

# 礼物配置
giftId = {
	"69": {  # 椰子水*100钻
		"gid": 69,
		"cid": 329,
		"price": 100
	}
}
# 分成 config.bbs_room_gift_rate
rates = {
	"A-工会": {
		"room_1_config": {  # 本公会房间,已配置且<=96%,按配置规则分成 合计0.96 money_cash
			"anchor_rate": 0.81,  # 主播
			"owner_rate": 0.09,  # 房主
			"broker_rate": 0.06,  # 会长
		},
		"room_2_over_config": {  # 本公会房间,已配置且>96%超上限,兜底 主播0.94 money_cash
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
		"room_1_not_config": {  # 本公会房间,未配置 兜底 主播0.94 money_cash
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
		"xsg-vip-room": {  # 个人房
			"gs_rate": 0.9,  # 小拾光新用户,个人房 主播 0.9 money_cash_b
			"gs_self_rate": 0.9,  # 主播,个人房,自刷
		}
	},
	"normal_uid": {  # 普通用户
		"chat": {  # 私聊 0.90 money_cash_b
			"user_rate": 0.90,  # 用户
			"user_self_rate": 0.90,  # 用户,私聊,自刷
		},
		"room": {
			"user_rate": 0.90,  # 用户 # 房间 0.90 money_cash_b
			"user_self_rate": 0.94,  # 用户,房间,自刷 0.94 钻石/个人魅力值变成个人魅力值，公会魅力值变成公会魅力值
		},
		"xsg-vip-room": {  # 个人房
			"user_rate": 0.90,  # 用户 个人房 0.90 money_cash_b
			"user_self_rate": 0.94,  # 用户,个人房,自刷 0.94 钻石/个人魅力值变成个人魅力值，公会魅力值变成公会魅力值
		}
	}
}

# 爵位
juewei_level = {
	"normal_uid": {
		'隐': {
			'level': 10,
			'update': 100,
			'base': 0,
		},
		'轩': {
			'level': 20,
			'update': 100,
			'base': 60000,
		},
		'楼': {
			'level': 30,
			'update': 100,
			'base': 300000,
		},
		'阁': {
			'level': 40,
			'update': 105,
			'base': 1000000,
		},
		'堂': {
			'level': 50,
			'update': 110,
			'base': 4000000,
		},
		'宫': {
			'level': 60,
			'update': 115,
			'base': 10000000,
		},
		'殿': {
			'level': 70,
			'update': 120,
			'base': 25000000,
		},
		'帝': {
			'level': 80,
			'update': 125,
			'base': 60000000,
		},
		'仙': {
			'level': 90,
			'update': 130,
			'base': 200000000,
		},
		'神': {
			'level': 100,
			'update': 140,
			'base': 800000000,
		},
	},
	"gs": {
		'隐': {
			'level': 10,
			'update': 100,
			'base': 0,
		},
		'轩': {
			'level': 20,
			'update': 100,
			'base': 20000,
		},
		'楼': {
			'level': 30,
			'update': 100,
			'base': 100000,
		},
		'阁': {
			'level': 40,
			'update': 105,
			'base': 300000,
		},
		'堂': {
			'level': 50,
			'update': 110,
			'base': 1200000,
		},
		'宫': {
			'level': 60,
			'update': 115,
			'base': 3000000,
		},
		'殿': {
			'level': 70,
			'update': 120,
			'base': 8000000,
		},
		'帝': {
			'level': 80,
			'update': 125,
			'base': 20000000,
		},
		'仙': {
			'level': 90,
			'update': 130,
			'base': 60000000,
		},
		'神': {
			'level': 100,
			'update': 140,
			'base': 260000000,
		},
	}
}

