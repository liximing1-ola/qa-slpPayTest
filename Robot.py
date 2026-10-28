"""
通知机器人：企业微信群机器人 webhook

webhook 地址只从环境变量读，仓库里不留默认值：
    WX_BOT_SLP     企业微信机器人 webhook（不夜星球测试通知群）

key 相当于「在群里发言」的权限。一旦提交进 git，它就会永久留在历史里——
后续删掉文件也回收不了（谁 clone 都能翻出来），只能重新生成地址来作废。
所以这类值一律走环境变量，不进代码。

未配置时推送跳过并在控制台/日志里明确提示，不影响用例执行，也不影响退出码。
"""
import os

import requests

# 机器人别名 -> 环境变量名。别名仍保留，是为了调用点写 bot='slp' 而不是记环境变量名
WX_BOT_ENV = {'slp': 'WX_BOT_SLP'}


def _post(url, data):
    """发一条消息。企业微信用 200 + 响应体含 ok 表示发送成功"""
    return requests.post(url, headers={'Content-Type': 'application/json'}, json=data, timeout=5)


def _bot_url(bot):
    """取机器人 webhook；别名不存在或环境变量没设时返回 None（并说明原因）"""
    env = WX_BOT_ENV.get(bot)
    if not env:
        print('未配置的通知机器人: {}，可选: {}'.format(bot, list(WX_BOT_ENV)))
        return None
    url = (os.environ.get(env) or '').strip()
    if not url:
        print('未设置 {}（企业微信群机器人 webhook），本次跳过推送'.format(env))
        return None
    return url


def robot(mode, reason, bot='slp'):
    """
    发送通知
    :param mode: markdown=正文即 markdown 内容（早先的 icon 配图消息随旧项目下线删除，
                 它依赖外网图床，失败时反而把通知本身带崩）
    :param reason: 正文（markdown 内容）
    :param bot: WX_BOT_ENV 里的别名
    :return: True 已发送 / False 未发送（未配置 webhook、网络异常或服务端返回失败）
    """
    url = _bot_url(bot)
    if not url:
        return False
    if mode != 'markdown':
        # 只有 markdown 在用；旧项目的 icon / fail / success / slack 模式需要时从 git 历史取回
        print('robot 未支持的 mode: {}'.format(mode))
        return False

    data = {"msgtype": "markdown", "markdown": {"content": reason}}
    try:
        response = _post(url, data)
    except Exception as error:
        # 网络问题不该把「用例跑完了」变成「执行异常」：调用方按 False 记日志即可
        print('企业微信推送异常: {}'.format(error))
        return False
    return response.status_code == 200 and 'ok' in response.text


if __name__ == '__main__':
    robot('markdown', reason='commit')
