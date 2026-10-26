"""
通知机器人：企业微信群机器人 / slack webhook

webhook 地址支持用环境变量覆盖，换群、轮换 key 都不用改代码：
    WX_BOT_SLP     企业微信机器人 webhook（默认指向不夜星球测试通知群）
    SLACK_BOT_SLP  slack webhook
另外已下线项目（伴伴/PT/starify）的 webhook 一并删除，避免 key 继续留在仓库里。
"""
import os
from time import localtime, strftime, time

import requests

from common import method

# 企业微信群机器人 webhook
WX_BOTS = {
    'slp': os.environ.get('WX_BOT_SLP') or 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=998f0f30-0a19-4551-a9c5-def001c69908',
}

# slack webhook
SLACK_BOTS = {
    'slp': os.environ.get('SLACK_BOT_SLP') or 'https://hooks.slack.com/services/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',
}


def _mention_all(url, headers):
    """补充 @all 提醒：上一条消息发送成功后再补一条，避免重复打扰"""
    data = {
        "msgtype": "text",
        "text": {
            "mentioned_mobile_list": ["@all"]
        }
    }
    requests.post(url, headers=headers, json=data, timeout=5)


def robot(mode, reason, title='', bot='slp', color="good", to='wx'):
    """
    发送通知
    :param mode: fail / success / markdown / icon / slack
    :param reason: 正文（markdown 模式即 markdown 内容）
    :param title: 标题（fail / slack 模式使用）
    :param bot: WX_BOTS / SLACK_BOTS 里的 key
    :param color: slack 颜色
    :param to: wx=企业微信, slack=slack
    """
    headers = {'Content-Type': 'application/json'}
    bots = SLACK_BOTS if to == 'slack' else WX_BOTS
    if bot not in bots:
        print('未配置的通知机器人: {}，可选: {}'.format(bot, list(bots)))
        return
    url = bots[bot]

    if mode == 'fail':
        content = "警告! 失败用例: {}, 失败原因: {}".format(title, reason)
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        r = requests.post(url, headers=headers, json=data, timeout=5)
        if r.status_code == 200 and 'ok' in r.text:
            _mention_all(url, headers)

    elif mode == 'success':
        data = {
            "msgtype": "text",
            "text": {
                "content": reason
            }
        }
        requests.post(url, headers=headers, json=data, timeout=5)

    elif mode == 'markdown':
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": reason
            }
        }
        requests.post(url, headers=headers, json=data, timeout=5)

    elif mode == 'icon':
        now = strftime('%m-%d %H:%M', localtime(time()))
        title = "{}, Execution is abnormal.Please check the status!".format(now)
        data = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": reason,
                        "url": "https://www.12306.cn/index/",
                        "picurl": method.getImage(mode=1),
                    }
                ]
            }
        }
        r = requests.post(url, headers=headers, json=data, timeout=5)
        if r.status_code == 200 and 'ok' in r.text:
            _mention_all(url, headers)

    elif mode == 'slack':
        data = {
            "attachments": [
                {
                    "fallback": "",
                    "pretext": "",
                    "color": color,
                    "fields": [
                        {
                            "title": title,
                            "value": reason,
                            "short": 0
                        }
                    ]
                }
            ]
        }
        requests.post(url, headers=headers, json=data, timeout=5)

    else:
        print('robot over gg')


if __name__ == '__main__':
    robot('markdown', reason='commit')
