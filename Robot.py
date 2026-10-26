from time import time, strftime, localtime
import requests
from common import method


def robot(mode, reason, title='', bot='BB', color="good", to='wx'):
    headers = {'Content-Type': 'application/json'}
    #  企微
    robot_dict_wechat = {
        'BB': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f9d916cb-6b93-4389-8aa4-f51c755faa0e',
        'test': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0179d8d1-2078-41ba-a8da-0fb11bd51880',
        'PT': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b05a239e-3cc3-4faf-a3cc-c77e200ae1e6',
        'slp': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=998f0f30-0a19-4551-a9c5-def001c69908',
    }
    #  slack
    robot_dict = {
        'BB': 'https://hooks.slack.com/services/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',
        'PT': 'https://hooks.slack.com/workflows/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',
        # 'starify': 'https://hooks.slack.com/services/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',
        # 'starify': 'https://hooks.slack.com/services/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',  # todo 调试
        'slp': 'https://hooks.slack.com/services/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',  # todo 调试
    }
    if to == 'slack':
        url = robot_dict[bot]
    else:
        url = robot_dict_wechat[bot]

    if mode == 'fail':
        content = "警告! 失败用例: {}, 失败原因: {}".format(title, reason)
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        r = requests.post(url, headers=headers, json=data)
        if r.status_code == 200 and r.text.find('ok'):
            data = {
                "msgtype": "text",
                "text": {
                    "mentioned_mobile_list": ["all"]
                }
            }
            requests.post(url, headers=headers, json=data)

    elif mode == 'success':
        data = {
            "msgtype": "text",
            "text": {
                "content": reason
            }
        }
        requests.post(url, headers=headers, json=data)

    elif mode == 'markdown':
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": reason
            }
        }
        requests.post(url, headers=headers, json=data)

    elif mode == 'icon':
        now = strftime('%m-%d %H:%M', localtime(time()))
        title = "{}, Execution is abnormal.Please check the status!".format(now)
        des = reason
        icon = method.getImage(mode=1)
        data = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": des,
                        "url": "https://www.12306.cn/index/",
                        "picurl": icon,
                    }
                ]
            }
        }
        r = requests.post(url, headers=headers, json=data)
        if r.status_code == 200 and r.text.find('ok'):
            data = {
                "msgtype": "text",
                "text": {
                    "mentioned_mobile_list": ["@all"]
                }
            }
            requests.post(url, headers=headers, json=data)

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
        requests.post(url, headers=headers, json=data)

    elif mode == 'slack_pt':
        data = {
            "title": title,
            "value": reason,
        }
        requests.post(url, headers=headers, json=data)

    elif mode == 'wxBot':
        data = {
            "msgtype": "text",
            "text": {
                "content": reason
            }
        }
        url = robot_dict_wechat['BB']
        requests.post(url, headers=headers, json=data)

    else:
        print('robot over gg')


if __name__ == '__main__':
    robot('slack', reason='commit')
