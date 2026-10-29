# coding=utf-8
import os

from common.envLocal import get


class config:
    # 工程目录
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    # 接口地址不进仓库：值取环境变量 APP_HOST 或 common/env_local.py，模板见 env_local.example.py
    # 末尾统一补一个 /，拼 pay_url 时不必各自判断
    _host = (get('APP_HOST') or 'http://127.0.0.1').rstrip('/') + '/'
    appInfo = {
        'slp': _host,
        'xsg': _host,
    }
    codeInfo = {
        'slp_git_branch': "dev",  # todo 调试用 "wzx" / dev分支  dev
    }
    # App 名一律用缩写：同一份 App 既有中文名又有缩写，日志/推送/异常里就会出现两套说法，
    # 排查时要多做一次「这是哪个 App」的翻译，徒增歧义
    appName = {
        "SLP": 'slp',
        "XSG": 'xsg',
    }
    # 服务器标识：用于判断是否同机房（决定状态码断言前要不要等），空值表示不认识这台机器
    linux_node = {
        'ali': get('NODE_ALI') or '',
        'ali-slp': get('NODE_ALI_SLP') or '',
        'ali-xsg': get('NODE_ALI_XSG') or '',
    }
    # 内网支付接口
    slp_pay_url = appInfo['slp'] + 'pay/create?package=com.yhl.sleepless.android'
    xsg_pay_url = appInfo['xsg'] + 'pay/create?package=com.im.shiguang.android'
    # app登录方式
    slp_mobile_login_url = appInfo['slp'] + 'account/login'

