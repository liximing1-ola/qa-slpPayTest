# coding=utf-8
import inspect
import unittest
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config
from common.Session import Session


def extract_des_from_docstring(docstring):
    """从测试方法 docstring 中提取用例描述（用例描述：与脚本步骤：之间的第一行非空文本）"""
    if not docstring:
        return None
    lines = docstring.splitlines()
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('用例描述'):
            capture = True
            # 如果 "用例描述：" 同行后面有内容，直接取
            after_colon = stripped.split('：', 1)[-1].strip()
            if after_colon:
                return after_colon
            continue
        if capture and stripped.startswith('脚本步骤'):
            break
        if capture and stripped:
            return stripped
    return None


class AllTestResult(unittest.TextTestResult):
    """自定义测试结果类，记录所有用例（通过/失败/异常）"""
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []
        self.test_des_map = {}  # 记录每个测试的 des 值

    def startTest(self, test):
        super().startTest(test)
        # 优先从方法签名的 des 默认参数获取，其次从 docstring 提取
        try:
            method = getattr(test, test._testMethodName)
            # 方式1: 从方法签名获取 des 默认值
            sig = inspect.signature(method)
            des_param = sig.parameters.get('des', None)
            if des_param is not None and des_param.default is not inspect.Parameter.empty:
                self.test_des_map[test] = des_param.default
                return
            # 方式2: 从 docstring 提取用例描述
            docstring = test._testMethodDoc
            if docstring:
                des = extract_des_from_docstring(docstring)
                if des:
                    self.test_des_map[test] = des
        except Exception:
            pass

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
		# 刷新 Token（只调用一次）
		Session.getSession(appInfo)

		# 检查代码更新（不阻塞测试执行）
		updateCode.autoGitPull('slp_php', bot='slp', to=to, env=appInfo)
		updateCode.autoGitPull('slp_common_rpc', bot='slp', to=to, env=appInfo)
		updateTime('write', now=str(int(time())))

		# 执行测试
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
			des_val = test_result.test_des_map.get(case, case.id())
			lines.append(f"{des_val} - PASS")

		# 列出失败的用例
		for case, reason_str in test_result.failures:
			des_val = test_result.test_des_map.get(case, case.id())
			lines.append(f"{des_val} - FAIL")
			# 从 reason 中提取响应体（去掉 "Depiction: xxx, failReason: " 前缀）
			if "failReason:" in reason_str:
				body_part = reason_str.split("failReason:", 1)[1].strip()
				lines.append(f"  {body_part}")

		# 列出异常的用例
		for case, reason_str in test_result.errors:
			des_val = test_result.test_des_map.get(case, case.id())
			lines.append(f"{des_val} - ERROR")
			lines.append(f"  {str(reason_str)[:200]}")

		message = "\n".join(lines)
		robot('markdown', message, bot='slp')

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
