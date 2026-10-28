# -*- encoding=utf8 -*-
"""并发与幂等用例的配置：账号组与阈值

与 caseSlp/config.py 唯一的区别是账号组：并发打赏必须「一人一账号」。
同一账号并发会被服务端频控挡在入口，测出来的是限流而不是并发。

账号直接复用 caseSlp 的真实数据，不另造一套：这样余额重置、礼物价格、房间号
与主流程用例的口径完全一致，出问题时能拿主流程的结论对照。
"""
from caseSlp.config import (default_num, giftId, gs_A_ceo_uid, gs_A_rid_1, gs_A_uid, gs_B_uid,
                            normal_uid, payUid)
# pay_url 本文件不用，只给用例从这里取（与 caseSlp/tools.py 的转发同一意图），标 noqa 免得被当残留
from caseSlp.config import pay_url  # noqa:F401

# 并发付款方：四个真实账号，各持自己的 token 同时下单
CONCURRENT_PAYERS = (payUid, gs_B_uid, gs_A_ceo_uid, normal_uid)
# 收礼方与房间：歌手身份 + 商业房，与主流程 test_gs_room 同一套
ANCHOR_UID = gs_A_uid
ROOM_RID = gs_A_rid_1
# 单笔订单的礼物与金额：礼物 69 单价最低、无优惠券，扣款渠道只有 money，便于守恒对账
GIFT = giftId['69']
PAY_AMOUNT = giftId['69']['price'] * default_num
# 重复提交次数：同一份请求体连发几次（模拟客户端超时重发）
REPEAT_TIMES = 3
