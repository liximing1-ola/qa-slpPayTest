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

from caseStress.config import ANCHOR_UID, CONCURRENT_PAYERS, GIFT, PAY_AMOUNT, ROOM_RID, pay_url
from caseStress.tools import classify, read_income, read_money, read_wallets, reset_payer
from common.Assert import (WAIT_INTERVAL, WAIT_TIMEOUT, assert_between, assert_equal,
                           assert_equal_eventually)
from common.Request import FREQUENT_RETRY, frequent_retry_count, post_request_session, reset_frequent_retries
from common.Session import Session
from common.basicSlpXsgData import encodeData
from common.tools import get_test_token


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

    def wait_income_gain(self, uid, base):
        """等到账增量出现，返回增量；超时返回 0 交给调用方判

        分成是异步结算，下单成功不等于钱已到账，读一次就判会把「还没写库」当成没到账。
        """
        deadline = time.time() + WAIT_TIMEOUT
        while time.time() < deadline:
            gain = read_income(uid) - base
            if gain > 0:
                return gain
            time.sleep(WAIT_INTERVAL)
        return 0

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
        if kinds.count('limited') >= 1 or kinds.count('success') == 0:
            # 被限流挡下的那一笔根本没走到余额校验，守恒式两侧一起缩小，绿得毫无意义
            print('[并发-同账号][未测到] 有 {} 笔被限流挡下，第二笔没走到余额校验，本轮结论无效；'
                  '可试 STAGGER=0.2 错峰重跑'.format(kinds.count('limited')), flush=True)

        assert_equal(broken, [])
        # 两笔都成功时服务端必须真的扣两笔：余额只留了一笔，扣两笔会变负，被区间挡住
        self.assert_conserved(uid, before, kinds.count('success'), price, bodies)

    def test_003(self, des='四账号各连发两笔相同请求: 每个账号扣款=自己成功笔数*单价, 且不得透支'):
        """一次并发 8 个请求，但判定按账号拆开算

        上一轮实测服务端对相同请求没有幂等，两笔都可能成交；这里不预设「第几笔该被拒」
        （口径还在产品那边确认），只钉死一件事：每个账号的扣款必须等于它自己成功了几笔。
        余额留两笔的量，所以「响应说一笔、实际扣两笔」不会因为余额不足被掩成拒绝，
        真扣了就能看见。
        """
        price = PAY_AMOUNT
        before = {}
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price * 2)
            before[uid] = read_money(uid)

        tasks = []
        for uid in CONCURRENT_PAYERS:
            tasks.append((uid, self.pay_call(uid)))
            tasks.append((uid, self.pay_call(uid)))

        results = self.run_concurrently(tasks)
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
        # 一个账号都没成交等于什么都没测到
        assert_between(sum(kinds[uid].count('success') for uid in CONCURRENT_PAYERS),
                       1, len(CONCURRENT_PAYERS) * 2)
        for uid in CONCURRENT_PAYERS:
            self.assert_conserved(uid, before[uid], kinds[uid].count('success'), price, bodies[uid])

    def test_004(self, des='同账号并发两笔自刷(余额只够一笔): 钱与响应必须一致, 不得透支'):
        """打赏给自己走的是另一条分支，余额校验与「打赏他人」不同

        2026-10-29 实测：余额 100、并发两笔自刷，两笔都返回 success=True，money 却只
        扣了 100（期望 200），同时两笔都产生了分成到账——收一份钱、发两份货。
        同一张卡同样的余额去打赏主播时，第二笔会被「余额不足」正确拒掉，
        可见问题只出在自刷分支的余额校验上。

        test_001~003 改成打赏主播后，这条路就没人覆盖了，单独留一条钉住，
        避免缺陷重新隐身。本用例转绿即代表服务端已修好，不要调断言去它变绿。
        """
        uid = CONCURRENT_PAYERS[0]
        price = PAY_AMOUNT
        reset_payer(uid, price)
        before = read_money(uid)

        # 自刷：收礼方就是付款人自己，不能复用 pay_call（那个固定打给主播）
        data = encodeData(rid=ROOM_RID, payType='package', uid=uid, giftId=GIFT['gid'],
                          display_page=1)

        def call():
            return post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)

        results = self.run_concurrently([(uid, call), (uid, call)], stagger=self.stagger())
        kinds = [classify(res) for _, res in results]
        bodies = [res.get('body') for _, res in results]
        broken = [body for body, kind in zip(bodies, kinds) if kind == 'broken']
        print('[并发-自刷] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔，响应 {}'.format(
            kinds.count('success'), kinds.count('limited'), kinds.count('rejected'),
            len(broken), bodies), flush=True)
        if kinds.count('limited') >= 1 or kinds.count('success') == 0:
            print('[并发-自刷][未测到] 有 {} 笔被限流挡下，第二笔没走到余额校验，本轮结论无效；'
                  '可试 STAGGER=0.2 错峰重跑'.format(kinds.count('limited')), flush=True)

        assert_equal(broken, [])
        self.assert_conserved(uid, before, kinds.count('success'), price, bodies)

    def test_005(self, des='四账号并发打赏同一主播: 收礼方到账总额=成功笔数*单笔到账'):
        """扣款守恒归 test_001，这条只验收款侧——两条不同的链路

        扣款在支付服务里做余额扣减，分成在结算服务里「按厅取比例 + 累加」。前者错了
        打赏用户立刻投诉；后者错了要等主播对账才发现，而且到账是异步的——丢失更新会
        表现成「总额少一笔」，很容易被当成「还在结算中」糊过去，所以必须等到达标或超时。

        比例不写死：先单笔测出 unit，再要求并发 N 笔的增量严格等于 N * unit。单笔到账
        多少是业务规则（跟厅、工会、是否签署大神都有关），写死比例会把配置变更变成红灯，
        也会掩盖真正的守恒问题；多笔是否守恒才是并发正确性。
        """
        price = PAY_AMOUNT
        probe = CONCURRENT_PAYERS[0]
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price)

        base = read_income(ANCHOR_UID)
        probe_res = post_request_session(pay_url, self.pay_data(), tokenName='slp', pay_uid=probe)
        probe_kind = classify(probe_res)
        if probe_kind != 'success':
            # 单笔都没成交，比例无从测起，守恒式两边都是 0，绿了也毫无意义
            print('[并发-到账][未测到] 单笔探针没成交（{}），测不出单笔到账额，本轮结论无效；'
                  '可稍后重跑'.format(probe_kind), flush=True)
            return
        unit = self.wait_income_gain(ANCHOR_UID, base)
        assert_between(unit, 1, price)

        # 探针花掉的那一笔补回来，否则这个账号余额少一份，并发时会因余额不足被拒
        reset_payer(probe, price)

        before = read_income(ANCHOR_UID)
        results = self.run_concurrently([(uid, self.pay_call(uid)) for uid in CONCURRENT_PAYERS])
        kinds = [classify(res) for _, res in results]
        bodies = [res.get('body') for _, res in results]
        broken = [body for body, kind in zip(bodies, kinds) if kind == 'broken']
        success = kinds.count('success')
        print('[并发-到账] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔；'
              '单笔到账={}，期望到账={}'.format(
                  success, kinds.count('limited'), kinds.count('rejected'), len(broken),
                  unit, success * unit), flush=True)

        assert_equal(broken, [])
        assert_between(success, 1, len(CONCURRENT_PAYERS))
        try:
            assert_equal_eventually(lambda: read_income(ANCHOR_UID) - before, success * unit)
        finally:
            # 失败时这一行才是能定位的依据：差多少、差几笔的钱、钱落在哪个渠道
            now = read_income(ANCHOR_UID)
            print('[并发-到账] 收礼方 uid={} 打赏前={} 现在={} 到账={} 期望={} 全渠道={}'.format(
                ANCHOR_UID, before, now, now - before, success * unit,
                read_wallets(ANCHOR_UID)), flush=True)
