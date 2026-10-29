# coding=utf-8
"""执行前的环境体检：MySQL / Redis / 支付接口

为什么要有这道闸：环境不通时，用例会一条一条失败到结束，最后推一句「137 条全红」。
它不是回归信号，是噪音——而且比噪音更糟，因为「137 条全红」这个信号只能用一次，
被一场连不上库的抖动用掉之后，真出事时没人会再当回事。

四项探测互相独立，必须分别报：实测存在「接口能访问 192.168.1.23，但连不上
192.168.1.24:3306」的情况。一个通了就当全通，等于把最容易坏的那条藏起来。

第四项查的是「种子数据还在不在」：连得上库不等于数据还在。账号被清时一百多条用例
会集体变红，现象和服务器改坏了完全一样——不把这两种情况分开，排查方向从一开始就是错的。

每项重试 3 次才判定不可用：偶发的一次连接抖动不该让当天的回归整轮不跑。
判定不可用时不执行任何用例，退出码 3——不跑要明说，不能安静退出。

本机（Windows）一般不在测试环境内网里，探测必然失败；这不是限制，是防止在
本机白跑一轮、再把一堆「连不上」的假失败推给所有人。本机请只做静态检查：
    python -m compileall -q caseSlp caseXsg common
    python -m common.selfcheck
    python pre_push_audit.py
"""
import os
import platform
import time

import pymysql
import redis
import requests
from urllib3.exceptions import InsecureRequestWarning

from common import Logs
from common.Config import config

# 自签证书的测试环境会刷一屏 InsecureRequestWarning，探测只关心可达性，关掉
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 退出码：与 0 通过 / 1 有用例失败 / 2 没跑完 区分开
EXIT_ENV_DOWN = 3


def is_local_windows():
    """本机（Windows）默认只做静态检查"""
    return platform.system() == 'Windows'


def bypassed():
    """PREFLIGHT=0 跳过体检：只用于排查「体检误报」

    默认开启。做成开关而不是删探测：某天接口探针被 WAF 拦截而业务其实正常时，
    人需要一个不挡路的出口——但跳过会在控制台和 runCode.log 里各留一行，
    不然「这轮怎么没拦」就无从查证。cron 里永远不写它。
    """
    return os.environ.get('PREFLIGHT', '1') != '1'


def check_mysql(timeout=3):
    """连一次库并读一行：造数和断言都依赖它，连不上则整轮无意义"""
    from common.conSlpXsgMysql import conMysql
    db = conMysql.db_config
    host, user, password = db['ali_db'], db['ali_user'], db['ali_pas']
    try:
        con = pymysql.connect(host=host, port=3306, user=user, password=password,
                              connect_timeout=timeout, read_timeout=timeout)
    except Exception as error:
        return False, '{}:3306 连接失败（{}）'.format(host, error)
    try:
        with con.cursor() as cur:
            cur.execute('select 1')
            cur.fetchone()
    except Exception as error:
        return False, '{}:3306 查询失败（{}）'.format(host, error)
    finally:
        try:
            con.close()
        except Exception:
            pass
    return True, '{}:3306 可读'.format(host)


def check_redis(timeout=3):
    """部分用例要读房间缓存，缓存挂了会表现为「读不到数据」，容易被当成业务 bug"""
    from common.conRedis import conRedis
    host = conRedis.redis_config['host_slp']
    port = conRedis.redis_config['port']
    try:
        redis.Redis(host=host, port=port, socket_connect_timeout=timeout,
                    socket_timeout=timeout).ping()
    except Exception as error:
        return False, '{}:{} 连接失败（{}）'.format(host, port, error)
    return True, '{}:{} 可 ping'.format(host, port)


def check_http(app_key, timeout=5):
    """探接口网关：任何 HTTP 状态码都算可达，只有连不上/超时才是不通"""
    url = config.appInfo.get(app_key)
    if not url:
        return False, '未配置 {} 的接口地址'.format(app_key)
    try:
        response = requests.get(url, timeout=timeout, verify=False)
    except Exception as error:
        return False, '{} 不可达（{}）'.format(url, error)
    return True, '{} 可达（HTTP {}）'.format(url, response.status_code)


def check_data(timeout=5):
    """查种子数据还在不在：连得上库不等于数据还在

    账号被删时，一百多条用例会集体变红，现象和服务器改坏了完全一样，排查方向从一开始
    就是错的。这道探测就是为了把「环境被清理」和「服务端引入 bug」分开。

    只差集点名缺失的 id，不数总数：「缺 uid=200250759」能照着补，「少 1 个」还得自己数。
    表被 drop 也走查询失败分支——查不了就是环境有问题，不能当成数据还在。
    """
    from common.conSlpXsgMysql import conMysql
    from common.envData import seed_checks
    db = conMysql.db_config
    try:
        con = pymysql.connect(host=db['ali_db'], port=3306, user=db['ali_user'],
                              password=db['ali_pas'], connect_timeout=timeout,
                              read_timeout=timeout)
    except Exception as error:
        return False, '{}:3306 连不上，无法检查种子数据（{}）'.format(db['ali_db'], error)

    blocking, warnings = [], []
    try:
        with con.cursor() as cur:
            for name, sql, expected, hint, is_blocking in seed_checks():
                collected = blocking if is_blocking else warnings
                try:
                    cur.execute(sql.format(','.join(str(item) for item in expected)))
                    present = {row[0] for row in cur.fetchall()}
                except Exception as error:
                    collected.append('{} 查询失败（{}）'.format(name, str(error)[:60]))
                    continue
                missing = [item for item in expected if item not in present]
                if not missing:
                    continue
                text = '{}缺 {} 个：{}'.format(
                    name, len(missing),
                    ', '.join(str(item) for item in missing[:3]) + (' 等' if len(missing) > 3 else ''))
                collected.append(text + '；' + hint)
    finally:
        try:
            con.close()
        except Exception:
            pass

    if blocking:
        return False, '；'.join(blocking)
    if warnings:
        return True, '种子基本齐全（{}）'.format('；'.join(warnings))
    return True, '账号/房间/礼物/工会 种子齐全'


def check_all(app_key, retries=3, interval=3, timeout=3, log=print):
    """逐项探测，返回 (是否全部可用, [{'name','ok','detail'}, ...])

    :param app_key: slp / xsg，决定探哪个接口地址
    :param retries: 每项最多试几次；偶发抖动不该让当天整轮不跑
    :param interval: 重试间隔（秒）
    """
    targets = [
        ('MySQL', lambda: check_mysql(timeout), retries),
        # 数据缺失不会靠重试长回来，只探一次，免得闸门平白多耗十几秒
        ('数据', lambda: check_data(timeout), 1),
        ('Redis', lambda: check_redis(timeout), retries),
        ('接口', lambda: check_http(app_key, timeout=max(timeout, 5)), retries),
    ]
    rows = []
    mysql_ok = True
    for name, probe, attempts in targets:
        if name == '数据' and not mysql_ok:
            # MySQL 那条已经把根因说清了，这里再报一遍只会让失败项翻倍、把真问题淹掉
            rows.append({'name': name, 'ok': True, 'detail': '跳过（MySQL 不可用）'})
            continue
        ok, detail = False, ''
        for attempt in range(1, attempts + 1):
            ok, detail = probe()
            if ok:
                break
            if attempt < attempts:
                log('[环境] {} 第 {}/{} 次探测失败，{} 秒后重试: {}'.format(
                    name, attempt, attempts, interval, detail))
                time.sleep(interval)
        if name == 'MySQL':
            mysql_ok = ok
        rows.append({'name': name, 'ok': ok, 'detail': detail})
    return all(row['ok'] for row in rows), rows


def describe(rows):
    """排成几行，控制台与日志直接用；失败项放前面，先看坏的那个"""
    ordered = [row for row in rows if not row['ok']] + [row for row in rows if row['ok']]
    return ['{} {:<6}{}'.format('FAIL' if not row['ok'] else 'OK  ', row['name'], row['detail'])
            for row in ordered]


def gate(app_key):
    """开跑前的闸：探测、逐项打印、落日志，返回 (是否可跑, rows, 提示语)

    两个入口（定时任务 / 手工全量）都走这里。判定一旦分成两份写，就会出现
    「一个入口拦住了、另一个还在白跑一轮」这种最难查的差异。
    """
    if bypassed():
        print('[环境] 体检已按 PREFLIGHT=0 跳过，本轮结果不代表环境可用', flush=True)
        Logs.get_log('runCode.log', console=False).warning('环境体检被 PREFLIGHT=0 跳过')
        return True, [], ''

    ok, rows = check_all(app_key, retries=1 if is_local_windows() else 3)
    detail = '\n'.join(describe(rows))
    print('[环境] ' + detail.replace('\n', '\n[环境] '), flush=True)
    if ok:
        return True, rows, ''

    hint = local_hint() or restore_hint(rows)
    print('[环境] 本轮不执行任何用例', flush=True)
    if hint:
        print('[环境] ' + hint, flush=True)
    Logs.get_log('runCode.log', console=False).error(
        '环境不可用，本轮未执行\n' + detail + ('\n' + hint if hint else ''))
    return False, rows, hint


def push_message(rows, hint=''):
    """推送用的「环境不可用」消息：只列失败项，附一行本机提示

    三项全通时不会走到这里；通了的项也不列，推一条只有名字的灰字没有意义。
    """
    lines = ['<font color="warning">**环境不可用，本轮未执行**</font>']
    for row in rows:
        if row['ok']:
            continue
        # 错误里常带一长串 urllib3 上下文，推送里只留关键部分
        lines.append('<font color="comment">{}　{}</font>'.format(row['name'], row['detail'][:80]))
    if hint:
        lines.append('<font color="comment">{}</font>'.format(hint))
    return lines


def local_hint():
    """本机探测失败时的说明：告诉人该干什么，而不是只报一句连接失败"""
    if is_local_windows():
        return ('本机不在测试环境内网，真实用例请在服务器执行。'
                '本机只做静态检查：compileall / selfcheck / pre_push_audit')
    return ''


def restore_hint(rows):
    """种子缺失时补一句怎么恢复：只说「环境不可用」等于让人从零开始查"""
    if not any(row['name'] == '数据' and not row['ok'] for row in rows):
        return ''
    return ('种子数据缺失通常是测试环境被清理或重置过。'
            '先用 python backup_seed.py list 看有无快照，再 restore 到最近一份；'
            '没有快照就按 DEPLOY.md 重建账号/房间/工会')


if __name__ == '__main__':
    import sys
    app = sys.argv[1] if len(sys.argv) > 1 else 'slp'
    # 与入口共用 gate：单独跑体检时看到的东西，和入口里打出来的必须一致
    ok, _rows, _hint = gate(app)
    sys.exit(0 if ok else EXIT_ENV_DOWN)
