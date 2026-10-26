# coding=utf-8
import os
import unittest
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config
from common.Session import Session
from common.report import (AllTestRunner, fail_detail_text, not_pass_report,
						   not_pass_summary, result_counts, split_message)

# 是否推送到企业微信群：默认关闭。当前直接在云服务器上看日志，企业微信的 markdown 展示效果不理想，
# 需要恢复推送时用 PUSH_WX=1
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
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
		test_result = AllTestRunner(verbosity=2).run(all_case(appInfo))
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
		report_text = not_pass_report(test_result, title='[{}] 未通过用例'.format(appInfo))
		print(report_text, flush=True)
		Logs.get_log('notPassCase.log', console=False, back_count=30).info(report_text)

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


def all_case(appInfo):
	case_dir = config.BASE_PATH
	if appInfo == config.appName['不夜星球']:
		case_dir += '/caseSlp'
	elif appInfo == config.appName['小拾光']:
		case_dir += '/caseXsg'
	else:
		return

	testcase = unittest.TestSuite()
	# 全量执行：pattern 可按需改成单个文件名调试
	discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
	                                               pattern="test_*.py",
	                                               top_level_dir=config.BASE_PATH)
	testcase.addTests(discover)
	return testcase


if __name__ == "__main__":
	import sys

	if len(sys.argv) >= 2:
		arg = sys.argv[1].strip().lower()
	else:
		arg = None

	if arg == config.appName['不夜星球'] or arg == 'slp':
		counts = main(config.appName['不夜星球'])
	elif arg == config.appName['小拾光'] or arg == 'xsg':
		counts = main(config.appName['小拾光'])
	else:
		counts = main(config.appName['不夜星球'])

	# 退出码：有失败/异常时返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
	sys.exit(1 if counts and (counts['fail'] or counts['error']) else 0)
