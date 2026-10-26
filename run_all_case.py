# coding=utf-8
import os
import unittest
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config
from common.Session import Session
from common.report import AllTestRunner, not_pass_summary, split_message

# 是否在通知里逐条列出通过的用例：默认关闭。通过用例动辄上百条，会把消息撞到企微 4096 字节上限，
# 导致真正需要看的失败/异常清单被截断；需要看全量明细时用 LIST_PASS=1 临时打开
LIST_PASS = os.environ.get('LIST_PASS', '0') == '1'


def main(appInfo):
	if appInfo == config.appName['不夜星球'] or appInfo == config.appName['小拾光']:
		to = 'wx'
		print("*" * 50)
		print(f"消息推送到:{to}")
		print("*" * 50)
		# 刷新 Token（只调用一次）
		Session.getSession(appInfo)

		# 检查代码更新（不阻塞测试执行）
		updateCode.autoGitPull('slp_php')
		updateCode.autoGitPull('slp_common_rpc')
		updateTime('write', now=str(int(time())))

		# 执行测试
		test_result = AllTestRunner(verbosity=0).run(all_case(appInfo))
		Consts.endTime = time()

		pass_count = len(test_result.successes)
		fail_count = len(test_result.failures)
		error_count = len(test_result.errors)
		skip_count = len(test_result.skipped)
		des = "用例总数: {}, 通过: {}, 失败: {}, 异常: {}, 跳过: {}".format(
			test_result.testsRun, pass_count, fail_count, error_count, skip_count)
		Logs.get_log('caseResult.log').info(des)

		# 未通过用例放在最前面：企微单条 markdown 上限 4096 字节，超长会被静默截断，
		# 通过用例若逐条列出会占满篇幅，把真正要看的结论挤到截断区之外
		lines = [f"des: {des}", "", not_pass_summary(test_result)]
		if LIST_PASS:
			lines.append("")
			lines.append("通过用例：")
			for case in test_result.successes:
				lines.append("{} - PASS".format(test_result.test_des_map.get(case, case.id())))

		# 仍然超长时按字节拆成多条推送，避免被企微静默截断
		for chunk in split_message(lines):
			robot('markdown', chunk, bot='slp')

		# 记录失败日志
		if fail_count >= 1:
			Logs.get_log('failCase.log').error("failures: {}".format(test_result.failures))
		if error_count >= 1:
			Logs.get_log('failCase.log').error("error: {}".format(test_result.errors))
	else:
		Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))


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
		main(config.appName['不夜星球'])
	elif arg == config.appName['小拾光'] or arg == 'xsg':
		main(config.appName['小拾光'])
	else:
		main(config.appName['不夜星球'])
