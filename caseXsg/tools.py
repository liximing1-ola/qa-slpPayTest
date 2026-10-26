import hashlib
import math
import time

import requests


def merge_dicts(*args):
    """
	合并dict
	:param dict_old:老的字典
	:param dict_new:新的字典
	:return:
	"""
    _all_dict = {}
    for _dict in args:
        if not isinstance(_dict, dict):
            _dict = {}
        _all_dict = {**_all_dict, **_dict}
    return _all_dict


def create_sign(query, salt="!rilegoule#"):
    """
	生成sign
	:param query: 路径参数,以dict形式传�?	:param salt: �?可能不一�?	:return:
	"""
    keys = ['_abi', '_index', '_ipv', '_model', '_platform', '_timestamp', 'format', 'package']
    hashArgs = []
    for key in sorted(keys):
        value = query[key]
        hashArgs.append(f"{key}={value}")
    content = '&'.join(hashArgs) + salt
    _sign = hashlib.md5(bytes(content, encoding='utf-8')).hexdigest()
    return _sign


def hash_key():
    """生成连击key"""
    return hashlib.md5(str(int(time.time())).encode()).hexdigest()


def deal_num(num):
    """处理精度问题,保留2位小数后,向上取整"""
    return math.ceil(round(num, 2))


def get_test_token(*uids):
    import requests

    if not uids:
        raise ValueError("至少传入一个uid")

    token_map = {}
    for uid in uids:
        url = f"https://192.168.1.23/test/userToken?uid={uid}"
        payload = {}
        headers = {}
        try:
            res = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=3)
            print(res.json())
            if res.status_code != 200 or not res.json().get('data', None):
                raise Exception("使用测试接口,获取token失败")
            token_map[uid] = res.json()['data']
        except Exception as e:
            print("使用测试接口,获取token失败")
            raise e
    return token_map


# 校验 外显的vip/人气标签(影响分成)
def check_vip_pop(uid, expect_show='vip'):
    """
    校验用户外显标签是否符合预期
    :param uid: 用户ID
    :param expect_show: 预期标签 'vip' �?'pop'
    :return: 是否符合预期
    """
    from common.conSlpXsgMysql import conMysql as mysql

    user_broker_flag = mysql.checkUserBroker(uid)  # 在工�?    user_agreement_flag = mysql.checkUserAgreement(uid)  # 签署大神协议
    user_white_flag = mysql.checkUserWhite(uid, 198)  # 在主播身份白名单198�?
    # 实际标签判断：同时满足三个条件为pop，否则为vip
    actual_result = "pop" if (user_broker_flag and user_agreement_flag and user_white_flag) else "vip"

    return actual_result == expect_show


# ==================== 公共数据准备方法 ====================

def prepare_test_data(pay_uid, *target_uids, money=None, clear_commodity=True, god_status=None):
    """
    通用的测试数据准备方�?    :param pay_uid: 打赏者UID
    :param target_uids: 被打赏者UID列表
    :param money: 打赏者初始金额（None表示不设置）
    :param clear_commodity: 是否清理背包
    :param god_status: 设置大神状�?{uid: status, ...}
    """
    from common.conSlpXsgMysql import conMysql as mysql

    if money is not None:
        mysql.updateMoneySql(pay_uid, money)
    for uid in target_uids:
        mysql.updateUserMoneyClearSql(uid)
    if clear_commodity:
        mysql.deleteUserAccountSql('user_commodity', pay_uid)
    if god_status:
        for uid, status in god_status.items():
            mysql.updateUserGodSql(uid, status)


def prepare_vip_pop_data(uid, pay_uid=None):
    """
    准备 VIP/人气�?相关的数据清�?    :param uid: 被打赏者UID
    :param pay_uid: 打赏者UID（可选）
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.deleteUserAccountSql('user_popularity', uid)
    mysql.deleteUserAccountSql('user_title_new', uid)
    mysql.deleteUserAccountSql('pay_room_money', uid)
    if pay_uid:
        mysql.deleteUserAccountSql('user_popularity', pay_uid)
        mysql.deleteUserAccountSql('user_title_new', pay_uid)
        mysql.deleteUserAccountSql('pay_room_money', pay_uid)


def prepare_room_data(rid, uid=None, position=0):
    """
    准备房间相关数据
    :param rid: 房间ID
    :param uid: 上麦用户UID（None表示下麦�?    :param position: 麦位位置
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.deleteXsMicPermission(rid)
    if uid:
        mysql.updateXsChatroomConfig(rid, uid=uid, position=position)
    else:
        mysql.updateXsChatroomConfig(rid, 0, position=position)


def prepare_acceleration_card(uid, speed, pay_uid=None, pay_speed=None):
    """
    准备加速卡数据
    :param uid: 被打赏者UID
    :param speed: 被打赏者加速倍率
    :param pay_uid: 打赏者UID（可选）
    :param pay_speed: 打赏者加速倍率（可选）
    :return: 包含加速信息的字典
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.deleteXsUserAccelerationInfo(uid)
    mysql.insertXsUserAccelerationInfo(uid, speed)

    result = {'uid_speed': speed}

    if pay_uid and pay_speed:
        mysql.deleteXsUserAccelerationInfo(pay_uid)
        mysql.insertXsUserAccelerationInfo(pay_uid, pay_speed)
        result['pay_uid'] = pay_uid
        result['pay_speed'] = pay_speed

    return result


def clear_acceleration_card(uid, pay_uid=None):
    """
    清理加速卡数据
    :param uid: 被打赏者UID
    :param pay_uid: 打赏者UID（可选）
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.deleteXsUserAccelerationInfo(uid)
    if pay_uid:
        mysql.deleteXsUserAccelerationInfo(pay_uid)


def insert_coupon(uid, cid, num=1):
    """
    插入优惠券并返回coupon id
    :param uid: 用户UID
    :param cid: 优惠券配置ID
    :param num: 数量
    :return: 用户优惠券ID
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.insertXsUserCommodity(uid, cid, num)
    mysql.insertXsUserCouponUse(uid, cid)
    return int(mysql.selectUserInfoSql('id_commodity', uid, cid=cid))


def insert_package_gift(uid, cid, num=1):
    """
    插入背包礼物并返回package cid
    :param uid: 用户UID
    :param cid: 礼物配置ID
    :param num: 数量
    :return: 背包礼物ID
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.insertXsUserCommodity(uid, cid, num)
    return int(mysql.selectUserInfoSql('id_commodity', uid, cid=cid))


if __name__ == '__main__':
    pass
