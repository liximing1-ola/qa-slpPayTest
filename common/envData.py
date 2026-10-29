# coding=utf-8
"""环境种子数据清单：跑用例之前必须存在的「造不出来」的那部分

余额、背包、等级、人气、上周厅都能由用例前置重造（prepare_test_data / reset_room_acs /
prepare_vip_pop_data / prepare_acceleration_card），这些丢了不算事故，下一轮自己就长回来。
但账号、房间、工会关系、礼物配置是造数的前提——账号被删时连 update 都无从下手，
礼物 69 没了这一单直接下不出去。

所以只查这几张「种子表」，而且只查最小集。取舍是明确的：
漏掉一个账号的代价是一条用例红且排查方向明确；误把不存在的资产写进清单，会让闸门
每天误拦整轮回归，那比不检查更糟。所以下面每一项都是当前用例真正依赖的账号/房间/礼物。

测试库固定为 xianshi，跨库表（config）写全限定；表名不带库前缀的写法在既有 SQL 里也存在，
这里统一全限定，避免换了连接参数就查不到表。
"""
from caseSlp.config import (business_room_rid, business_room_uid, gs_A_bid, gs_A_ceo_rid,
                            gs_A_ceo_uid, gs_A_rid_1, gs_A_uid, gs_B_bid, gs_B_ceo_uid,
                            gs_B_uid, giftId, normal_uid, payUid, payUid_subsidiary,
                            payUid_subsidiary2)

# 核心账号：每个都单独点名，缺谁报谁。打赏方三兄弟 + 两工会会长 + 两工会成员 + 房主 + 普通用户
SEED_USERS = (payUid, payUid_subsidiary, payUid_subsidiary2, gs_A_ceo_uid, gs_B_ceo_uid,
              gs_A_uid, gs_B_uid, business_room_uid, normal_uid)
# 房间：主流程、分成、并发用例都用这几个厅
SEED_ROOMS = (gs_A_rid_1, gs_A_ceo_rid, business_room_rid)
# 工会：跨档与本工会分成的比例侧由工会决定，两边都要参与断言
SEED_BROKERS = (gs_A_bid, gs_B_bid)
# 礼物：69 号（椰子水 100 钻）是并发与主流程共用的最小额礼物
SEED_GIFTS = (giftId['69']['gid'],)


def seed_checks():
    """返回 [(名称, 查存在的 SQL, 期望 id 元组, 缺失提示, 是否阻断), ...]

    每个 SQL 都是 `select <主键> from <表> where <主键> in (...)`，回来的行与期望做差集，
    报告里就能直接点名「缺 uid=200250759」，而不是「少 1 个」让人自己去数。

    工会一项标为不阻断：工会 id 与会长 uid 同号（gs_A_bid == gs_A_ceo_uid），若哪天有工会
    只建了账号没建工会行，把它做成硬拦截会挡住整轮回归；作为警告仍然能让人看见。
    """
    return [
        ('账号', 'select uid from xianshi.xs_user_index where uid in ({})', SEED_USERS,
         '恢复 xs_user_index / xs_user_profile / xs_user_mobile 快照', True),
        # 房间不加 deleted=0 过滤：gs_A_ceo_rid 实测 deleted 非 0，但 test_gs_room.test_011
        # 拿它跑得通（服务端按 rid 取 room_factory_type，不看 deleted）。加上这个条件会把
        # 一条正常用例判成环境缺失——体检误拦比不体检更糟
        ('房间', 'select rid from xianshi.xs_chatroom where rid in ({})', SEED_ROOMS,
         '恢复 xs_chatroom 快照（房间与 uid 绑定，只补 rid 不够）', True),
        ('礼物', 'select id from xianshi.xs_gift where id in ({})', SEED_GIFTS,
         '恢复 xs_gift 快照，主流程与并发用例都靠 69 号礼物下单', True),
        ('工会', 'select bid from xianshi.xs_broker where bid in ({})', SEED_BROKERS,
         '恢复 xs_broker / xs_broker_user 快照，分成比例依赖工会关系', False),
    ]
