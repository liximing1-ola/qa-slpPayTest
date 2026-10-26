# coding=utf-8
import unittest
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config


class AllTestResult(unittest.TextTestResult):
    """自定义测试结果类，记录所有用例（通过/失败/异常）"""
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)


class AllTestRunner(unittest.TextTestRunner):
    """自定义测试运行器，返回 AllTestResult"""
    resultclass = AllTestResult


def main(appInfo):
	if appInfo == config.appName['不夜星球'] or appInfo == config.appName['小拾光']:
		to = 'wx'
		print("*" * 50)
		print(f"消息推送到:{to}")
		print("*" * 50)
		if updateCode.autoGitPull('slp_php', bot='slp', to=to, env=appInfo) | updateCode.autoGitPull('slp_common_rpc', bot='slp', to=to, env=appInfo):
			updateTime('write', now=str(int(time())))
			test_result = AllTestRunner(verbosity=0).run(all_case(appInfo))
			Consts.endTime = time()
			des = "用例总数: {}, 失败用例数: {}, 异常用例数: {}" \
				.format(test_result.testsRun, len(test_result.failures), len(test_result.errors))
			Logs.get_log('caseResult.log').info(des)

			# 构建消息内容
			lines = []
			lines.append(f"des: {des}")
			lines.append("")

			pass_count = len(test_result.successes)
			fail_count = len(test_result.failures)
			error_count = len(test_result.errors)

			lines.append(f"通过: {pass_count}  失败: {fail_count}  异常: {error_count}")
			lines.append("")

			# 列出所有通过的用例
			for case in test_result.successes:
				lines.append(f"✅ {case.id()} - PASS")

			# 列出失败的用例
			for case, reason in test_result.failures:
				lines.append(f"❌ {case.id()} - FAIL")

			# 列出异常的用例
			for case, reason in test_result.errors:
				lines.append(f"⚠️ {case.id()} - ERROR")

			message = "\n".join(lines)
			robot('markdown', message, bot='slp')

			# 记录失败日志
			if fail_count >= 1:
				Logs.get_log('failCase.log').error("failures: {}".format(test_result.failures))
			if error_count >= 1:
				Logs.get_log('failCase.log').error("error: {}".format(test_result.errors))
		else:
			Logs.get_log('runCode.log').info('NoRun')
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
	# discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
	#                                                pattern="test_pt_cnArea.py",
	#                                                top_level_dir=None)
	discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
	                                               pattern="test_*.py",
	                                               # pattern="test_gs_other_broker_slporder_room_new.py",
	                                               # pattern="test_gs_room_pay_self.py",
	                                               # pattern="test_naming_song.py",
	                                               # pattern="test_001.py",
	                                               # pattern="test_002.py",
	                                               # pattern="test_coupon.py",
	                                               top_level_dir=None)
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
