import urllib.parse
from caseSlp.config import *


# 国内Slp消费场景
def encodeData(
        payType='package',
        money=giftId['69']['price'] * default_num,
        rid=business_room_rid,  # 商业标准9麦
        uid=rewardUid,
        giftId=giftId['69']['gid'],
        giftType='normal',
        cid=5,
        boxType='copper',
        num=default_num,
        package_cid=0,  # xs_user_commodity的id
        ctype='',
        duction_money=0,
        star=0,
        defend_id=244,
        uids=('{}'.format(rewardUid), '{}'.format(gsUid)),
        knight_level=room_defend['zhenai']['month']['knight_level'],
        duration_level=room_defend['zhenai']['month']['duration_level'],
        price=giftId['69']['price'],
        order_songs=None,
        naming_song=None,
        group_id=None,
        talent_show=None,
        display_page=0
):
    if naming_song is None:
        naming_song = {}
    if order_songs is None:
        order_songs = []

    if payType == 'chat-gift':
        data = {
            "platform": "available",
            "type": "chat-gift",
            "money": money,
            "params":
                {
                    "notify_group_id": 0,
                    "to": '{}'.format(uid),
                    "giftId": giftId,
                    "giftNum": num,
                    "cid": 0,
                    "ctype": "",
                    "duction_money": 0,
                    "version": 2,
                    "num": num,
                    "gift_type": "normal",
                    "star": star,
                    "show_pac_man_guide": 1,
                    "all_mic": 0,
                    "useCoin": -1,
                    "display_page":display_page
                },
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    if payType == 'package':
        data = {
            "platform": "available",
            "type": "package",
            "money": money,
            "params":
                {
                    "rid": rid,
                    "uids": '{}'.format(uid),
                    "positions": "1",
                    "position": -1,
                    "giftId": giftId,
                    "giftNum": num,
                    "price": price,
                    "cid": package_cid,
                    "ctype": ctype,
                    "duction_money": duction_money,
                    "version": 2,
                    "num": num,
                    "gift_type": "{}".format(giftType),
                    "star": star,
                    "show_pac_man_guide": 1,
                    "refer": "",
                    "all_mic": 0,
                    "useCoin": -1,
                    "display_page": display_page,
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'package-more':
        p = []
        uid = ','.join(uids)
        num_more = len(uids)
        for i in range(len(uids)):
            p.append(str(i + 1))
        position = ','.join(p)
        data = {
            "platform": "available",
            "type": "package",
            "money": money * num * num_more,
            "params":
                {
                    "rid": rid,
                    "uids": '{}'.format(uid),
                    "positions": "{}".format(position),
                    "position": -1,
                    "giftId": giftId,
                    "giftNum": num,
                    "price": price,
                    "cid": 0,
                    "ctype": "",
                    "duction_money": 0,
                    "version": 2,
                    "num": num_more * num,
                    "gift_type": "{}".format(giftType),
                    "useCoin": -1,
                    "star": star,
                    "show_pac_man_guide": 1,
                    "refer": "",
                    "all_mic": 0,
                    "display_page": display_page,
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'package-knightDefend':
        data = {
            "platform": "available",
            "type": "package",
            "money": money,
            "params":
                {
                    "price": price,
                    "knight_level": knight_level,
                    "duration_level": duration_level,
                    "rid": rid,
                    "uids": "{}".format(uid),
                    "useCoin": -1,
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'defend':
        data = {
            "platform": 'available',
            "type": 'defend',
            "money": money,
            "params":
                {
                    "defend": defend_id,
                    "to": uid,
                    "cid": 0,
                    "duction_money": 0,
                    "unified_relation_version": 1,
                    "useCoin": -1
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'defend-upgrade':
        data = {
            "platform": 'available',
            "type": 'defend-upgrade',
            "money": money,
            "params":
                {
                    "id": "{}".format(defend_id),  # xs_relation_defend  id
                    "useCoin": -1
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'defend-break':
        data = {
            "platform": 'available',
            "type": 'defend-break',
            "money": money,
            "params":
                {
                    "id": "{}".format(defend_id),  # xs_relation_defend  id
                    "useCoin": -1
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'chat-coupon':
        data = {
            "platform": 'available',
            "type": 'chat-gift',
            "money": money,
            "params":
                {
                    "notify_group_id": 0,
                    "to": '{}'.format(uid),
                    "giftId": giftId,
                    "giftNum": num,
                    "cid": cid,
                    "ctype": "coupon",
                    "duction_money": duction_money,
                    "version": 2,
                    "num": num,
                    "gift_type": "normal",
                    "star": 0,
                    "show_pac_man_guide": 1,
                    "all_mic": 0,
                    "gift_tab": "gift"
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'room-coupon':
        p = []
        uid = ','.join(uids)
        num_more = len(uids)
        for i in range(len(uids)):
            p.append(str(i + 1))
        position = ','.join(p)
        data = {
            "platform": "available",
            "type": "package",
            "money": price * num_more * num,  # 单价*人数*单次送礼个数
            "params": {
                "rid": rid,
                "uids": '{}'.format(uid),
                "positions": "{}".format(position),
                "position": -1,
                "giftId": giftId,
                "giftNum": num,
                "price": price,
                "cid": cid,
                "ctype": "coupon",
                "duction_money": duction_money,
                "version": 2,
                "num": num * num_more,  # 人数*单次送礼个数
                "gift_type": "normal",
                "star": 0,
                "show_pac_man_guide": 1,
                "refer": "flow_recommend:room",
                "all_mic": 0,
                "gift_tab": "gift",
                "gift_refer": "",
            }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'zx_box':  # 甄选礼盒
        p = []
        uid = ','.join(uids)
        num_more = len(uids)
        for i in range(len(uids)):
            p.append(str(i + 1))
        position = ','.join(p)
        data = {
            "platform": "available",
            "type": "package",
            "money": price * num_more * num,  # 单价*人数*单次送礼个数
            "params": {
                "rid": rid,
                "uids": '{}'.format(uid),
                "positions": "{}".format(position),
                "position": -1,
                "giftId": giftId,
                "giftNum": num,
                "price": price,
                "cid": 0,
                "ctype": "",
                "duction_money": 0,
                "version": 2,
                "num": num * num_more,  # 人数*单次送礼个数
                "gift_type": "normal",
                "star": 0,
                "show_pac_man_guide": 1,
                "refer": "search:room",
                "all_mic": 0,
                "gift_refer": "",
                "useCoin": -1
            }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'graffiti':
        p = []
        uid = ','.join(uids)
        num_more = len(uids)
        for i in range(len(uids)):
            p.append(str(i + 1))
        position = ','.join(p)
        graffiti_feature=[]
        for i in range(num):
            x = 40
            y = 40
            x_y = [x + i, y + i]
            graffiti_feature.append(x_y)
        data = {
            "platform": "available",
            "type": "package",
            "money": price * num * num_more,
            "params":
                {
                    "rid": rid,
                    "uids": '{}'.format(uid),
                    "positions": "{}".format(position),
                    "position": -1,
                    "giftId": giftId,
                    "giftNum": num,
                    "price": price,
                    "version": 2,
                    "gift_type": "{}".format(giftType),
                    "all_mic": 0,
                    "graffiti_feature": graffiti_feature
                },
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'choose_song':  # 点歌
        data = {
            "platform": "available",
            "type": "slp-consume",
            "money": money,
            "params":
                {
                    "consume_type": "music_order",
                    "rid": rid,
                    "order_songs": order_songs,
                    "version": 1
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'naming_song':  # 冠歌
        data = {
            "platform": "available",
            "type": "slp-consume",
            "money": naming_song['money'],
            "params": {
                "consume_type": "naming_song",
                "rid": rid,
                "song_id": naming_song['song_id'],
                "singer": uid,
                "multiple_id": naming_song['multiple_id'],
                "gift_id": naming_song['gift_id'],

                "gift_cnt": naming_song['gift_cnt'],
                "ucid": naming_song['ucid'],
                "money_pay": naming_song['money_pay'],
                "ucnum": naming_song['ucnum'],
            }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'starship-im':
        p = []
        uid = ','.join(uids)
        num_more = len(uids)
        for i in range(len(uids)):
            p.append(str(i + 1))
        position = ','.join(p)
        data = {
            "platform": "available",
            "type": "group-chat-gift",
            "money": money * num * num_more,
            "params":
                {
                    "notify_group_id": 0,
                    "uids": '{}'.format(uid),
                    "group_id": group_id,
                    "giftId": giftId,
                    "giftNum": num,
                    "cid": 0,
                    "ctype": "",
                    "duction_money": 0,
                    "version": 2,
                    "num": num_more * num,
                    "gift_type": "normal",
                    "star": 0,
                    "show_pac_man_guide": 1,
                    "clone_id": 0,
                    "all_mic": 0,
                    "gift_tab": "gift"
                }
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    elif payType == 'talent_show':
        data = {
            "platform": "available",
            "type": "slp-consume",
            "money": talent_show['price'],
            "params":
                {
                    "consume_type": "talent_show_mic",
                    "rid": rid,
                    "position": talent_show['position'],
                    "price_id": talent_show['price_id'],
                    "broker_uid": uid
                },
        }
        print(data)
        d = urllib.parse.urlencode(data)
        data = d.replace('+', '').replace('%27', '%22')
        return data
    else:
        # 未知 payType 原来会静默返回 None，调用方拿 None 去发请求，
        # 用例最终报的是“响应不对”而不是“场景写错”，排查成本很高，这里直接抛错暴露调用方问题
        raise ValueError('encodeData 不支持的 payType: {}'.format(payType))


if __name__ == '__main__':
    uid = gsUid
    rid = gs_soundchat_rid
    num = 10
    uids = tuple([str(i) for i in [gs_A_uid, normal_uid]])
    data = encodeData(
        rid=rid,
        payType='package',
        uid=uid,
        giftId=giftId['69']['gid']
    )
    print(data)
