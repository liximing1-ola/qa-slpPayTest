"""
通知机器人：企业微信群机器人 webhook

webhook 地址支持用环境变量覆盖，换群、轮换 key 都不用改代码：
    WX_BOT_SLP     企业微信机器人 webhook（默认指向不夜星球测试通知群）
只保留企业微信一个通道：slack webhook 与已下线项目（伴伴/PT/starify）的地址一并删除，
避免 key 继续留在仓库里。
"""
import os
from time import localtime, strftime, time

import requests

from common import method

# 企业微信群机器人 webhook
WX_BOTS = {
    'slp': os.environ.get('WX_BOT_SLP') or 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=998f0f30-0a19-4551-a9c5-def001c69908',
}


def _post(url, data):
    """发一条消息。企业微信用 200 + 响应体含 ok 表示发送成功"""
    return requests.post(url, headers={'Content-Type': 'application/json'}, json=data, timeout=5)


def _mention_all(url):
    """补充 @all 提醒：上一条消息发送成功后再补一条，避免重复打扰"""
    _post(url, {
        "msgtype": "text",
        "text": {
            "mentioned_mobile_list": ["@all"]
        }
    })


def robot(mode, reason, bot='slp'):
    """
    发送通知
    :param mode: markdown=正文即 markdown 内容；icon=带时间与配图的告警
    :param reason: 正文（markdown 模式即 markdown 内容；icon 模式显示在配图下方）
    :param bot: WX_BOTS 里的 key
    """
    if bot not in WX_BOTS:
        print('未配置的通知机器人: {}，可选: {}'.format(bot, list(WX_BOTS)))
        return
    url = WX_BOTS[bot]

    if mode == 'markdown':
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": reason
            }
        }

    elif mode == 'icon':
        now = strftime('%m-%d %H:%M', localtime(time()))
        data = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": "{}, Execution is abnormal.Please check the status!".format(now),
                        "description": reason,
                        "url": "https://www.12306.cn/index/",
                        "picurl": method.getImage(mode=1),
                    }
                ]
            }
        }

    else:
        # 只有 markdown / icon 在用（两个入口都传字面量）；早先的 fail / success / slack
        # 随旧项目下线已无人调用，需要时从 git 历史取回
        print('robot 未支持的 mode: {}'.format(mode))
        return

    response = _post(url, data)
    # 只有告警（icon）发送成功后再补一条 @all，汇总消息不重复打扰
    if mode == 'icon' and response.status_code == 200 and 'ok' in response.text:
        _mention_all(url)


if __name__ == '__main__':
    robot('markdown', reason='commit')
