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
from caseStress.tools import (classify, read_income, read_money, read_total_money, read_wallets,
                              reset_payer)
from common.Assert import (WAIT_INTERVAL, WAIT_TIMEOUT, assert_between, assert_equal,
                           assert_equal_eventually)
from common.Request import FREQUENT_RETRY, frequent_retry_count, post_request_session, reset_frequent_retries
from common.Session import Session
from common.basicSlpXsgData import encodeData
from common.conSlpXsgMysql import conMysql as mysql
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

    def test_005(self, des='四账号并发打赏同一主播: 主播/厅长/公会长三方分成各自守恒'):
        """扣款守恒归 test_001，这条只验收款侧——两条不同的链路

        扣款在支付服务里做余额扣减，分成在结算服务里「按厅取比例 + 累加」。前者错了
        打赏用户立刻投诉；后者错了要等主播对账才发现，而且到账是异步的——丢失更新会
        表现成「总额少一笔」，很容易被当成「还在结算中」糊过去，所以必须等到达标或超时。

        三方各验一次：厅配置 71:6:3 对应主播、厅长、公会长，是三条不同记录、各自写入。
        主播那行对了不代表另外两行也对——如果三者是三条相互独立的「读-加-写」，
        其中一条丢了在主播身上根本看不见。

        对账用 read_total_money（四个人民币渠道余额之和）而不是单个渠道：分成落在
        money_cash 还是 money_cash_b 由工会/大神身份决定，只看 money 会把「到账落别处」
        当成没到账。但要记住它是**可变余额**：公会长本人就在并发打赏名单里，他余额里少的
        那一刀是他自己花出去的，期望值里必须减掉（首跑就是漏了这一项：期望 0、实际 -100）。

        比例不写死：先单笔测出各方 unit，再要求并发 N 笔的增量严格等于 N * unit。单笔
        到账多少是业务规则（跟厅、工会、是否签署大神都有关），写死比例会把配置变更
        变成红灯，也会掩盖真正的守恒问题；多笔是否守恒才是并发正确性。

        基线必须等静默：前一条用例的到账是异步的，底还没落完就开始探，测出的 unit 会
        把别人的钱算进来（实测报过 142 = 71 x 2）。

        并发前要重新取一次基线：探针那一笔的到账就落在第一个基线到并发之间，不从并发
        基线里抹掉，它就会被算进「并发增量」（探针实测 355 = 284 + 71）。重取还能顺手
        吃掉迟到的到账，否则它会在并发窗口里冒出来，看起来像多到账了一笔。
        """
        price = PAY_AMOUNT
        probe = CONCURRENT_PAYERS[0]
        parties = (('主播', ANCHOR_UID), ('厅长', OWNER_UID), ('公会长', CEO_UID))
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, price)

        # 三方基线逐个等静默：静默轮询在本次迭代内就跑完，闭包晚绑定不会串到下一方
        base = {}
        for name, uid in parties:
            base[name] = self.wait_stable(lambda: read_total_money(uid))
        probe_res = post_request_session(pay_url, self.pay_data(), tokenName='slp', pay_uid=probe)
        probe_kind = classify(probe_res)
        if probe_kind != 'success':
            # 单笔都没成交，比例无从测起，守恒式两边都是 0，绿了也毫无意义
            print('[并发-到账][未测到] 单笔探针没成交（{}），测不出单笔到账额，本轮结论无效；'
                  '可稍后重跑'.format(probe_kind), flush=True)
            return

        unit = {}
        for name, uid in parties:
            unit[name] = self.wait_stable(lambda: read_total_money(uid)) - base[name]
        if unit['主播'] <= 0:
            # 成交了却一直没到账：可能是结算慢于超时，也可能是真丢了。两者在读数上
            # 长得一样，不在这一层替服务端定罪，但必须说清本轮没测到
            print('[并发-到账][未测到] 单笔探针成交但 {} 秒内主播没到账（增量 {}），'
                  '测不出单笔到账额，本轮结论无效；可稍后重跑'.format(
                      int(WAIT_TIMEOUT), unit['主播']), flush=True)
            return
        # 单笔到账不可能超过礼物单价：这条上界最早抓住「基线取错」这类错
        assert_between(unit['主播'], 1, price)
        for name in ('厅长', '公会长'):
            # 该厅可能没给这一方配分成，0 是合法的；但不可能为负
            assert_between(unit[name], 0, price)
        if unit['厅长'] == 0 and unit['公会长'] == 0:
            # 不报错（配置属于业务决定），但必须说出来：否则这一轮的绿看着验了三方，
            # 实际只验了主播一行，后面真丢了那两行也看不出来
            print('[并发-到账][注意] 厅长与公会长单笔到账都是 0，该厅可能没给这两方配分成，'
                  '本轮实际只验证了主播那一行', flush=True)

        # 探针花掉的那一笔补回来，否则这个账号余额少一份，并发时会因余额不足被拒
        reset_payer(probe, price)
        # 并发前重新取基线：把探针那一笔（及迟到的到账）留在窗口外，后面只对 success * unit 负责
        base = {}
        for name, uid in parties:
            base[name] = self.wait_stable(lambda: read_total_money(uid))

        results = self.run_concurrently([(uid, self.pay_call(uid)) for uid in CONCURRENT_PAYERS])
        # 按 uid 留档而不是只看总数：公会长既是收款方又是付款方，算他的期望值时
        # 要单独看他这一笔成没成交，才能决定减不减那一刀
        kind_by_uid = {uid: classify(res) for uid, res in results}
        kinds = list(kind_by_uid.values())
        bodies = [res.get('body') for _, res in results]
        broken = [res.get('body') for uid, res in results if kind_by_uid[uid] == 'broken']
        success = kinds.count('success')
        print('[并发-到账] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔；'
              '单笔分别为 {}；响应 {}'.format(
                  success, kinds.count('limited'), kinds.count('rejected'), len(broken),
                  '，'.join('{}={}'.format(name, unit[name]) for name, _ in parties), bodies),
              flush=True)

        assert_equal(broken, [])
        assert_between(success, 1, len(CONCURRENT_PAYERS))
        try:
            for name, uid in parties:
                baseline = base[name]
                # 他若自己也是付款方，余额里会少掉成交的那一笔——那不是分成少给了，
                # 不扣就是「期望 0、实际 -100」这种假红
                spend = price if kind_by_uid.get(uid) == 'success' else 0
                expect = success * unit[name] - spend
                assert_equal_eventually(lambda: read_total_money(uid) - baseline, expect)
        finally:
            # 失败时这一行才是能定位的依据：差多少、差几笔、哪一方丢的，以及余额落在哪个渠道
            print('[并发-到账] 余额增量 {}，期望 {}（已扣除各自付款 {}）；主播 uid={} 当前余额={} 全渠道={}'.format(
                '，'.join('{}={}'.format(name, read_total_money(uid) - base[name])
                         for name, uid in parties),
                '，'.join('{}={}'.format(name, success * unit[name]
                                        - (price if kind_by_uid.get(uid) == 'success' else 0))
                         for name, uid in parties),
                '，'.join('{}={}'.format(name, price if kind_by_uid.get(uid) == 'success' else 0)
                         for name, uid in parties),
                ANCHOR_UID, read_income(ANCHOR_UID), read_wallets(ANCHOR_UID)), flush=True)

    def test_006(self, des='四账号并发, 其中一人零余额: 该笔必须被拒且不牵连其余三笔'):
        """部分失败不能拖垮整批，也不能被整批抹平

        两种常见错法：一是「一人余额不足、整批都失败」，说明校验被做成了批次级；
        二是更糟的「零余额那个也返回成功」，钱要么没扣就发了货，要么从别人的账上抹平。
        四个账号各自独立，所以这里严格按「每人一刀」验：成功的必须扣钱，被拒的一分不少。

        reset_payer 只设 money，所以零余额那个账号还要把其他渠道一起清零——
        只清 money 时，服务端若回退到别的渠道扣款，这条用例就白测了。
        """
        price = PAY_AMOUNT
        broke = CONCURRENT_PAYERS[-1]
        for uid in CONCURRENT_PAYERS:
            reset_payer(uid, 0 if uid == broke else price)
        mysql.updateMoneySql(broke)  # 默认实参全 0：五个渠道一起清
        before = {uid: read_money(uid) for uid in CONCURRENT_PAYERS}
        assert_equal(before[broke], 0)

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
