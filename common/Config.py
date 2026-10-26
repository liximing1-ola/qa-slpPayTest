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
        'slp_git_branch': "dev",  # todo 调试�?"wzx" / dev分支  dev
    }
    appName = {
        "不夜星球": 'slp',
        "小拾�?: 'xsg',
    }
    # 服务器标�?    linux_node = {
        'ali': 'iZbp1fveowr7j693hrwb48Z',
        'ali-slp': 'slp-dev',  # todo 修改 调试�?ubuntu / dev=iZj6cig35upuwmdws5sec2Z
        'ali-xsg': 'slp-dev',  # todo 修改 调试�?ubuntu / dev=iZj6cig35upuwmdws5sec2Z
    }
    # 内网支付接口
    slp_pay_url = appInfo['slp'] + 'pay/create?package=com.yhl.sleepless.android'
    xsg_pay_url = appInfo['xsg'] + 'pay/create?package=com.im.shiguang.android'
    # app登录方式
    slp_mobile_login_url = appInfo['slp'] + 'account/login'

