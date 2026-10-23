# coding=utf-8
"""
封装 request
"""
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


def post_request_session(url, data, tokenName='dev', pay_uid=None):
    """
    post请求
    :param url:
    :param data:
    :param tokenName:
    :param pay_uid: 指定用户uid读取对应token
    :return:
    """
    time.sleep(2)
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
    try:
        if data is None:
            response = requests.post(url=url, headers=header, verify=False)
        else:
            response = requests.post(url=url, data=data, headers=header, verify=False)
    except requests.RequestException as e:
        print(e)
        return ()
    except Exception as e:
        print(e)
        return ()
    print("#"*100)
    print(response.status_code)
    print(response.json())
    print("#"*100)
    time_consuming = response.elapsed.microseconds/1000
    time_total = response.elapsed.total_seconds()
    response_dicts = dict()
    response_dicts['code'] = response.status_code
    try:
        response_dicts['body'] = response.json()
    except Exception as e:
        print(e)
        response_dicts['body'] = ''
    response_dicts['time_consuming'] = time_consuming
    response_dicts['time_total'] = time_total
    return response_dicts


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
