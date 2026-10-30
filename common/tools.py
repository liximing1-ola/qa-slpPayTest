# -*- coding: utf-8 -*-
"""
用例公共工具

原来 caseSlp/tools.py 与 caseXsg/tools.py 各存一份，内容 99% 相同
（唯一差异是 slp 多了 get_last_weekday_timestamp，xsg 多了无用的 import requests），
改一处漏一处的风险很高，现合并到这里统一维护。

这些方法都不依赖 caseSlp/caseXsg 的配置，入参全部由调用方显式传入。
caseSlp/tools.py 与 caseXsg/tools.py 保留为转发模块，兼容原有引用写法。
"""
import hashlib
import math
import time
from datetime import datetime, timedelta

import requests

from common import Request
from common.Config import config
from common.conRedis import conRedis


def merge_dicts(*args):
    """
    合并 dict，后面的覆盖前面的
    :param args: 任意多个 dict，非 dict 入参当作空 dict 忽略
    :return: 合并后的新 dict
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
	:param query: 路径参数,以dict形式传递
	:param salt: 盐,可能不一样
	:return:
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
    """通过测试接口批量获取 token"""
    if not uids:
        raise ValueError("至少传入一个uid")

    token_map = {}
    # 域名跟 common.Config 走，换测试环境不用改代码（这里原本写死了一个固定地址）
    url_template = config.appInfo['slp'] + 'test/userToken?uid={}'
    for uid in uids:
        url = url_template.format(uid)
        payload = {}
        headers = {}
        try:
            res = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=3)
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
    :param expect_show: 预期标签 'vip' 或 'pop'
    :return: 是否符合预期
    """
    from common.conSlpXsgMysql import conMysql as mysql

    user_broker_flag = mysql.checkUserBroker(uid)  # 在工会
    user_agreement_flag = mysql.checkUserAgreement(uid)  # 签署大神协议
    user_white_flag = mysql.checkUserWhite(uid, 198)  # 在主播身份白名单198中

    # 实际标签判断：同时满足三个条件为pop，否则为vip
    actual_result = "pop" if (user_broker_flag and user_agreement_flag and user_white_flag) else "vip"

    return actual_result == expect_show


# ==================== 公共数据准备方法 ====================

def prepare_test_data(pay_uid, *target_uids, money=None, clear_commodity=True, god_status=None):
    """
    通用的测试数据准备方法
    :param pay_uid: 打赏者UID
    :param target_uids: 被打赏者UID列表
    :param money: 打赏者初始金额（None表示不设置）
    :param clear_commodity: 是否清理背包
    :param god_status: 设置大神状态 {uid: status, ...}
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


def reset_room_acs(uid, rid):
    """
    把用户在厅内的收入统计重置成「只剩当前厅一行」

    xsst_roomacs_sum 是累计值：上一轮用例打的赏会叠进来，分成断言就会莫名
    多出上一轮的金额。用例里原本各写两行（先删干净、再插当前厅），17 处重复，
    语义只存在于读代码的人脑子里；收成一处之后，这里要补字段也只改一遍。
    :param uid: 被测用户（一般是主播）
    :param rid: 要保留的那一行对应的厅
    """
    from common.conSlpXsgMysql import conMysql as mysql

    mysql.deleteXsstRoomacsSum(uid)
    mysql.insertXsstRoomacsSum(uid, rid)


def read_vip_pop_direct(uid):
    """直接读表拿 (vip 经验值, 人气值)，不参与重试轮次的读值回放

    复位的观察循环要在一条用例里读好几轮，走 selectUserInfoSql 会占掉回放用的读序号
    （它按「同一查询在本轮的第几次」对齐）。重试轮一旦少读一轮，后面的 read_vip_pop
    就会拿到错位的旧值——这类「框架自己的观察」不该进业务读值序列。
    :param uid: 用户UID
    :return: (pay_room_money, popularity)，缺行按 0 处理
    """
    from common.conSlpXsgMysql import conMysql as mysql

    vip_rows = mysql.selectRawDict('select pay_room_money from xs_user_profile where uid={}'.format(int(uid)))
    pop_rows = mysql.selectRawDict('select popularity from xs_user_popularity where uid={}'.format(int(uid)))
    vip = vip_rows[0].get('pay_room_money') if vip_rows else None
    pop = pop_rows[0].get('popularity') if pop_rows else None
    return 0 if vip is None else int(vip), 0 if pop is None else int(pop)


def prepare_vip_pop_data(uid, pay_uid=None, quiet=3, timeout=None, interval=None):
    """把双方的 VIP 经验值/人气值清零，并等到清零之后不再被写回

    清零只是几条 update，写完不等于「别人不会再写」：vip/人气 是异步结算写的，上一条用例
    （带券多人打赏那类）只断言余额和分成、不等这两项，它那笔 6000 就可能在本条用例
    「清零 + 记基线」之后才落库——100 的增量会读成 6100（6100 = 6000 + 100，6000 是
    600 钻礼物打 10 个那批，2026-10-30 全量实测）。重试也救不回来：回放轮丢弃写库
    （_ReplayCursor 只放行查询），那 6000 清不掉，只能照样红一次。

    所以清零之后多观察几轮：连读 quiet 次都是 0 才算安静；中途读回非 0 说明有笔结算
    迟到了，打印出来再清一遍。超时没等到静默不在这里抛：有些用例只比增量（基线取当前
    值即可），要求基线必须为 0 的那种（test_exp.test_001）会在紧跟着的基线断言上亮红，
    并报出实际值——报错落在断言上，别让复位函数替它判。

    :param uid: 被打赏者UID
    :param pay_uid: 打赏者UID（可选）
    :param quiet: 连续几次读到全 0 才算安静
    :param timeout: 最多观察多少秒，默认 WAIT_TIMEOUT
    :param interval: 两次观测的间隔，默认 WAIT_INTERVAL
    :return: 最后一次读到的 {uid: (vip, 人气)}
    """
    from common.Assert import WAIT_INTERVAL, WAIT_TIMEOUT
    from common.conSlpXsgMysql import conMysql as mysql
    from common.Request import is_replaying

    uids = [uid] + ([pay_uid] if pay_uid else [])
    timeout = WAIT_TIMEOUT if timeout is None else timeout
    interval = WAIT_INTERVAL if interval is None else interval

    def _clear():
        for target in uids:
            mysql.deleteUserAccountSql('user_popularity', target)
            mysql.deleteUserAccountSql('user_title_new', target)
            mysql.deleteUserAccountSql('pay_room_money', target)

    if is_replaying():
        # 回放轮写库被丢弃，清了不生效、也等不到静默，只能白等一个 timeout 再打一串误导的日志
        print('[vip] 回放轮跳过复位：本轮写库被丢弃，复位不生效')
        return None

    _clear()
    deadline = time.time() + timeout
    still = 0
    rounds = 0
    while True:
        time.sleep(interval)
        rounds += 1
        snapshot = dict((target, read_vip_pop_direct(target)) for target in uids)
        dirty = [(target, value) for target, value in snapshot.items() if value != (0, 0)]
        if not dirty:
            still += 1
            if still >= quiet:
                return snapshot
        else:
            still = 0
            print('[vip] 复位后又被写回（第 {} 次观测）：{}，有结算迟到了'.format(
                rounds, '，'.join('uid={} vip={} 人气={}'.format(target, value[0], value[1])
                                 for target, value in sorted(dirty))))
            if time.time() >= deadline:
                print('[vip] 已观察 {:.1f} 秒仍在被写，不再等，当前值交后续断言判定'.format(timeout))
                return snapshot
            _clear()
            continue
        if time.time() >= deadline:
            print('[vip] 已观察 {:.1f} 秒仍未连读 {} 次为 0，当前值交后续断言判定'.format(timeout, quiet))
            return snapshot


def read_vip_pop(pay_uid, uid):
    """读取双方的 vip 经验值与人气值，作为打赏前的基线

    分成/人气断言都是「打赏后的值 == 打赏前的值 + 增量」，用例开头都要先把这四个值记下来。
    读取顺序固定：付款人 vip、付款人 人气、收款人 vip、收款人 人气，
    调用方按同样顺序解包即可，与原先逐行赋值的变量一一对应。

    :return: (pay_uid 的 pay_room_money, pay_uid 的 popularity,
              uid 的 pay_room_money, uid 的 popularity)
    """
    from common.conSlpXsgMysql import conMysql as mysql

    return (mysql.selectUserInfoSql('pay_room_money', pay_uid),
            mysql.selectUserInfoSql('popularity', pay_uid),
            mysql.selectUserInfoSql('pay_room_money', uid),
            mysql.selectUserInfoSql('popularity', uid))


def read_vip_pop_snapshot(*uids):
    """把一批账号的 (vip 经验值, 人气值) 读成 {uid: (vip, 人气)}

    打赏前记一份，配合 wait_vip_pop_settled 看「这笔打赏的 vip/人气 写到哪了」。
    """
    return dict((target, read_vip_pop_direct(target)) for target in uids)


def wait_vip_pop_settled(baseline, quiet=5, timeout=None, first_timeout=None, interval=None):
    """等一条用例引发的 vip/人气 结算落定，再让下一条用例开始

    带券多人打赏这类用例只断言余额与分成，vip/人气 是异步写的：不等它落库就结束，
    这笔尾数会落在下一条用例「清零 + 记基线」之后（实测 6100 = 6000 + 100）。
    重试救不回来——回放轮丢弃写库，那 6000 清不掉。

    这里不改任何预期值，只把「自己这笔写完了」等出来：先等读数离开基线（证明结算
    真的在写），再等连读 quiet 次不再变。落定时把前后值打一行，将来要把这两项从
    「只等」补成「断言」时，可以直接照这行实测值写。

    :param baseline: 打赏前读到的 {uid: (vip, 人气)}，见 read_vip_pop_snapshot
    :param quiet: 连续几次读数不变才算落定
    :param timeout: 从第一次变化起最多再等多少秒，默认 WAIT_TIMEOUT
    :param first_timeout: 最多等多久等到第一次变化，默认 WAIT_TIMEOUT
    :param interval: 观测间隔，默认 WAIT_INTERVAL
    :return: 最后一次读到的 {uid: (vip, 人气)}
    """
    from common.Assert import WAIT_INTERVAL, WAIT_TIMEOUT
    from common.Request import is_replaying

    if is_replaying():
        # 回放轮没有真正下单，不会产生新的 vip/人气，白等一个 first_timeout 只会拖慢重跑
        print('[vip] 回放轮跳过等待：本轮下单是回放的，不会产生新的 vip/人气')
        return dict(baseline)
    timeout = WAIT_TIMEOUT if timeout is None else timeout
    first_timeout = WAIT_TIMEOUT if first_timeout is None else first_timeout
    interval = WAIT_INTERVAL if interval is None else interval

    def _read():
        return read_vip_pop_snapshot(*baseline)

    def _text(values):
        return '，'.join('uid={} vip {}→{} 人气 {}→{}'.format(
            target, baseline[target][0], values[target][0], baseline[target][1], values[target][1])
            for target in sorted(values))

    started = time.time()
    current = _read()
    while current == baseline and time.time() - started < first_timeout:
        time.sleep(interval)
        current = _read()
    if current == baseline:
        # 不是断言：这两项不在本条用例的验证范围里，只把「没等到变化」打出来
        print('[vip] 打赏后 {:.1f} 秒 vip/人气 没有变化：{}'.format(time.time() - started, _text(current)))
        return current

    still = 0
    deadline = time.time() + timeout
    last = current
    while True:
        time.sleep(interval)
        current = _read()
        still = still + 1 if current == last else 0
        last = current
        if still >= quiet:
            break
        if time.time() >= deadline:
            print('[vip] 打赏后 vip/人气 等了 {:.1f} 秒仍在变，剩下的交给下一条用例的清零循环'.format(
                time.time() - started))
            break
    print('[vip] 打赏后 vip/人气 已落定：{}'.format(_text(current)))
    return current


def prepare_room_data(rid, uid=None, position=0):
    """
    准备房间相关数据
    :param rid: 房间ID
    :param uid: 上麦用户UID（None表示下麦）
    :param position: 麦位位置
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


def _insert_once(label, desc, insert_func, read_func):
    """
    插入类的数据准备只真正执行一次

    插入不是幂等操作，重试轮次里再插一次会让背包/优惠券数量翻倍，因此回放轮跳过插入。
    但后续那次"取 id"的读取照常执行：它属于下单前的准备产物，会被读值回放命中、返回首轮记下的值，
    同时让读序号与首轮对齐——否则同一查询在这轮少调用一次，后面的读值会静默错位。
    :param label: 日志与报错里的中文名称
    :param desc: 参数描述，用于定位是哪一次插入
    :param insert_func: 真正执行插入
    :param read_func: 插入后查询记录 id，返回 None 视为查不到
    """
    if Request.is_replaying():
        print('[重试] 跳过重复插入{}: {}'.format(label, desc))
    else:
        insert_func()

    value = read_func()
    if value is None:
        raise AssertionError('{}插入后查不到记录: {}'.format(label, desc))
    return int(value)


def insert_coupon(uid, cid, num=1):
    """
    插入优惠券并返回coupon id
    :param uid: 用户UID
    :param cid: 优惠券配置ID
    :param num: 数量
    :return: 用户优惠券ID
    """
    from common.conSlpXsgMysql import conMysql as mysql

    def _insert():
        mysql.insertXsUserCommodity(uid, cid, num)
        mysql.insertXsUserCouponUse(uid, cid)

    return _insert_once(
        '优惠券', 'uid={}, cid={}, num={}'.format(uid, cid, num), _insert,
        lambda: mysql.selectUserInfoSql('id_commodity', uid, cid=cid))


def insert_package_gift(uid, cid, num=1):
    """
    插入背包礼物并返回package cid
    :param uid: 用户UID
    :param cid: 礼物配置ID
    :param num: 数量
    :return: 背包礼物ID
    """
    from common.conSlpXsgMysql import conMysql as mysql

    def _insert():
        mysql.insertXsUserCommodity(uid, cid, num)

    return _insert_once(
        '背包礼物', 'uid={}, cid={}, num={}'.format(uid, cid, num), _insert,
        lambda: mysql.selectUserInfoSql('id_commodity', uid, cid=cid))


def get_last_weekday_timestamp(weekday_num=1):
    """
    获取上周指定星期几的 00:00:00 时间戳

    参数:
        weekday_num: 1-7 (1=周一，2=周二，..., 7=周日)

    返回:
        int: Unix 时间戳
    """
    if weekday_num < 1 or weekday_num > 7:
        raise ValueError("weekday_num 必须是 1-7 之间的整数")

    # 这里必须用服务器本地时间：返回的时间戳会写进 xsst_roomacs_sum.date，
    # 它是与服务端"周桶"对齐的 key，服务端按同一时区口径算周一 00:00。
    # 改成固定 UTC+8 会让桶整体偏移 8 小时，服务端查不到"上周厅"，
    # 分成类用例会全部掉进"上周厅不存在"的兜底规则（实测 6 条用例集体变红）
    today = datetime.now()
    target_weekday = weekday_num - 1  # 转换为 0-6 (0=周一)
    days_ago = (today.weekday() - target_weekday + 7) % 7 + 7
    last_weekday = today - timedelta(days=days_ago)
    last_weekday = last_weekday.replace(hour=0, minute=0, second=0, microsecond=0)

    return int(last_weekday.timestamp())


class XsgTravelerMixin(object):
    """「不夜活跃」用户的公共前置：给打赏账号打上 XSG 旅行者标记

    caseXsg 下 5 个用例文件原本各抄一份 setUp/tearDown，唯一差别是「哪几条用例要标」：
    私聊只有 test_002，公会房间是 test_005~test_008。差别用类属性声明，Redis 的
    取放只留一份——否则日后改 key 格式，5 个文件里漏掉一个，就会出现“某几条用例
    单独跑绿、全量跑红”这种最难查的偏差。

    用法（类属性写在类体里，此时 config 的 star import 已经在作用域内）：
        class TestPayCreate(XsgTravelerMixin, unittest.TestCase):
            traveler_tests = ('test_002',)
            traveler_uid = payUid
    """
    # 需要打标记的方法名；空元组表示这个文件一条都不标
    traveler_tests = ()
    # 打赏账号 uid；由子类指定，common 层不反向依赖 case 的配置
    traveler_uid = None

    def traveler_key(self):
        return 'Xs.Traveler.XSG.{}'.format(self.traveler_uid)

    def setUp(self):
        # 同样用 _testMethodName 判断：重试轮次里方法名不变，行为与原来一致
        if self._testMethodName in self.traveler_tests:
            conRedis.set(self.traveler_key(), 1)

    def tearDown(self):
        # 无论本轮有没有打过标记都删：残留的标记会让下一条用例的定价走错档
        conRedis.delete(self.traveler_key())
