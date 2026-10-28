# coding=utf-8
import os


class config:
    # 工程目录
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    appInfo = {
        'slp': 'https://192.168.1.23/',
        'xsg': 'https://192.168.1.23/',
    }
    codeInfo = {

        'slp_php_path': r"/var/www/slp/slp-php",
        'slp_common_rpc_path': r"/home/ecs-user/webroot/slp-common-rpc",
        'slp_git_branch': "dev",  # todo 调试用 "wzx" / dev分支  dev
    }
    # App 名一律用缩写：同一份 App 既有中文名又有缩写，日志/推送/异常里就会出现两套说法，
    # 排查时要多做一次「这是哪个 App」的翻译，徒增歧义
    appName = {
        "SLP": 'slp',
        "XSG": 'xsg',
    }
    # 服务器标识
    linux_node = {
        'ali': 'iZbp1fveowr7j693hrwb48Z',
        'ali-slp': 'slp-dev',  # todo 修改 调试用 ubuntu / dev=iZj6cig35upuwmdws5sec2Z
        'ali-xsg': 'slp-dev',  # todo 修改 调试用 ubuntu / dev=iZj6cig35upuwmdws5sec2Z
    }
    # 内网支付接口
    slp_pay_url = appInfo['slp'] + 'pay/create?package=com.yhl.sleepless.android'
    xsg_pay_url = appInfo['xsg'] + 'pay/create?package=com.im.shiguang.android'
    # app登录方式
    slp_mobile_login_url = appInfo['slp'] + 'account/login'

