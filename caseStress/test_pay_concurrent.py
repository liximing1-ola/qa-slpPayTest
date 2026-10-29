# -*- encoding=utf8 -*-
__desc__ = "并发打赏"

import os

# 必须在 import common.Request 之前：Request 在 import 阶段就把 REQUEST_INTERVAL 读成常量。
# 入口 run_stress_case.py 也设了一次，这里兜住「单独跑这个文件」的情况。
os.environ.setdefault('REQUEST_INTERVAL', '0')

import threading
import unittest

from caseStress.config import CONCURRENT_PAYERS, GIFT, PAY_AMOUNT, ROOM_RID, pay_url
from caseStress.tools import classify, read_money, reset_payer
from common.Assert import assert_between, assert_equal, assert_equal_eventually
from common.Request import post_request_session
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

    def run_concurrently(self, tasks):
        """tasks = [(uid, callable)]，Barrier 对齐后同时出发，返回 [(uid, 响应)]

        线程里不写断言：unittest 的断言失败不会传回主线程，只会让线程静默退出，
        看起来像「少跑了一笔」。线程只负责发请求，判定全部回主线程做。
        """
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(len(tasks))

        def worker(uid, call):
            try:
                barrier.wait(timeout=10)
                res = call()
            except Exception as error:
                res = {'code': -1, 'body': {'msg': repr(error)}, 'error': True}
            with lock:
                results.append((uid, res))

        threads = [threading.Thread(target=worker, args=task, name='pay-{}'.format(index))
                   for index, task in enumerate(tasks)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
            assert_equal(thread.is_alive(), False)
        assert_equal(len(results), len(tasks))
        return results

    def pay_call(self, uid):
        data = encodeData(rid=ROOM_RID, payType='package', uid=uid, giftId=GIFT['gid'], display_page=1)
        return lambda: post_request_session(pay_url, data, tokenName='slp', pay_uid=uid)

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
            # 无论轮询到达还是超时，都把现场打出来：失败时这一行才是能定位账号的依据
            left = read_money(uid)
            print('[并发] uid={} 下单前={} 现在={} 扣款={} 期望扣款={} 成功响应={} 笔 响应={}'.format(
                uid, before, left, before - left, expect_deducted, success_count, body_text), flush=True)
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

        results = self.run_concurrently([(uid, self.pay_call(uid)), (uid, self.pay_call(uid))])
        kinds = [classify(res) for _, res in results]
        bodies = [res.get('body') for _, res in results]
        broken = [body for body, kind in zip(bodies, kinds) if kind == 'broken']
        print('[并发-同账号] 成功 {} 笔，频控 {} 笔，业务拒绝 {} 笔，服务端异常 {} 笔，响应 {}'.format(
            kinds.count('success'), kinds.count('limited'), kinds.count('rejected'),
            len(broken), bodies), flush=True)

        assert_equal(broken, [])
        # 两笔都成功时服务端必须真的扣两笔：余额只留了一笔，扣两笔会变负，被区间挡住
        self.assert_conserved(uid, before, kinds.count('success'), price, bodies)
