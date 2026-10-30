# coding=utf-8
"""两个入口共用的执行流程片段：环境体检结论、刷新 token、计数与清单落盘

`run_all_case.py`（手工全量）和 `run_crontab_case.py`（定时任务）各写过一份，已经漂过一次：
定时入口有分片续号和推送失败日志、有场景族统计，全量入口都没有；同名日志行一个带 App 前缀、
一个不带。这些差异没有一处是刻意设计的，全是各改各改出来的。

所以把「两个入口都必须一致」的步骤收在这里：改一处，两个入口一起生效。只属于某个入口的
东西——拉取被测服务端代码、逐条播报通过用例、耗时与版本号、执行中断兜底——留在各自文件里。

`common/report.py` 保持纯格式化：给数据、返回字符串，不打印、不写日志。这里才是落盘的地方。
"""
from Robot import robot
from common import Logs, preflight
from common.Session import Session
from common.report import (fail_detail_text, fail_kind_report, group_report, not_pass_report,
                           result_counts, retry_report, retry_summary, server_error_report,
                           server_error_summary, split_message)


def push_lines(lines, app_info):
    """按企微单条上限拆分后逐条推送，返回是否全部发送成功

    推送失败不能改变本轮结论：网络抖动时 requests 会抛异常，这时只记日志、
    退出码仍然只表达「用例过没过」。但必须留下痕迹——群里没消息很容易被当成
    「今天没跑」，而不是「推送坏了」。
    """
    ok = True
    chunks = split_message(lines)
    total = len(chunks)
    for index, chunk in enumerate(chunks, 1):
        if index > 1:
            # 第二条起是「清单续」：单独出现在群里时看不出属于哪一轮，标上序号
            chunk = '<font color="comment">{} ({}/{}) 清单续</font>\n{}'.format(
                app_info, index, total, chunk)
        try:
            # robot 内部已经兜住了网络异常，这里再包一层是防以后改动把异常漏出去
            sent = robot('markdown', chunk, bot='slp')
        except Exception as error:
            sent = False
            print('[{}] 企业微信推送异常: {}'.format(app_info, error), flush=True)
        if sent:
            continue
        ok = False
        # 最可能是 WX_BOT_SLP 没设：群里没消息，日志里必须能查到原因
        Logs.get_log('runCode.log', console=False).error(
            '[{}] 企业微信消息未发出（检查 WX_BOT_SLP），内容前 80 字: {}'.format(app_info, chunk[:80]))
    return ok


def env_down_notify(app_info, rows, hint, push):
    """环境体检不通过：本轮一条用例都不跑，把体检结论发出去（有推送通道时）"""
    if not push:
        return
    push_lines(preflight.push_message(rows, hint), app_info)


def refresh_token(app_info):
    """开跑前刷新一次 token：token 过期时用例会逐条失败，那不是回归信号

    不直接带着 traceback 退出：记日志后继续跑，用例逐条报错比「一条都没跑」更容易定位。
    """
    try:
        Session.getSession(app_info)
    except Exception as error:
        # console=False：否则会先给 caseResult.log 挂上控制台 handler，导致后面同名的 console=False 失效
        Logs.get_log('caseResult.log', console=False).error('[{}] 刷新 token 失败: {}'.format(app_info, error))


def counts_text(counts, app_info):
    """结论行的文案：带 App 前缀，两处日志文件是共用的，不带前缀分不清是哪个 App"""
    return "[{}] 用例总数: {}, 通过: {}, 失败: {}, 异常: {}, 跳过: {}".format(
        app_info, counts['total'], counts['pass'], counts['fail'], counts['error'], counts['skip'])


def log_counts(test_result, app_info):
    """结算计数并落盘，返回 counts（供退出码与推送使用）

    用 result_counts 而不是 testsRun - 失败 - 异常 - 跳过：setUpClass 报错时 testsRun
    不含这条，相减会把「通过」算成负数。
    """
    counts = result_counts(test_result)
    des = counts_text(counts, app_info)
    # flush=True：stdout 重定向到文件时是块缓冲，不刷会延迟到进程退出才落盘
    print(des, flush=True)
    Logs.get_log('caseResult.log', console=False).info(des)
    return counts


def log_retry(test_result):
    """重试记录落盘：摘要固定一行，明细只在有条目时才写

    重试后才通过的用例最终状态是 PASS，但每条背后都是一次真实的断言失败。定时任务场景
    控制台没人看，所以摘要同时写 caseResult.log 与 runCode.log，明细写 retryCase.log。
    """
    retry_line = retry_summary(test_result)
    print(retry_line, flush=True)
    Logs.get_log('caseResult.log', console=False).info(retry_line)
    Logs.get_log('runCode.log', console=False).info(retry_line)
    retry_text = retry_report(test_result)
    if retry_text:
        print(retry_text, flush=True)
        Logs.get_log('retryCase.log', console=False, back_count=30).info(retry_text)


def log_server_errors():
    """接口 5xx 台账：固定一行摘要 + 明细，控制台与 caseResult.log 各一份

    5xx 不会被频控重试兜，但会被 @Retry 兜：那条用例最终是 PASS，与一次就过的
    长得一模一样。摘要行让「本轮偶发几次」始终可见——2026-10-30 的 breaker open
    只能靠翻截图定位，就是因为这个数字从来没被打印过。

    延迟 import：Request 是上层请求封装，且它会反向引用 Scene，放模块顶部
    会把「执行流程」和「请求封装」绑成环。
    """
    from common.Request import server_error_records

    records = server_error_records()
    line = server_error_summary(records)
    print(line, flush=True)
    Logs.get_log('caseResult.log', console=False).info(line)
    detail = server_error_report(records)
    if detail:
        print(detail, flush=True)
        Logs.get_log('caseResult.log', console=False).info(detail)


def console_reports(test_result, app_info):
    """未通过清单、失败性质、场景族统计、完整堆栈：控制台看摘要，日志留全量

    失败性质（连不上库 / 分成算错）决定下一步是重跑还是查代码；场景族统计回答的是
    「某一类整体跨了，还是东一条西一条」——只看失败清单回答不了这个问题。
    """
    # 5xx 台账放在清单前面：先看「本轮服务端抖了几次」，再逐条看红
    log_server_errors()

    report_text = not_pass_report(test_result, title='[{}] 未通过用例'.format(app_info))
    print(report_text, flush=True)
    Logs.get_log('notPassCase.log', console=False, back_count=30).info(report_text)

    kind_text = fail_kind_report(test_result)
    if kind_text:
        print(kind_text, flush=True)
        Logs.get_log('caseResult.log', console=False).info(kind_text)

    group_text = group_report(test_result)
    if group_text:
        print(group_text, flush=True)
        Logs.get_log('caseResult.log', console=False).info(group_text)

    # 完整堆栈只写文件、不打控制台：控制台已有上面带编号的清单，
    # 而 unittest 的 failures 列表直接 format 是一整行带 \n 转义的 repr，堆栈全糊在一起
    if test_result.failures or test_result.errors:
        Logs.get_log('failCase.log', console=False, back_count=30).error(fail_detail_text(test_result))
        print('失败/异常完整堆栈: log/failCase.log', flush=True)
