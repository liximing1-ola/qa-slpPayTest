# coding=utf-8
"""统计单条用例的复现率：连跑 N 轮，分别数红 / 绿 / 未测到

为什么不在用例里循环：一条用例的结论只有通过/失败两档，表达不了「10 轮里红 2 次」；
而「未测到」（被服务端限流挡下、根本没走到被测逻辑）更不是失败，混进分子会让数字
虚高，混进分母会让数字虚低。所以要分开数。

为什么每轮起独立进程：与人工反复执行完全一致。同进程里连着跑，token、连接池、
上一轮残留的线程状态都可能影响结论，统计出来的就不是「独立一次执行」的概率。

用 `python -m unittest` 直接跑单条：复现统计不需要入口的体检与汇总，需要的是干净的单轮结论。

用法：
    python run_reproduce.py                                   # 默认 test_004 跑 10 轮
    python run_reproduce.py --rounds 20 --stagger 0.2
    python run_reproduce.py --case caseStress.test_pay_concurrent.TestConcurrentPay.test_002

判读：
    复现率 = 红 / (红 + 绿)，未测到与无效轮次不进分母。
    10 轮全绿且未测到 0，就说明这条路径当前打不出来，用例该降级为现状探测；
    出现过红就是硬证据，红的那轮完整输出会存进 log/reproduce-*.log，可直接拿去提单。
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

DEFAULT_CASE = 'caseStress.test_pay_concurrent.TestConcurrentPay.test_004'
ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, 'log')


def classify(code, output):
    """一轮的结论：红优先（有断言失败就是硬证据），其次未测到，最后才是绿

    退出码 2/3 是「没跑完 / 环境不通」，不算任何一种业务结论，单列成无效。
    """
    if code == 1:
        return 'red'
    if code == 0 and '[未测到]' in output:
        return 'blind'
    if code == 0:
        return 'green'
    return 'invalid'


def key_line(output):
    """挑一行能代表本轮结论的输出：未测到的原因优先，其次断言失败现场，最后看计数"""
    for marker in ('[未测到]', 'AssertionError', '扣款=', '[并发-自刷]', '[并发-同账号]'):
        for line in output.splitlines():
            if marker in line:
                return line.strip()[:130]
    return ''


def run_round(case, stagger, timeout):
    env = dict(os.environ, PUSH_WX='0')
    if stagger is not None:
        env['STAGGER'] = str(stagger)
    done = subprocess.run([sys.executable, '-m', 'unittest', case], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='ignore', timeout=timeout)
    return done.returncode, (done.stdout or '') + (done.stderr or '')


def main():
    parser = argparse.ArgumentParser(description='统计单条用例的复现率')
    parser.add_argument('--case', default=DEFAULT_CASE)
    parser.add_argument('--rounds', type=int, default=10)
    parser.add_argument('--stagger', type=float, default=None)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if not os.path.isdir(LOG_DIR):
        os.makedirs(LOG_DIR)
    evidence_path = os.path.join(LOG_DIR, 'reproduce-{}.log'.format(stamp))

    tally = {'red': 0, 'green': 0, 'blind': 0, 'invalid': 0}
    print('[复现] {} 跑 {} 轮{}'.format(
        args.case, args.rounds,
        '' if args.stagger is None else '，STAGGER={}'.format(args.stagger)), flush=True)

    with open(evidence_path, 'w', encoding='utf-8') as evidence:
        evidence.write('用例：{}\n时间：{}\n\n'.format(args.case, stamp))
        for round_no in range(1, args.rounds + 1):
            code, output = run_round(args.case, args.stagger, args.timeout)
            outcome = classify(code, output)
            tally[outcome] += 1
            print('[复现] 第 {}/{} 轮 {:<8}{}'.format(
                round_no, args.rounds, outcome, key_line(output)), flush=True)
            if outcome in ('red', 'invalid'):
                # 红的留下当提单材料，无效的用来看是环境还是中断——绿的没什么可看的
                evidence.write('=== 第 {} 轮 {}（退出码 {}）===\n{}\n\n'.format(
                    round_no, outcome, code, output))

    valid = tally['red'] + tally['green']
    print('[复现] 汇总：红 {} / 绿 {} / 未测到 {} / 无效 {}（共 {} 轮）'.format(
        tally['red'], tally['green'], tally['blind'], tally['invalid'], args.rounds), flush=True)
    if valid:
        print('[复现] 复现率 {:.0f}%（{}/{}），未测到与无效轮次不计入分母'.format(
            tally['red'] / valid * 100, tally['red'], valid), flush=True)
    else:
        print('[复现] 没有有效轮次，先确认环境与频控参数再重跑', flush=True)
    print('[复现] 红与无效轮次的完整输出：{}'.format(evidence_path), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
