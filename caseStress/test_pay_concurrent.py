# -*- encoding=utf8 -*-
__desc__ = "并发打赏"

import os

# 必须在 import common.Request 之前：Request 在 import 阶段就把 REQUEST_INTERVAL 读成常量。
# 入口 run_stress_case.py 也设了一次，这里兜住「单独跑这个文件」的情况。
os.environ.setdefault('REQUEST_INTERVAL', '0')
# 频控不重试：退避重发会把两个并发请求拉成串行，测到的就不是并发了
os.environ.setdefault('FREQUENT_RETRY', '0')

import threading
import time
import unittest

from caseStress.config import (ANCHOR_UID, CEO_UID, CONCURRENT_PAYERS, GIFT, OWNER_UID, PAY_AMOUNT,
                               ROOM_RID, pay_url)
from caseStress.tools import (classify, concurrent_window_tested, expected_rows, flows_by_key,
                              max_pay_change_id, read_flows_by_uid, read_money, read_total_money,
                              read_wallets, reset_payer, scale_income, split_flows, wait_flow_quiet,
                              wait_flows_stable)
from common.Assert import (WAIT_INTERVAL, WAIT_TIMEOUT, assert_between, assert_equal,
                           assert_equal_eventually)
from common.Request import FREQUENT_RETRY, frequent_retry_count, post_request_session, reset_frequent_retries
from common.Session import Session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
from common.tools import get_test_token

# 日志里带名字：流水只给 uid，光看数字对不上人
PARTY_NAMES = {ANCHOR_UID: '主播', OWNER_UID: '厅长', CEO_UID: '公会长'}


def flow_text(income):
    """{(uid, op): [行数, 金额]} 转成一行可读文字，空的时候不返回空字符串"""
    return '，'.join('{}({}) op={} {}行{}元'.format(
        PARTY_NAMES.get(uid, 'uid'), uid, op, count, amount)
        for (uid, op), (count, amount) in sorted(income.items())) or '无'


def flow_rows_text(rows, limit=24):
    """原始流水行：id / 谁 / 什么 op / 多少钱

    聚合后的 flow_text 能看出「少了哪个 key」，看不出「是压根没写，还是晚到没读到」：
    id 的分布能把这两种情况分开——同一批的 id 应该连着，缺掉的那一行如果在
    后面又出现了，就是读得太早；完全不同就是结算真没写。
    """
    if not rows:
        return '无'
    items = ['#{id} {name}({uid}) {op} {money}元'.format(
        id=row['id'], name=PARTY_NAMES.get(row['uid'], 'uid'), uid=row['uid'],
        op=row['op'], money=row['money']) for row in rows[:limit]]
    if len(rows) > limit:
        items.append('……另 {} 行'.format(len(rows) - limit))
    return '，'.join(items)


class TestConcurrentPay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Session.getSession 只备 payUid / gsUid / gs_B_uid 三个账号的 token，并发名单里还有
        # gs_A_ceo_uid 与 normal_uid；post_request_session 按 pay_uid 从 token 文件里读，
        # 缺一个就会在发请求之前抛「token 为空」，看起来像并发失败，实际是没备 token
        token_map = get_test_token(*CONCURRENT_PAYERS)
        for uid, token in token_map.items():
            Session.checkUserToken('write', app_name='slp', uid=uid, token=token)

    def run_concurrently(self, tasks, stagger=0.0):
        """tasks = [(uid, callable)]，Barrier 对齐后同时出发，返回 [(uid, 响应)]

        线程里不写断言：unittest 的断言失败不会传回主线程，只会让线程静默退出，
        看起来像「少跑了一笔」。线程只负责发请求，判定全部回主线程做。

        stagger：第 n 个任务再加 n*stagger 秒。服务端对同一账号有限流，毫秒级完全
        同时发会被「请求太快」直接挡回去，根本走不到余额校验——用例虽然绿，却什么
        都没测到。错峰一点反而能落进「两次读余额都发生在第一次写之前」的窗口，
        那才是这条用例真正要打的地方。默认 0，保持完全同时。
        """
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(len(tasks))
        # 只统计本轮：频控是全进程共享的，不清零会把前面用例的账算到这一轮头上
        reset_frequent_retries()

        def worker(index, uid, call):
            try:
                barrier.wait(timeout=10)
                if stagger > 0:
                    time.sleep(index * stagger)
                res = call()
            except Exception as error:
                res = {'code': -1, 'body': {'msg': repr(error)}, 'error': True}
            with lock:
                results.append((uid, res))

        threads = [threading.Thread(target=worker, args=(index,) + task, name='pay-{}'.format(index))
                   for index, task in enumerate(tasks)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
            assert_equal(thread.is_alive(), False)
        assert_equal(len(results), len(tasks))

        # 频控会把并发拉成串行（命中后请求层退避 2 秒再发，同一账号的两个请求就不
        # 是同时到了）。入口已经把 FREQUENT_RETRY 设为 0，频控响应原样返回、由 classify
        # 计成业务拒绝，请求保持同时到达；这里只负责把次数报出来，让绿的含金量可见
        frequent = frequent_retry_count()
        if frequent and FREQUENT_RETRY > 0:
            note = '请求被退避重发拉成串行：余额不足场景的「通过」不可信，需重跑'
        elif frequent:
            note = '频控响应已原样计入业务拒绝（未重试），并发度保持完整'
        else:
            note = '并发度完整'
        print('[并发] 本轮命中频控 {} 次，错峰 {}s，{}'.format(frequent, stagger, note), flush=True)
        return results

    def stagger(self):
        """同账号两笔之间的错峰秒数：STAGGER=0.2 环境变量控制，默认 0（完全同时）"""
        return float(os.environ.get('STAGGER') or 0)

    def pay_call(self, uid):
        """uid 是收礼方，pay_uid 是扣款方：四个账号都打赏给同一个主播

        这里早先写的是 uid=uid（各自打赏自己），与 config 的 ANCHOR_UID、用例描述
        和 README 的「四账号并发打同一主播」三处都对不上，代码这一处是错的。
        自刷会把钱再返还到打赏方自己的 money_cash / money_cash_b（实测四个账号
        各累积 120~320），对账时「扣了多少」与「又收回来多少」糊在一起，
        失败现场根本分不清少扣的那一笔是没扣、还是被返还抵消了。
        """
        data = self.pay_data()
        return lambda: post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)

    def pay_data(self):
        """打赏给主播的请求体：探针与并发共用一份，避免两处参数漂移"""
        return encodeData(rid=ROOM_RID, payType='package', uid=ANCHOR_UID, giftId=GIFT['gid'],
                          display_page=1)

    def wait_stable(self, reader, quiet=5):
        """等到 reader() 的读数静默后返回该值：连续 quiet 次间隔读到同一个数才算稳定

        前置用例的打赏分成是异步结算的，跑到这条用例时上一轮的到账可能还在灌进来。
        基线只取一次瞬时快照，增量的差值就会把「别人的钱」一起算上：实测 unit 报 142，
        而单笔到账实际是 71——翻了一倍，后面 N * unit 跟着全错，于是在完全正确的
        服务端上报「到账不守恒」。

        reader 传无参可调用而不是 uid：要同时盯主播、厅长、公会长三个账户，而且
        余额与累计是两个字段，写死成某一个就没法复用。

        超时返回最后一次读数，不抛：结算比 WAIT_TIMEOUT 还慢的情况下，静默与否分不清，
        这个判断应该交给调用方的断言，而不是在这里猜。
        """
        last = reader()
        same = 0
        deadline = time.time() + WAIT_TIMEOUT
        while time.time() < deadline:
            time.sleep(WAIT_INTERVAL)
            now = reader()
            same = same + 1 if now == last else 0
            last = now
            if same >= quiet:
                return last
        return last

    def batch_flows(self, mark, gid, payers, uids, least=1, await_uids=()):
        """取水位线之后的流水，拆成收款/付款两部分，返回 (income, pay, note, rows)

        payers 是本轮自己下单的账号：付款行按 uid 认，不靠 op 名（见 tools.split_flows）。
        uids 只用于按 gid 查不到时的兜底复查，范围要盖住收款人。

        按 gid 筛不到时用 uid 兜底复查，把两种可能分开：结算压根没写流水（真缺陷），
        还是写了但不带 gid（本轮的筛选口径失效）。前者直接抛失败，后者返回一句说明
        由调用方显式打印——两种情况都不能悄悄当成通过。

        note 为空表示口径正常、返回值可信；note 非空时 income/pay 都是空的。
        rows 一起交回：失败时要打原始行（id 分布能把「没写」和「读得太早」分开）。
        """
        rows = wait_flows_stable(mark, gid, least=least, await_uids=await_uids)
        income, pay = split_flows(rows, payers)
        if income or pay:
            return income, pay, '', rows
        looked = sum(len(read_flows_by_uid(mark, uid)) for uid in uids)
        if looked:
            return {}, [], '按 uid 查到 {} 行流水，但都不带 gid={}，按 gid 框批次的筛选失效'.format(
                looked, gid), rows
        raise AssertionError(
            '成交后 {} 秒内按 gid 和按 uid 都查不到流水（账号 {}）：结算可能没写库。'
            '这不是「未测到」，是「成交了没留痕」'.format(int(WAIT_TIMEOUT), list(uids)))

    def probe_flows(self, payer):
        """单笔探针：量出「一笔打赏到底写了哪些流水」，返回 (income, pay, note, kind)

        收款侧的一切判据都来自这一笔：写几条路径、每条几行、各多少，不预设谁分成、
        也不写死比例。三条用例（003/005/006）共用，免得各自写一份、迟早口径漂移。

        kind 不是 'success' 时 income/pay 都是空的：调用方要先决定这一轮算未测到、
        还是根本不能算未测到（成交了却没留痕是真的缺陷）。
        """
        # 先等流水表安静：上一条用例若是 SkipTest 走的，它那批还在异步落库，
        # 这一取水位线就会把别人的行当成这一笔的写路径
        wait_flow_quiet()
        mark = max_pay_change_id()
        kind = classify(
            post_request_session(pay_url, self.pay_data(), tokenName='slp', pay_uid=payer))
        if kind != 'success':
            return {}, [], '', kind
        income, pay, note, _ = self.batch_flows(
            mark, GIFT['gid'], (payer,), (ANCHOR_UID, payer), await_uids=(payer,))
        return income, pay, note, kind

    def batch_buckets(self, mark, gid, uid, least=1):
        """自刷批次：按（账号, op）分桶取流水，返回 (buckets, rows, note)

        为什么不复用 batch_flows：自刷时付款方就是收款人，split_flows 按 uid 认付款行，
        会把收款行一起算成付款行，收款侧一条都不剩——「收一份钱、发两份货」在付款侧
        完全看不出来（行数与金额都对）。分桶不区分收付，一笔自刷写下的每个桶都要严格
        按成功笔数放大，多一行 income 就红。

        note 非空 = 流水写了但不带 gid（筛选口径失效），由调用方打印并跳过；
        按 gid、按 uid 都查不到则是「扣了钱没留痕」，直接失败。

        只看自己那个账号的行（keep_uid）：自刷这一批里只有它在下单，别的账号的行
        只可能是别的批次晚到的。2026-10-29 真机就这样红过一次——上一条用例频控
        未测到直接跳、没等流水落库，探针就把 200250759 / 200252072 的 consume 行
        算成了自己这一笔的写路径。
        """
        rows = wait_flows_stable(mark, gid, least=least, await_uids=(uid,), keep_uid=uid)
        if rows:
            return flows_by_key(rows), rows, ''
        looked = read_flows_by_uid(mark, uid)
        if looked:
            return {}, rows, '按 uid 查到 {} 行流水，但都不带 gid={}，按 gid 框批次的筛选失效'.format(
                len(looked), gid)
        raise AssertionError(
            '自刷成交后 {} 秒内按 gid 和按 uid 都查不到流水（账号 {}）：钱扣了却没留痕。'
            '这不是「未测到」'.format(int(WAIT_TIMEOUT), uid))

    def assert_conserved(self, uid, before, success_count, price, body_text):
        """钱与响应必须严格对应：多说成功就是多扣，少说成功就是给货没扣钱

        余额只留了单笔的量，所以「成功两笔却只扣一笔」和「成功一笔却扣两笔」
        都会在这里露出来：前者扣款对不上，后者余额变负被透支区间挡住。
        """
        expect_deducted = success_count * price
        try:
            # 下单后余额可能异步落库，直接读一次会把「还没写库」当成没扣钱
            assert_equal_eventually(lambda: before - read_money(uid), expect_deducted)
        finally:
            # 无论轮询到达还是超时，都把现场打出来：失败时这一行才是能定位账号的依据。
            # 全渠道一起打：只打 money 时，「钱从别的渠遁扣走了」和「少扣一笔」长得一模一样
            left = read_money(uid)
            print('[并发] uid={} 下单前={} 现在={} 扣款={} 期望扣款={} 成功响应={} 笔 全渠道={} 响应={}'.format(
                uid, before, left, before - left, expect_deducted, success_count,
                read_wallets(uid), body_text), flush=True)
        # 余额不得为负：「成功两笔却只扣一笔」会被上面抓到，「只成功一笔却扣两笔」在这里露出来
        assert_between(left, 0, before)

    def test_001(self, des='四账号并发打同一主播: 扣款总额=成功笔数*单价, 且不得透支'):
        price = PAY_AMOUNT
        before = {}
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price)
            before[uid] = read_money(uid)
        assert_equal(sorted(before.values()), [price] * len(CONCURRENT_PAYERS))

        results = self.run_concurrently([(uid, self.pay_call(uid)) for uid in CONCURRENT_PAYERS])
        outcome = {uid: (classify(res), res) for uid, res in results}
        success = [uid for uid in CONCURRENT_PAYERS if outcome[uid][0] == 'success']
        limited = [uid for uid in CONCURRENT_PAYERS if outcome[uid][0] == 'limited']
        rejected = [(uid, outcome[uid][1].get('body')) for uid in CONCURRENT_PAYERS
                    if outcome[uid][0] == 'rejected']
        broken = [(uid, outcome[uid][1]) for uid in CONCURRENT_PAYERS if outcome[uid][0] == 'broken']
        print('[并发] 成功 {} 笔 {}，频控 {} 笔 {}，业务拒绝 {} 笔 {}，服务端异常 {} 笔'.format(
            len(success), success, len(limited), limited, len(rejected), rejected, len(broken)), flush=True)
        for uid, res in broken:
            print('[并发][服务端异常] uid={} 响应={}'.format(uid, res), flush=True)

        # 服务端异常不接受：HTTP 非 200 / 空 body / 请求层抛错，那是真问题
        assert_equal(broken, [])
        # 全部被拒等于什么都没测到，至少得有一笔成交；上界就是并发人数
        assert_between(len(success), 1, len(CONCURRENT_PAYERS))
        for uid in CONCURRENT_PAYERS:
            self.assert_conserved(uid, before[uid], 1 if uid in success else 0, price,
                                  outcome[uid][1].get('body'))

    def test_002(self, des='同账号并发两笔(余额只够一笔): 钱与成功响应严格对应且不得透支'):
        uid = CONCURRENT_PAYERS[0]
        price = PAY_AMOUNT
        reset_payer(uid, price)
        before = read_money(uid)

        results = self.run_concurrently([(uid, self.pay_call(uid)), (uid, self.pay_call(uid))],
                                        stagger=self.stagger())
        kinds = [classify(res) for _, res in results]
        bodies = [res.get('body') for _, res in results]
        broken = [body for body, kind in zip(bodies, kinds) if kind == 'broken']
        print('[并发-同账号] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔，响应 {}'.format(
            kinds.count('success'), kinds.count('limited'), kinds.count('rejected'),
            len(broken), bodies), flush=True)
        assert_equal(broken, [])
        if kinds.count('limited') >= 1 or kinds.count('success') == 0:
            # 被限流挡下的那一笔根本没走到余额校验，守恒式两侧一起缩小，绿得毫无意义。
            # 这里必须抛 SkipTest 而不是只打印：只打印在报告里仍然是一条「通过」，
            # 看报告的人不知道这一轮其实什么都没测到。
            print('[并发-同账号][未测到] 成功 {} 笔、频控 {} 笔：第二笔没走到余额校验，本轮结论无效；'
                  '可试 STAGGER=0.2 错峰重跑'.format(
                      kinds.count('success'), kinds.count('limited')), flush=True)
            raise unittest.SkipTest('第二笔没走到余额校验（成功 {} 笔、频控 {} 笔），本轮没验并发窗口'.format(
                kinds.count('success'), kinds.count('limited')))

        # 两笔都成功时服务端必须真的扣两笔：余额只留了一笔，扣两笔会变负，被区间挡住
        self.assert_conserved(uid, before, kinds.count('success'), price, bodies)

    def test_003(self, des='四账号各连发两笔: 每个账号扣款=自己成功笔数*单价, 分成也按成功笔数放大'):
        """一次并发 8 个请求，但判定按账号拆开算

        上一轮实测服务端对相同请求没有幂等，两笔都可能成交；这里不预设「第几笔该被拒」
        （口径还在产品那边确认），只钉死一件事：每个账号的扣款必须等于它自己成功了几笔。
        余额留两笔的量，所以「响应说一笔、实际扣两笔」不会因为余额不足被掩成拒绝，
        真扣了就能看见。

        另加一道收款侧流水对账：余额只证明「钱扣对了」，证明不了「货发了几份」。
        同账号连发两笔最该防的恰恰是「收一份钱、发两份货」——test_004 撞到的那次
        缺陷就是两笔都返回成功、钱只扣一笔、分成却发了两份。多写一行分成在余额上
        完全不体现，只有流水能看出来。

        错峰（STAGGER）必须一起传：任务表按账号成对排，同账号那两笔正好相差一个错峰量。
        不传时 8 个请求完全同时，第二笔全被频控挡在请求层，这条用例就只剩「未测到」
        （2026-10-29 真机就是如此：4 次频控、每个账号各挡一笔）。
        """
        price = PAY_AMOUNT
        gid = GIFT['gid']
        probe = CONCURRENT_PAYERS[0]
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price * 2)

        # 探针：这笔打赏在流水里写了几行、给谁、各多少，全部实测（同 test_005）
        income_probe, pay_probe, note, probe_kind = self.probe_flows(probe)

        # 探针花掉一笔，补回两笔的量：余额少了，「第二笔该成交却被拒」会被错当成
        # 服务端去重，扣款侧那一半就白验了
        reset_payer(probe, price * 2)
        before = {uid: read_money(uid) for uid in CONCURRENT_PAYERS}
        assert_equal(sorted(before.values()), [price * 2] * len(CONCURRENT_PAYERS))
        mark = max_pay_change_id()

        tasks = []
        for uid in CONCURRENT_PAYERS:
            tasks.append((uid, self.pay_call(uid)))
            tasks.append((uid, self.pay_call(uid)))

        results = self.run_concurrently(tasks, stagger=self.stagger())
        kinds, bodies = {}, {}
        for uid, res in results:
            kinds.setdefault(uid, []).append(classify(res))
            bodies.setdefault(uid, []).append(res.get('body'))

        broken = [(uid, body) for uid in CONCURRENT_PAYERS
                  for body, kind in zip(bodies[uid], kinds[uid]) if kind == 'broken']
        for uid in CONCURRENT_PAYERS:
            print('[并发-重发] uid={} 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，响应 {}'.format(
                uid, kinds[uid].count('success'), kinds[uid].count('limited'),
                kinds[uid].count('rejected'), bodies[uid]), flush=True)

        assert_equal(broken, [])
        # 频控那一笔在请求层就被挡下，根本没走到余额与幂等校验。四个账号的第二笔全被
        # 挡下时，「同账号连发两笔」这个场景本轮一次都没验到——而扣款侧依然各扣一笔、
        # 全对，绿得毫无意义。2026-10-29 真机跑就撞上了：4 次频控、每账号各挡一笔
        clean = concurrent_window_tested(kinds)
        if not clean:
            print('[并发-重发][未测到] 第二笔全被频控挡下（本轮频控 {} 次）：没有一对送到校验，'
                  '本轮没验同账号重复提交；可试 STAGGER=0.2'.format(
                      sum(kinds[uid].count('limited') for uid in CONCURRENT_PAYERS)), flush=True)
            raise unittest.SkipTest('第二笔全被频控挡下，本轮没验同账号重复提交')
        if len(clean) < len(CONCURRENT_PAYERS):
            print('[并发-重发] 频控挡下的账号 {} 这一对没验到（扣款侧仍已验）'.format(
                [uid for uid in CONCURRENT_PAYERS if uid not in clean]), flush=True)

        # 一个账号都没成交等于什么都没测到
        total_success = sum(kinds[uid].count('success') for uid in CONCURRENT_PAYERS)
        assert_between(total_success, 1, len(CONCURRENT_PAYERS) * 2)
        for uid in CONCURRENT_PAYERS:
            self.assert_conserved(uid, before[uid], kinds[uid].count('success'), price, bodies[uid])

        # 收款侧流水：分成必须按成功笔数放大。探针没成交或筛选口径失效时这一半没验，
        # 不能因为扣款侧绿了就报通过
        if probe_kind != 'success' or note:
            why = note or '探针未成交（{}）'.format(probe_kind)
            print('[并发-重发][未测到] {}；收款侧本轮没验，扣款侧已验'.format(why), flush=True)
            raise unittest.SkipTest('收款侧没验（{}）；扣款侧已验'.format(why))
        if not income_probe:
            raise AssertionError(
                '探针成交并写下了 {} 行付款流水，但没有任何收款行：这笔打赏没给任何人分成'.format(
                    len(pay_probe)))

        succeeded = [uid for uid in CONCURRENT_PAYERS for kind in kinds[uid] if kind == 'success']
        income_batch, pay_batch, note_batch, batch_rows = self.batch_flows(
            mark, gid, CONCURRENT_PAYERS, CONCURRENT_PAYERS + (ANCHOR_UID,),
            least=expected_rows(income_probe, pay_probe, total_success), await_uids=succeeded)
        if note_batch:
            print('[并发-重发][未测到] {}；收款侧本轮没验，扣款侧已验'.format(note_batch), flush=True)
            raise unittest.SkipTest('流水筛选失效，收款侧没验：{}'.format(note_batch))
        try:
            # 收款侧：写路径、条数、金额整体按成功笔数放大
            assert_equal(income_batch, scale_income(income_probe, total_success))
            # 付款侧：成交几笔就几行扣款，且每行都要落在成交的那个账号名下
            if not pay_probe:
                raise unittest.SkipTest(
                    '探针那笔没有任何付款流水（付款方 {}），付款侧本轮没验'.format(probe))
            assert_equal(sorted({int(row['uid']) for row in pay_batch}), sorted(set(succeeded)))
            assert_equal(len(pay_batch), len(pay_probe) * total_success)
            assert_equal(sum(int(row['money'] or 0) for row in pay_batch),
                         sum(int(row['money'] or 0) for row in pay_probe) * total_success)
        finally:
            print('[并发-重发] 流水 {}，期望 {}；付款行 {} 行 {} 元（期望 {} 行 {} 元，成交账号 {}）'
                  '；原始行 {}'.format(
                      flow_text(income_batch),
                      flow_text(scale_income(income_probe, total_success)),
                      len(pay_batch), sum(int(row['money'] or 0) for row in pay_batch),
                      len(pay_probe) * total_success if pay_probe else '未测',
                      sum(int(row['money'] or 0) for row in pay_probe) * total_success
                      if pay_probe else '未测',
                      sorted(succeeded), flow_rows_text(batch_rows)), flush=True)

    def test_004(self, des='同账号并发两笔自刷(余额只够一笔): 钱与响应必须一致, 不得透支, 分成不得多发'):
        """打赏给自己走的是另一条分支，余额校验与「打赏他人」不同

        2026-10-29 实测：余额 100、并发两笔自刷，两笔都返回 success=True，money 却只
        扣了 100（期望 200），同时两笔都产生了分成到账——收一份钱、发两份货。
        同一张卡同样的余额去打赏主播时，第二笔会被「余额不足」正确拒掉，
        可见问题只出在自刷分支的余额校验上。

        test_001~003 改成打赏主播后，这条路就没人覆盖了，单独留一条钉住，
        避免缺陷重新隐身。本用例转绿即代表服务端已修好，不要调断言去它变绿。

        收款侧也要对：那次缺陷在余额上能看出来（扣 100 而不是 200），而它的另一面
        ——只成交一笔、分成却写了两份——在余额上完全看不见。自刷付款方就是收款人，
        按 uid 分不出收付（见 batch_buckets），所以按（账号, op）分桶：整批的每个桶
        都必须正好是单笔探针的 success 倍。
        """
        uid = CONCURRENT_PAYERS[0]
        price = PAY_AMOUNT
        gid = GIFT['gid']

        # 自刷：收礼方就是付款人自己，不能复用 pay_call（那个固定打给主播）
        data = encodeData(rid=ROOM_RID, payType='package', uid=uid, giftId=GIFT['gid'],
                          display_page=1)

        def call():
            return post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)

        # 探针：自刷一笔写下哪些（账号, op）桶、各几行几元，全部实测。它花掉的那一笔
        # 随后被 reset 覆盖，不影响下面「余额只够一笔」的设置
        reset_payer(uid, price)
        # 先等上一条用例那批流水落完，再取水位线（同 probe_flows）
        wait_flow_quiet()
        probe_mark = max_pay_change_id()
        probe_kind = classify(call())
        if probe_kind == 'success':
            probe_buckets, _, note_probe = self.batch_buckets(probe_mark, gid, uid)
        else:
            probe_buckets, note_probe = {}, '探针未成交（{}）'.format(probe_kind)

        reset_payer(uid, price)
        before = read_money(uid)
        mark = max_pay_change_id()

        results = self.run_concurrently([(uid, call), (uid, call)], stagger=self.stagger())
        kinds = [classify(res) for _, res in results]
        bodies = [res.get('body') for _, res in results]
        broken = [body for body, kind in zip(bodies, kinds) if kind == 'broken']
        print('[并发-自刷] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔，响应 {}'.format(
            kinds.count('success'), kinds.count('limited'), kinds.count('rejected'),
            len(broken), bodies), flush=True)
        assert_equal(broken, [])
        if kinds.count('limited') >= 1 or kinds.count('success') == 0:
            # 同 test_002：只打印等于「通过」，必须让报告里能看见这一条没验到
            print('[并发-自刷][未测到] 成功 {} 笔、频控 {} 笔：第二笔没走到余额校验，本轮结论无效；'
                  '可试 STAGGER=0.2 错峰重跑'.format(
                      kinds.count('success'), kinds.count('limited')), flush=True)
            raise unittest.SkipTest('第二笔没走到余额校验（成功 {} 笔、频控 {} 笔），本轮没验自刷分支'.format(
                kinds.count('success'), kinds.count('limited')))

        self.assert_conserved(uid, before, kinds.count('success'), price, bodies)

        # 收款侧：成交几笔就放几倍分成。被拒那笔若也分了成，这里会多出一整倍——
        # 那种错在余额上完全看不出来（钱只扣了一笔、扣得也对）
        if note_probe:
            print('[并发-自刷][未测到] {}；收款侧本轮没验，扣款侧已验'.format(note_probe), flush=True)
            raise unittest.SkipTest('自刷收款侧没验（{}）；扣款侧已验'.format(note_probe))

        success = kinds.count('success')
        # 等待下界：分桶后付款行也在桶里，所以第二项传空，别把付款行算两遍
        buckets, batch_rows, note = self.batch_buckets(
            mark, gid, uid, least=expected_rows(probe_buckets, [], success))
        if note:
            print('[并发-自刷][未测到] {}；收款侧本轮没验，扣款侧已验'.format(note), flush=True)
            raise unittest.SkipTest('自刷流水筛选失效，收款侧没验：{}'.format(note))
        try:
            # 每个（账号, op）桶的条数与金额都要按成功笔数放大，多一条 income 就红
            assert_equal(buckets, scale_income(probe_buckets, success))
        finally:
            print('[并发-自刷] 流水 {}，期望 {}（成交 {} 笔）；原始行 {}'.format(
                flow_text(buckets), flow_text(scale_income(probe_buckets, success)), success,
                flow_rows_text(batch_rows)), flush=True)

    def test_005(self, des='四账号并发打赏同一主播: 分成流水按成功笔数放大, 收款人由单笔探针实测'):
        """收款侧按「流水」对账，不再按余额逐方对齐

        为什么换到流水：余额是下游结果，里面混了自己付款、渠道差异（money_cash /
        money_cash_b）、到账迟到。前几轮我一直在修这些量法（142、-100、355），
        一次都没碰到被测的并发问题——方向错了，case 怎么写都别扭。

        流水（xs_pay_change）是结算服务真正写下的东西：一行一个收款人，reason 里带
        from / gid / num / rate。「少一笔分成」在这里就是少一行，不会像余额那样被
        另一笔、另一个渠道、或收款人自己花掉的钱抵消掉。

        口径全部由探针实测，不预设谁分成：探针一笔成交后，先查出「这笔打赏到底写了
        哪些行」（收款人是谁、op 是什么、各多少钱），并发就要求这些行严格按成功笔数
        放大。所以厅配置从 71:6:3 变成 80:0:0 也不会红——配置变了就是探针值变了，
        只有「少写/多写一行」才红。

        余额只留一条粗校验（主播不是付款方）：流水记了多少，钱包就得涨多少，
        防的是「账记了、钱没进钱包」这种两段式失败。
        """
        price = PAY_AMOUNT
        gid = GIFT['gid']
        probe = CONCURRENT_PAYERS[0]
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price)

        # 探针：一笔成交写几行、给谁、各多少，全从流水实测，不按配置猜
        income_probe, pay_probe, note, probe_kind = self.probe_flows(probe)
        if probe_kind != 'success':
            # SkipTest 而不是 return：return 在报告里就是一条「通过」，cron 绿着但什么都没验。
            # skip 会进计数，干净后一眼能看到本轮有几条没测到。
            print('[并发-流水][未测到] 单笔探针没成交（{}），本次结论无效；可稍后重跑'.format(
                probe_kind), flush=True)
            raise unittest.SkipTest('探针未成交（{}），本轮没做流水对账'.format(probe_kind))
        if note:
            print('[并发-流水][未测到] {}；本轮没有对账，别当成通过'.format(note), flush=True)
            raise unittest.SkipTest('流水筛选失效，本轮没做对账：{}'.format(note))
        if not income_probe:
            # 有付款流水、一条收款行都没有：这笔钱没人收，后面的「空 == 空」会全绿过去
            raise AssertionError(
                '探针成交并写下了 {} 行付款流水，但没有任何收款行：这笔打赏没给任何人分成'.format(
                    len(pay_probe)))
        print('[并发-流水] 单笔探针：收款 {}；付款行 {} 行'.format(
            flow_text(income_probe), len(pay_probe)), flush=True)

        # 探针花掉的那一笔补回来，再把水位线推到探针之后：并发只认这之后的流水
        reset_payer(probe, price)
        mark = max_pay_change_id()
        base_anchor = self.wait_stable(lambda: read_total_money(ANCHOR_UID))

        results = self.run_concurrently([(uid, self.pay_call(uid)) for uid in CONCURRENT_PAYERS])
        kind_by_uid = {uid: classify(res) for uid, res in results}
        kinds = list(kind_by_uid.values())
        broken = [res.get('body') for uid, res in results if kind_by_uid[uid] == 'broken']
        success = kinds.count('success')
        print('[并发-流水] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔'.format(
            success, kinds.count('limited'), kinds.count('rejected'), len(broken)), flush=True)

        assert_equal(broken, [])
        assert_between(success, 1, len(CONCURRENT_PAYERS))

        # 等这批流水写完：期望行数 = 探针实测行数 × 成功笔数（当等待下界，不放宽断言）。
        # await_uids：每笔都该留下自己的付款流水；实测出现过「4 笔分成先到、付款行后到」，
        # 光靠行数静默会提前返回，把晚到的当作没写
        succeeded = [uid for uid, kind in kind_by_uid.items() if kind == 'success']
        income_batch, pay_batch, note, batch_rows = self.batch_flows(
            mark, gid, CONCURRENT_PAYERS, CONCURRENT_PAYERS + (ANCHOR_UID,),
            least=expected_rows(income_probe, pay_probe, success), await_uids=succeeded)
        if note:
            print('[并发-流水][未测到] {}；本轮没有对账，别当成通过'.format(note), flush=True)
            raise unittest.SkipTest('流水筛选失效，本轮没做对账：{}'.format(note))
        try:
            # 收款侧：每个（收款人, op）就是一条写路径，条数与金额都按成功笔数放大。
            # 整体比较而不是分开比：键集合、条数、金额一次比完——分开比时
            # 「主播多一行、厅长少一行」两个 key 都在、总额也对，就漏过去了
            assert_equal(income_batch, scale_income(income_probe, success))
            # 付款侧：成交几笔就该有几行扣款流水，而且每行都得落在成交的那个账号名下。
            # 只比总行数会漏掉「A 少一行、B 多一行」；只比金额会漏掉「凑巧对得上」。
            if not pay_probe:
                # 探针那笔都没有付款行，付款侧无从对账。只打印一句就当成通过，
                # 等于这条用例只验了一半却报绿
                raise unittest.SkipTest(
                    '探针那笔没有任何付款流水（付款方 {}），付款侧本轮没验'.format(probe))
            assert_equal(sorted({int(row['uid']) for row in pay_batch}), sorted(succeeded))
            assert_equal(len(pay_batch), len(pay_probe) * success)
            # 行数对上还得金额对上：一行 100 记成 1，行数一模一样，钱却漏了。
            # 期望值按探针实测放大，不写死单价（厅配置变了单价也会变）
            assert_equal(sum(int(row['money'] or 0) for row in pay_batch),
                         sum(int(row['money'] or 0) for row in pay_probe) * success)
        finally:
            # 失败时这几行才是能定位的依据：哪条写路径少了、少了多少、缺的是哪一笔
            print('[并发-流水] 并发流水 {}，期望 {}；付款行 {} 行 {} 元（期望 {} 行 {} 元，成交账号 {}）；响应 {}'.format(
                flow_text(income_batch),
                flow_text(scale_income(income_probe, success)),
                len(pay_batch), sum(int(row['money'] or 0) for row in pay_batch),
                len(pay_probe) * success if pay_probe else '未测',
                sum(int(row['money'] or 0) for row in pay_probe) * success if pay_probe else '未测',
                succeeded, kinds), flush=True)
            print('[并发-流水] 原始行：{}'.format(flow_rows_text(batch_rows)), flush=True)

        # 余额粗校验：主播不是付款方，流水记多少钱包就该涨多少
        anchor_income = sum(amount for (uid, _), (_, amount) in income_probe.items()
                            if uid == ANCHOR_UID)
        if anchor_income:
            assert_equal_eventually(lambda: read_total_money(ANCHOR_UID) - base_anchor,
                                    anchor_income * success)

    def test_006(self, des='四账号并发, 其中一人零余额: 该笔必须被拒且不牵连其余三笔'):
        """部分失败不能拖垮整批，也不能被整批抹平

        两种常见错法：一是「一人余额不足、整批都失败」，说明校验被做成了批次级；
        二是更糟的「零余额那个也返回成功」，钱要么没扣就发了货，要么从别人的账上抹平。
        四个账号各自独立，所以这里严格按「每人一刀」验：成功的必须扣钱，被拒的一分不少。

        reset_payer 只设 money，所以零余额那个账号还要把其他渠道一起清零——
        只清 money 时，服务端若回退到别的渠道扣款，这条用例就白测了。
        """
        price = PAY_AMOUNT
        gid = GIFT['gid']
        broke = CONCURRENT_PAYERS[-1]
        probe = CONCURRENT_PAYERS[0]

        # 先量口径：探针用一个有余额的账号，它花掉的那一笔随后被 reset 覆盖。
        # 必须放在「零余额」设置之前，否则探针自己就被拒了，收款侧根本无从放大
        reset_payer(probe, price)
        income_probe, pay_probe, note_probe, probe_kind = self.probe_flows(probe)

        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, 0 if uid == broke else price)
        mysql.updateMoneySql(broke)  # 默认实参全 0：五个渠道一起清
        before = {uid: read_money(uid) for uid in CONCURRENT_PAYERS}
        assert_equal(before[broke], 0)
        mark = max_pay_change_id()

        results = self.run_concurrently([(uid, self.pay_call(uid)) for uid in CONCURRENT_PAYERS])
        kinds = {uid: classify(res) for uid, res in results}
        bodies = {uid: res.get('body') for uid, res in results}
        broken = [body for uid, body in bodies.items() if kinds[uid] == 'broken']
        others = [uid for uid in CONCURRENT_PAYERS if uid != broke]
        print('[并发-零余额] 零余额账号={} 结果={}；其余三人 成功 {} 笔，频控 {} 笔，'
              '业务拒绝 {} 笔，服务端异常 {} 笔'.format(
                  broke, kinds[broke], [kinds[uid] for uid in others].count('success'),
                  [kinds[uid] for uid in others].count('limited'),
                  [kinds[uid] for uid in others].count('rejected'), len(broken)), flush=True)

        assert_equal(broken, [])
        # 零余额那个必须被拒：返回 success 就是「没扣钱却发了货」
        assert_equal(kinds[broke], 'rejected')
        # 其余三人不该被牵连：一个人没钱，不能让整批都失败
        assert_between([kinds[uid] for uid in others].count('success'), 1, len(others))
        for uid in CONCURRENT_PAYERS:
            self.assert_conserved(uid, before[uid], 1 if kinds[uid] == 'success' else 0, price,
                                  bodies[uid])

        # 流水对账：拒单不能留下付款流水，也不能白送分成
        #
        # 扣款侧只能证明「被拒的那个账号余额没变」，证明不了服务端没给收礼人分成：
        # 若拒单只回了响应、去重没做干净，分成照样写进收款人账户，钱就是从平台手里漏的。
        # 付款流水一行一笔，所以成交几笔就该几行，多一行就是「拒了单还扣钱」。
        success = [kinds[uid] for uid in CONCURRENT_PAYERS].count('success')
        succeeded = [uid for uid in CONCURRENT_PAYERS if kinds[uid] == 'success']

        # 收款侧也要对：拒单只回响应、分成却照写，钱就是从平台手里漏的。
        # 这种错在付款行上完全看不出来（付款行数、金额都对），只有收款行能抓住
        if probe_kind != 'success' or note_probe:
            why = note_probe or '探针未成交（{}）'.format(probe_kind)
            print('[并发-零余额][未测到] {}；扣款侧已验，收款分成侧本轮没验'.format(why), flush=True)
            raise unittest.SkipTest('拒单是否白送分成本轮没验（{}）；扣款侧已验'.format(why))
        if not income_probe:
            raise AssertionError(
                '探针成交并写下了 {} 行付款流水，但没有任何收款行：这笔打赏没给任何人分成'.format(
                    len(pay_probe)))

        income_batch, pay_batch, note, batch_rows = self.batch_flows(
            mark, gid, CONCURRENT_PAYERS, CONCURRENT_PAYERS + (ANCHOR_UID,),
            least=expected_rows(income_probe, pay_probe, success), await_uids=succeeded)
        if note:
            # 扣款侧（余额）已经验完了，但「拒单还白送分成」这一半没验到。
            # 只打印一句让这条用例报绿，等于把没验的那一半藏起来
            print('[并发-零余额][未测到] {}；扣款侧已验，收款分成侧本轮没验'.format(note), flush=True)
            raise unittest.SkipTest('流水筛选失效，拒单是否白送分成本轮没验：{}'.format(note))
        try:
            # 收款侧：成交几笔就该放几倍的分成；被拒那笔若也分了成，这里会多出一整倍
            assert_equal(income_batch, scale_income(income_probe, success))
            # 付款行既要行数对，也要落在成交的账号名下：只比行数会让
            # 「被拒账号多一行、成交账号少一行」互相抵消
            assert_equal(sorted({int(row['uid']) for row in pay_batch}), sorted(succeeded))
            assert_equal(len(pay_batch), success)
            # 行数对了金额还得对：拒单那一笔若留下了「0 元付款行」，行数看不出来、钱却动了
            assert_equal(sum(int(row['money'] or 0) for row in pay_batch), price * success)
        finally:
            print('[并发-零余额] 付款流水 {} 行共 {} 元（成交 {} 笔，期望 {} 元），'
                  '收款流水 {}，期望 {}；被拒账号={}；原始行 {}'.format(
                      len(pay_batch), sum(int(row['money'] or 0) for row in pay_batch), success,
                      price * success, flow_text(income_batch),
                      flow_text(scale_income(income_probe, success)), broke,
                      flow_rows_text(batch_rows)), flush=True)
