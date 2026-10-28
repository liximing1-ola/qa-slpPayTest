# coding=utf-8
import os
import sys
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config
from common.Session import Session
from common.report import (AllTestRunner, build_suite, fail_detail_text, not_pass_report,
						   not_pass_summary, parse_app, result_counts, retry_report, retry_summary, split_message)

# 是否推送到企业微信群：默认关闭。当前直接在云服务器上看日志，企业微信的 markdown 展示效果不理想，
# 需要恢复推送时用 PUSH_WX=1
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 只跑指定用例（调试用）：不设则全量执行。
#   CASE=test_check                                          只跑 caseSlp/test_check.py
#   CASE=test_check.TestPayCreate.test_002,test_check.TestPayCreate.test_012
# unittest 的 discover 只能按**文件名** glob，写用例名是匹配不到文件的，所以两种写法分开处理
CASE = os.environ.get('CASE', '').strip()
# 推送时是否额外逐条列出通过的用例：默认关闭，通过用例动辄上百条，会把真正要看的失败清单挤到后面
LIST_PASS = os.environ.get('LIST_PASS', '0') == '1'


def main(appInfo):
	if appInfo == config.appName['不夜星球'] or appInfo == config.appName['小拾光']:
		to = 'wx'
		print("*" * 50)
		# 开关关掉时不要再打"消息推送到:wx"，否则日志里会和后面的"推送已关闭"互相矛盾
		print('消息推送: {}'.format('{}（PUSH_WX=1）'.format(to) if PUSH_WX else '已关闭（PUSH_WX=0），结果只输出到控制台与日志'))
		print("*" * 50)
		# 刷新 Token（只调用一次）
		# 与 run_crontab_case 保持一致：token 服务异常时不直接带着 traceback 退出，记日志后继续跑，
		# 用例会逐条报错，比"一条都没跑"更容易定位
		try:
			Session.getSession(appInfo)
		except Exception as error:
			Logs.get_log('caseResult.log', console=False).error('[{}] 刷新 token 失败: {}'.format(appInfo, error))

		# 检查代码更新（不阻塞测试执行）
		updateCode.autoGitPull('slp_php')
		updateCode.autoGitPull('slp_common_rpc')
		updateTime('write', now=str(int(time())))

		# 执行测试
		test_result = AllTestRunner(verbosity=2).run(build_suite(appInfo, CASE))
		Consts.endTime = time()

		# result_counts 会把 setUpClass/tearDownClass 报错补进总数，避免「总数: 0, 异常: 1」或「通过: -1」
		counts = result_counts(test_result)
		pass_count = counts['pass']
		fail_count = counts['fail']
		error_count = counts['error']
		skip_count = counts['skip']
		des = "用例总数: {}, 通过: {}, 失败: {}, 异常: {}, 跳过: {}".format(
			counts['total'], pass_count, fail_count, error_count, skip_count)

		# 结果直接打到控制台（nohup / crontab 的输出日志里能直接看到），
		# 同时落到 log/notPassCase.log（只写文件，不与上面的 print 重复）；
		# flush=True：stdout 重定向到文件时是块缓冲，不刷会延迟到进程退出才落盘
		print(des, flush=True)
		Logs.get_log('caseResult.log', console=False).info(des)
		# 固定行：重试率是「被 @Retry 兜住的服务端问题」唯一的存在证明。没有这一行，
		# 「全绿」就分不出「真的没问题」和「有问题但被重试掉了」。
		print(retry_summary(test_result), flush=True)
		report_text = not_pass_report(test_result, title='[{}] 未通过用例'.format(appInfo))
		print(report_text, flush=True)
		Logs.get_log('notPassCase.log', console=False, back_count=30).info(report_text)

		# 重试后才通过的用例：最终状态是 PASS，但每条背后都是一次真实的断言失败。
		# 一轮全量实测 54 次，不看这份就等于每轮主动丢掉几十条排查线索
		retry_text = retry_report(test_result)
		if retry_text:
			print(retry_text, flush=True)
			Logs.get_log('retryCase.log', console=False, back_count=30).info(retry_text)

		if PUSH_WX:
			# 推送时才拼消息：未通过用例放在最前面，避免末尾结论被截断
			lines = ["des: {}".format(des), "", not_pass_summary(test_result)]
			if LIST_PASS:
				lines.append("")
				lines.append("通过用例：")
				for case in test_result.successes:
					lines.append("{} - PASS".format(test_result.test_des_map.get(case, case.id())))
			# 仍然超长时按字节拆成多条推送
			for chunk in split_message(lines):
				robot('markdown', chunk, bot='slp')
		else:
			print('企业微信推送已关闭（PUSH_WX=0），完整结果见上方输出与 log/notPassCase.log', flush=True)

		# 失败/异常的完整堆栈只写文件、不打控制台：
		# 1. 控制台已经有上方带编号的完整清单；
		# 2. unittest 的 failures 列表直接 format 是一整行带 \n 转义的 repr，堆栈全糊在一起，没法看
		if fail_count or error_count:
			Logs.get_log('failCase.log', console=False, back_count=30).error(fail_detail_text(test_result))
			print('失败/异常完整堆栈: log/failCase.log', flush=True)
		return counts
	else:
		Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))
		return None


if __name__ == "__main__":
	counts = main(parse_app(sys.argv))

	# 退出码：有失败/异常时返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
	sys.exit(1 if counts and (counts['fail'] or counts['error']) else 0)
