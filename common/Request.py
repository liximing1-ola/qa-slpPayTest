# coding=utf-8
"""
封装 request
"""
import os
import threading
import time

import requests
import urllib3

# from caseStarify.need_data import starify_payUid
# from caseSlp.config import slp_payUid
# from caseStarify.tools import create_sign
from common import Session
# from common.Basic_starify import header_starify
# from common.Basic_starify import query_starify
from common.Session import Session

# 单次请求超时时间（秒），避免网络异常时用例无限挂起
REQUEST_TIMEOUT = 30
# 同一账号两次请求的最小间隔（秒）：服务端对连续操作有频控，间隔不足会返回"请勿频繁操作"；
# 需要提速时可用环境变量覆盖，例如 REQUEST_INTERVAL=0.5
REQUEST_INTERVAL = float(os.environ.get('REQUEST_INTERVAL', 2))
# 命中频控后的最大重试次数：设为 0 表示不重试，直接把频控响应交给用例判断
FREQUENT_RETRY = int(os.environ.get('FREQUENT_RETRY', 2))
FREQUENT_MSG = '请勿频繁操作'

# 每个账号上一次请求的计划发起时间，用于补足最小间隔
_last_request_at = {}
_interval_lock = threading.Lock()


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
    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; HD1900 Build/RKQ1.201022.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36 / Xs android V1.1.0.0 / Js V1.0.0.0 / Login V1658980709",
        "Content-Type": "application/x-www-form-urlencoded",
        'Connection': 'close',
        "user-token": Session.checkUserToken(operate='read', app_name=tokenName, uid=pay_uid)
    }
    if not url.startswith('https://'):
        url = '%s%s' % ('https://', url)

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
    return {
        'code': response.status_code,
        'body': body,
        # elapsed.microseconds 只是秒以下的部分，total_seconds() 才是完整耗时
        'time_consuming': response.elapsed.total_seconds() * 1000,
        'time_total': response.elapsed.total_seconds(),
    }


# def post_request_session_starify(url, data, tokenName='starify', uid=starify_payUid):
#     """
#     post请求
#     :param url:
#     :param data:
#     :param tokenName:
#     :return:
#     """
#     urllib3.disable_warnings()
#     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#     # 处理header
#     header = header_starify.copy()
#     header['user-token'] = Session.checkUserToken_starify(operate='read', app_name=tokenName, uid=uid)
#
#     # 处理query
#     deal_query = query_starify.copy()
#     deal_query['_timestamp'] = str(int(time()))
#     sign = create_sign(deal_query)
#     deal_query['_sign'] = sign
#     deal_query['_blid'] = starify_payUid
#     url = url + "?" + unquote(urlencode(deal_query))
#
#     try:
#         if data is None:
#             response = requests.post(url=url, headers=header, verify=False)
#         else:
#             response = requests.post(url=url, data=data, headers=header, verify=False)
#     except requests.RequestException as e:
#         print(e)
#         return ()
#     except Exception as e:
#         print(e)
#         return ()
#     # print(response.json())
#     time_consuming = response.elapsed.microseconds / 1000
#     time_total = response.elapsed.total_seconds()
#     response_dicts = dict()
#     response_dicts['code'] = response.status_code
#     try:
#         response_dicts['body'] = response.json()
#     except Exception as e:
#         print(e)
#         response_dicts['body'] = ''
#     response_dicts['time_consuming'] = time_consuming
#     response_dicts['time_total'] = time_total
#     return response_dicts
# def post_request_session_slp(url, data, tokenName='slp', uid=slp_payUid):
#     """
#     post请求
#     :param url:
#     :param data:
#     :param tokenName:
#     :return:
#     """
#     urllib3.disable_warnings()
#     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#     # 处理header
#     header = header_slp.copy()
#     header['user-token'] = Session.checkUserToken_slp(operate='read', app_name=tokenName, uid=uid)
#
#     # 处理query
#     deal_query = query_slp.copy()
#     deal_query['_timestamp'] = str(int(time()))
#     sign = create_sign(deal_query)
#     deal_query['_sign'] = sign
#     deal_query['_blid'] = slp_payUid
#     url = url + "?" + unquote(urlencode(deal_query))
#
#     try:
#         if data is None:
#             response = requests.post(url=url, headers=header, verify=False)
#         else:
#             response = requests.post(url=url, data=data, headers=header, verify=False)
#     except requests.RequestException as e:
#         print(e)
#         return ()
#     except Exception as e:
#         print(e)
#         return ()
#     # print(response.json())
#     time_consuming = response.elapsed.microseconds / 1000
#     time_total = response.elapsed.total_seconds()
#     response_dicts = dict()
#     response_dicts['code'] = response.status_code
#     try:
#         response_dicts['body'] = response.json()
#     except Exception as e:
#         print(e)
#         response_dicts['body'] = ''
#     response_dicts['time_consuming'] = time_consuming
#     response_dicts['time_total'] = time_total
#     return response_dicts
if __name__ == '__main__':
    header = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 11; CPH1969 Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.138 Mobile Safari/537.36 / Xs android V5.0.31.0 / Js V1.0.0.0 / Login V1691131402',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', 'Connection': 'close',
        'user-token': 'a4d3klcO2pbZg0__2BvGlU7jGTRCAPyfVdQ7nySzDPs0PZEi7rbX8VC__2BZ0QoEz2auiTnhYEWu1kYG7s7F7G__2BinZ7ZIT9QxfQ2MFc0LrVe12GOBdiICefxz82aloSw'}
    url = 'https://192.168.1.23/pay/create?package=com.yhl.sleepless.android'
    data = 'platform=available&type=chat-gift&money=1000&params=%7B%22notify_group_id%22%3A0%2C%22to%22%3A%22105002312%22%2C%22giftId%22%3A5%2C%22giftNum%22%3A10%2C%22cid%22%3A0%2C%22ctype%22%3A%22%22%2C%22duction_money%22%3A0%2C%22version%22%3A2%2C%22num%22%3A10%2C%22gift_type%22%3A%22normal%22%2C%22star%22%3A0%2C%22show_pac_man_guide%22%3A1%2C%22all_mic%22%3A0%2C%22useCoin%22%3A-1%7D'
    print(requests.post(url=url, data=data, headers=header, verify=False).json())
