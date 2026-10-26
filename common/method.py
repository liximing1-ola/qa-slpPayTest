"""
用例公共小工具

历史遗留的 dictToList / dictToListSlack / getValue / checkPath / getUserTitle / reason_slp
已确认全仓库零引用（并发脚本删掉后就没人调了），这里一并移除；
checkPath 还引用着已下线项目的 'PT' 机器人，属于会直接报错的死代码。
"""
import random

import requests


# 随机获取图片
def getImage(mode=2):
    """
    通知里用的配图。第三方图片接口不可用时退化为固定图床，
    不能让「取图失败」把失败通知本身带崩。
    :param mode: 1=mxnzp 随机图, 2=shibe 随机狗图, 其他=固定图床
    """
    url = 'https://www.mxnzp.com/api/image/girl/list/random?app_id=kilmc0p2ytsnawyp&app_secret=bnNoWElSVDBYbEhsc1EvYVM2WnVnZz09'
    url_dog = 'https://shibe.online/api/shibes?count=1'
    fallback = 'http://xs-image.oss-cn-hangzhou.aliyuncs.com/static/gift_big/{}.png'.format(random.randint(1, 1000))
    try:
        if mode == 1:
            res = requests.get(url, timeout=3)
            res.raise_for_status()
            res = res.json()
            if res['code'] == 1:
                return res['data'][0]['imageUrl']
        elif mode == 2:
            res = requests.get(url_dog, timeout=3)
            res = res.json()
            return res[0]
    except Exception as error:
        print('获取通知配图失败，使用默认图床: {}'.format(error))
    return fallback


# 检查当前字段是否在Json中存在
def isExtend(data, tag):
    if type(data) != type({}):
        print('please input a json!')
    else:
        key_list = getKeys(data)
        for key in key_list:
            if key == tag:
                return True
    return False


def getKeys(data):
    keysAll_list = []

    def getKey(json_data):  # 遍历json所有key
        if type(json_data) == type({}):
            keys = json_data.keys()
            for key in keys:
                value = json_data.get(key)
                if type(value) != type({}) and type(value) != type([]):
                    keysAll_list.append(key)
                elif type(value) == type({}):
                    keysAll_list.append(key)
                    getKey(value)
                elif type(value) == type([]):
                    keysAll_list.append(key)
                    for para in value:
                        if type(para) == type({}) or type(para) == type([]):
                            getKey(para)
                        else:
                            keysAll_list.append(para)

    getKey(data)
    return keysAll_list


def reason(des, res):
    body = res.get('body') if isinstance(res, dict) else None
    if isinstance(body, dict) and body.get('success') == 0 and not isExtend(body, 'msg'):
        print(body)
    return 'Depiction: {},  failReason: {}'.format(des, body)
