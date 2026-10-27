# coding=utf-8
"""
封装 request
"""
import os
import threading
import time

import requests
import urllib3

from common.Session import Session

# 单次请求超时时间（秒），避免网络异常时用例无限挂起
REQUEST_TIMEOUT = 30
# 同一账号两次请求的最小间隔（秒），避免网络异常时用例无限挂起；需要提速时可用环境变量覆盖，
# 例如 REQUEST_INTERVAL=0.5。注意用 or 而非默认参数：export REQUEST_INTERVAL= 这种空值会让 float('') 在 import 阶段抛错
REQUEST_INTERVAL = float(os.environ.get('REQUEST_INTERVAL') or 2)
# 命中频控后的最大重试次数：设为 0 表示不重试，直接把频控响应交给用例判断
FREQUENT_RETRY = int(os.environ.get('FREQUENT_RETRY') or 2)
FREQUENT_MSG = '请勿频繁操作'

# 每个账号上一次请求的计划发起时间，用于补足最小间隔
_last_request_at = {}
_interval_lock = threading.Lock()

# ===== 用例重试时的写请求复用 =====
# Retry 失败后会把整个用例体重跑一遍，里面如果是下单/送礼的写请求，就会真的再下一单：
# 测试账号多出重复订单、金额断言口径被污染，形成"失败→重跑→再下一单"的放大链。
# 这里对写请求（pay/create）做"同一用例内同参数复用"：首次执行把响应记下来，
# 重试时直接返回上一轮的响应，只重新做读库断言——结算延迟这类抖动依然能救回来。
#
# 只缓存**下单成功**的响应：业务失败的响应（success != 1）一旦进缓存，重试就再也发不出
# 新请求，“重试”退化成“把同一份失败响应重读三遍”，必然红。点唱房偶发的「房间类型错误」
# 就是这么连撞四轮同一个错的——服务端只抖了一下，是回放把它固化成了定局。
_RETRY_CACHE_MARK = 'pay/create'
_replay_state = threading.local()


def _cache():
    """回放缓存跟随线程：重试标记与缓存必须同源，否则并发时会互相踩"""
    cache = getattr(_replay_state, 'cache', None)
    if cache is None:
        cache = {}
        _replay_state.cache = cache
    return cache


def begin_case():
    """每个用例（含它的全部重试轮次）开始时调用：清掉上一个用例的缓存并退出重试态"""
    _cache().clear()
    _replay_state.replay = False
    _replay_state.wrote = False
    _replay_state.read_index = {}


# 回放轮还要还原"下单前的读值"：用例常写成 old = 查 → 下单 → 断言 new == old + 增量，
# 回放轮不再真正下单，库里的基线已经是首轮结算后的值，若不还原 old，断言必然失败。
# 这里按"同一查询在本轮的调用序号"对齐，只回放发生在首轮下单之前的读值；
# 下单之后的读值必须重新查询——那正是重试要观察的目标。
READ_MISS = object()


def begin_replay():
    """用例重试开始：后续同参数写请求直接复用上一轮的响应

    只有上一轮真的发出过写请求才进入回放：若首轮死在下单之前的前置断言上，
    缓存里根本没有下单记录，这时如果照样进入回放，就会"跳过数据准备 + 真实下单"，
    拿着上一条用例残留的脏数据跑出假失败，还白下一单。这种情况下保持普通重跑即可。
    """
    # 读序号按轮次归零：本轮的第 n 次查询才能对上上一轮的第 n 次查询
    _replay_state.read_index = {}
    if not getattr(_replay_state, 'wrote', False):
        return
    _replay_state.replay = True


def is_replaying():
    """当前是否处在重试轮次（非幂等的数据准备可据此跳过）"""
    return getattr(_replay_state, 'replay', False)


def next_read_index(key):
    """同一个查询在本轮内的调用序号"""
    index = getattr(_replay_state, 'read_index', None)
    if index is None:
        index = {}
        _replay_state.read_index = index
    seq = index.get(key, 0)
    index[key] = seq + 1
    return seq


def remember_read(key, seq, value):
    """记下本轮读值，并标记它是否发生在下单之前"""
    _cache()[('read', key, seq)] = (value, not getattr(_replay_state, 'wrote', False))


def replay_read(key, seq):
    """复用此前在下单前记下的读值；下单后记下的读值返回 READ_MISS，由调用方真实查询"""
    item = _cache().get(('read', key, seq))
    if item is None or not item[1]:
        return READ_MISS
    return item[0]


def cache_get(key):
    return _cache().get(key)


def cache_put(key, value):
    _cache()[key] = value


def _wait_for_interval(token_name):
    """
    按账号保证两次请求之间的最小间隔。

    原实现是每个请求前固定 sleep(2)，即使距上次请求已经过去很久也要空等；
    这里改为只补足差额：连续操作时不会触发频控，请求间隔本来就够时也不浪费时间。
    """
    with _interval_lock:
        now = time.time()
        last = _last_request_at.get(token_name)
        wait = REQUEST_INTERVAL - (now - last) if last is not None else 0
        if wait < 0:
            wait = 0
        # 先占位再等待，多个线程排队时也能保持间隔
        _last_request_at[token_name] = now + wait
    if wait > 0:
        time.sleep(wait)


def _is_frequent_response(body):
    """判断是否命中服务端频控"""
    return isinstance(body, dict) and FREQUENT_MSG in str(body.get('msg', ''))


def _is_business_success(body):
    """下单是否真的成功（响应里的 success 字段为 1/True）

    网关返回 html 等非 json 响应时 body 是字符串，一律按失败处理：这种响应没有结算，
    缓存它只会让重试永远拿到同一份垃圾。
    """
    if not isinstance(body, dict):
        return False
    return body.get('success') in (1, True, '1')


def post_request_session(url, data, tokenName='dev', pay_uid=None):
    """
    post请求
    :param url:
    :param data:
    :param tokenName:
    :param pay_uid: 指定用户uid读取对应token
    :return:
    """
    urllib3.disable_warnings()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if not url.startswith('https://'):
        url = '%s%s' % ('https://', url)

    # 写请求才做重试复用：读接口重复请求行为保持不变。
    # 命中回放要放在读 token 之前，否则 token 文件异常时回放会跟着一起失败
    cache_key = None
    if _RETRY_CACHE_MARK in url:
        cache_key = (url, str(data), tokenName, str(pay_uid))
        cached = cache_get(cache_key)
        if is_replaying() and cached is not None:
            print('[重试复用] 不重复下单: {}'.format(url))
            return cached

    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; HD1900 Build/RKQ1.201022.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36 / Xs android V1.1.0.0 / Js V1.0.0.0 / Login V1658980709",
        "Content-Type": "application/x-www-form-urlencoded",
        'Connection': 'close',
        "user-token": Session.checkUserToken(operate='read', app_name=tokenName, uid=pay_uid)
    }

    response = None
    body = None
    for attempt in range(FREQUENT_RETRY + 1):
        _wait_for_interval(tokenName)
        try:
            if data is None:
                response = requests.post(url=url, headers=header, verify=False, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.post(url=url, data=data, headers=header, verify=False, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            # 不能返回空元组：调用方会直接 res['code'] 触发 TypeError，把真实失败原因（超时/证书错误）掩盖掉
            raise AssertionError('接口请求失败: {}, 原因: {}'.format(url, error)) from error

        try:
            body = response.json()
        except ValueError:
            # 网关返回 html 等非 json 响应时保留原始文本，便于定位问题
            body = response.text

        # 频控属于环境噪声而不是被测逻辑，退避后重试；超过次数则把原响应交给用例断言
        if attempt < FREQUENT_RETRY and _is_frequent_response(body):
            print('[频控] 命中"{}", {} 秒后重试（第 {}/{} 次）'.format(
                FREQUENT_MSG, REQUEST_INTERVAL, attempt + 1, FREQUENT_RETRY))
            continue
        break

    print("#"*100)
    print(response.status_code)
    print(body)
    print("#"*100)
    result = {
        'code': response.status_code,
        'body': body,
        # elapsed.microseconds 只是秒以下的部分，total_seconds() 才是完整耗时
        'time_consuming': response.elapsed.total_seconds() * 1000,
        'time_total': response.elapsed.total_seconds(),
    }
    if cache_key is not None:
        # 发过下单请求就算"已下单"：数据准备（改金额、插背包礼物）不能在重试轮重做，
        # 否则会把首轮已经生效的造数覆盖掉，断言口径全乱
        _replay_state.wrote = True
        if _is_business_success(body):
            cache_put(cache_key, result)
        else:
            # 业务失败不入缓存：重试轮要重新发一次请求，而不是回放这份失败响应
            print('[重试] 下单未成功，本轮不缓存、重试时重新请求: {}'.format(body))
    return result


if __name__ == '__main__':
    header = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 11; CPH1969 Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.138 Mobile Safari/537.36 / Xs android V5.0.31.0 / Js V1.0.0.0 / Login V1691131402',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', 'Connection': 'close',
        'user-token': 'a4d3klcO2pbZg0__2BvGlU7jGTRCAPyfVdQ7nySzDPs0PZEi7rbX8VC__2BZ0QoEz2auiTnhYEWu1kYG7s7F7G__2BinZ7ZIT9QxfQ2MFc0LrVe12GOBdiICefxz82aloSw'}
    url = 'https://192.168.1.23/pay/create?package=com.yhl.sleepless.android'
    data = 'platform=available&type=chat-gift&money=1000&params=%7B%22notify_group_id%22%3A0%2C%22to%22%3A%22105002312%22%2C%22giftId%22%3A5%2C%22giftNum%22%3A10%2C%22cid%22%3A0%2C%22ctype%22%3A%22%22%2C%22duction_money%22%3A0%2C%22version%22%3A2%2C%22num%22%3A10%2C%22gift_type%22%3A%22normal%22%2C%22star%22%3A0%2C%22show_pac_man_guide%22%3A1%2C%22all_mic%22%3A0%2C%22useCoin%22%3A-1%7D'
    print(requests.post(url=url, data=data, headers=header, verify=False).json())
